import os
import json
import logging
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema

from accounts.models import RoleModel, Role
from properties.models import Property, PropertyFile
from properties.serializers import PropertySerializer, PropertyListSerializer
from properties.permissions import IsSponsor
from properties.validators import validate_images
from properties.services.file_services import download_images_from_urls
from properties.views.schemas import success_schema, error_schema

logger = logging.getLogger(__name__)


def _get_sponsor_role():
    """Return the Sponsor RoleModel (or None if not yet seeded)."""
    return RoleModel.objects.filter(name=Role.SPONSOR).first()


class PropertyViewSet(ModelViewSet):
    """
    Full CRUD for the requesting Sponsor's own properties.
    get_queryset() already filters by sponsor, so every object
    access is automatically ownership-checked.
    """

    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    permission_classes = [IsAuthenticated, IsSponsor]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        return PropertyListSerializer if self.action == "list" else PropertySerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Property.objects.none()

        qs = Property.objects.select_related("sponsor", "sponsor_role")

        # Superuser can see everything; regular Sponsor only sees their own
        if not self.request.user.is_superuser:
            qs = qs.filter(sponsor=self.request.user)

        # Only prefetch heavy file relations when actually needed
        if self.action in ("retrieve", "partial_update", "destroy"):
            return qs.prefetch_related(
                "files",
                "files__uploaded_by",
                "files__uploaded_by_role",
            )
        return qs.prefetch_related("files")

    def perform_create(self, serializer):
        serializer.save(sponsor=self.request.user, sponsor_role=_get_sponsor_role())

    @swagger_auto_schema(
        operation_summary="List my properties",
        tags=["Properties"],
        responses={200: success_schema("Properties retrieved successfully.")},
    )
    def list(self, request, *args, **kwargs):
        qs = self.get_queryset().order_by("-created_at")
        serializer = self.get_serializer(qs, many=True, context={"request": request})
        return Response(
            {"message": "Properties retrieved successfully.", "data": serializer.data}
        )

    @swagger_auto_schema(
        operation_summary="Create a property",
        tags=["Properties"],
        request_body=PropertySerializer,
        responses={
            201: success_schema("Property created successfully."),
            400: error_schema("Validation failed."),
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(
                {"message": "Property creation failed.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_create(serializer)
        prop = serializer.instance

        sponsor_role = _get_sponsor_role()

        # 1. Handle optional initial property images from manual uploads
        images = request.FILES.getlist("property_img")
        if images:
            valid_files, errors = validate_images(images)
            if not errors:
                for f in valid_files:
                    ext = os.path.splitext(f.name)[1].lstrip(".").lower()
                    PropertyFile.objects.create(
                        property=prop,
                        file=f,
                        category=PropertyFile.CATEGORY_IMAGE,
                        file_name=f.name,
                        file_type=ext,
                        image_source=PropertyFile.SOURCE_MANUAL,
                        uploaded_by=request.user,
                        uploaded_by_role=sponsor_role,
                    )

        # 2. Handle map photo URLs fetched from Google Places
        # Since it can be a list in a multipart form, we getlist
        photo_urls = request.data.getlist("photo_urls")

        # In case the frontend sends it as a single comma-separated string or multiple values
        # If it's empty, try 'photo_urls[]' just in case.
        if not photo_urls:
            photo_urls = request.data.getlist("photo_urls[]")

        # Clean up in case it's a single string with commas or a JSON array string
        if len(photo_urls) == 1:
            val = photo_urls[0].strip()
            if val.startswith('[') and val.endswith(']'):
                try:
                    photo_urls = json.loads(val)
                except Exception:
                    pass
            elif "," in val:
                photo_urls = [url.strip() for url in val.split(",")]

        if photo_urls:
            downloaded = download_images_from_urls(photo_urls)
            for filename, content in downloaded:
                ext = os.path.splitext(filename)[1].lstrip(".").lower()
                PropertyFile.objects.create(
                    property=prop,
                    file=content,
                    category=PropertyFile.CATEGORY_IMAGE,
                    file_name=filename,
                    file_type=ext,
                    image_source=PropertyFile.SOURCE_MAP,  # Mark it as coming from the map
                    uploaded_by=request.user,
                    uploaded_by_role=sponsor_role,
                )

        # Refresh serializer with the images attached
        serializer = self.get_serializer(prop, context={"request": request})

        return Response(
            {"message": "Property created successfully.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary="Get property detail",
        tags=["Properties"],
        responses={
            200: success_schema("Property retrieved successfully."),
            404: error_schema("Not found."),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            self.get_object(), context={"request": request}
        )
        return Response(
            {"message": "Property retrieved successfully.", "data": serializer.data}
        )

    @swagger_auto_schema(
        operation_summary="Update a property (partial)",
        tags=["Properties"],
        request_body=PropertySerializer,
        responses={
            200: success_schema("Property updated successfully."),
            400: error_schema("Validation failed."),
        },
    )
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=True, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(
                {"message": "Property update failed.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        return Response(
            {"message": "Property updated successfully.", "data": serializer.data}
        )

    @swagger_auto_schema(
        operation_summary="Delete a property",
        tags=["Properties"],
        responses={200: success_schema("Property deleted successfully.")},
    )
    def destroy(self, request, *args, **kwargs):
        self.get_object().delete()
        return Response({"message": "Property deleted successfully."})
