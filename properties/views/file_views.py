import os
import logging
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin, CreateModelMixin, DestroyModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework import status
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from properties.models import Property, PropertyFile
from properties.serializers import PropertyFileSerializer
from properties.permissions import IsSponsor
from properties.validators import validate_documents, validate_images
from properties.views.property_views import _get_sponsor_role
from properties.views.schemas import success_schema, error_schema

logger = logging.getLogger(__name__)


class PropertyFileViewSet(
    ListModelMixin, CreateModelMixin, DestroyModelMixin, GenericViewSet
):
    """
    Unified ViewSet for all Property files (images and documents).
    URL must include property_pk (parent) and pk (file).
    """

    permission_classes = [IsAuthenticated, IsSponsor]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = PropertyFileSerializer

    # ── Ownership helper ──────────────────────────────

    def _get_property(self):
        prop = get_object_or_404(
            Property.objects.only("id", "sponsor_id"),
            pk=self.kwargs["property_pk"],
        )
        if (
            prop.sponsor_id != self.request.user.id
            and not self.request.user.is_superuser
        ):
            raise PermissionDenied(
                "You do not have permission to access this property."
            )
        return prop

    # ── Queryset + object lookup ──────────────────────

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return PropertyFile.objects.none()

        return (
            PropertyFile.objects.filter(property=self._get_property())
            .select_related("uploaded_by", "uploaded_by_role")
            .order_by("-uploaded_at")
        )

    def get_object(self):
        return get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])

    # ── List / Destroy ─────────────────────────

    @swagger_auto_schema(
        operation_summary="List property files",
        tags=["Property Files"],
        responses={200: success_schema("Files retrieved successfully.")},
    )
    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            self.get_queryset(), many=True, context={"request": request}
        )
        return Response(
            {"message": "Files retrieved successfully.", "data": serializer.data}
        )

    @swagger_auto_schema(
        operation_summary="Delete a property file",
        tags=["Property Files"],
        responses={
            200: success_schema("File deleted successfully."),
            404: error_schema("Not found."),
        },
    )
    def destroy(self, request, *args, **kwargs):
        self.get_object().delete()
        return Response({"message": "File deleted successfully."})

    @swagger_auto_schema(
        operation_summary="Upload property files (images/documents)",
        tags=["Property Files"],
        manual_parameters=[
            openapi.Parameter(
                "files",
                openapi.IN_FORM,
                description="One or more files (PNG, JPG, PDF, DOCX, XLSX, etc)",
                type=openapi.TYPE_FILE,
                required=True,
            ),
        ],
        responses={
            201: success_schema("File(s) uploaded successfully."),
            400: error_schema("Validation failed."),
        },
    )
    def create(self, request, *args, **kwargs):
        prop = self._get_property()
        files = request.FILES.getlist("files")

        if not files:
            return Response(
                {"message": "No files provided. Use the 'files' field."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        valid_files = []
        errors = []

        IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

        images_to_validate = []
        docs_to_validate = []

        for f in files:
            ext = os.path.splitext(f.name)[1].lstrip(".").lower()
            if ext in IMAGE_EXTENSIONS:
                images_to_validate.append(f)
            else:
                docs_to_validate.append(f)

        if images_to_validate:
            valid_imgs, img_errs = validate_images(images_to_validate)
            valid_files.extend(valid_imgs)
            if img_errs:
                errors.extend(img_errs)

        if docs_to_validate:
            valid_docs, doc_errs = validate_documents(docs_to_validate)
            valid_files.extend(valid_docs)
            if doc_errs:
                errors.extend(doc_errs)

        if not valid_files and errors:
            return Response(
                {
                    "message": "Validation failed. No files were saved.",
                    "errors": errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        sponsor_role = _get_sponsor_role()
        ids = []
        for f in valid_files:
            ext = os.path.splitext(f.name)[1].lstrip(".").lower()
            category = (
                PropertyFile.CATEGORY_IMAGE
                if ext in IMAGE_EXTENSIONS
                else PropertyFile.CATEGORY_DOCUMENT
            )

            pf = PropertyFile.objects.create(
                property=prop,
                file=f,
                category=category,
                file_name=f.name,
                file_type=ext,
                image_source=(
                    PropertyFile.SOURCE_MANUAL
                    if category == PropertyFile.CATEGORY_IMAGE
                    else ""
                ),
                uploaded_by=request.user,
                uploaded_by_role=sponsor_role,
            )
            ids.append(pf.id)

        # Auto-ingest documents via Celery Task
        from properties.tasks import ingest_file_task
        for file_id in ids:
            ingest_file_task.delay(file_id)

        saved_qs = PropertyFile.objects.filter(pk__in=ids).select_related(
            "uploaded_by", "uploaded_by_role"
        )
        serializer = self.get_serializer(
            saved_qs, many=True, context={"request": request}
        )
        return Response(
            {
                "message": f"{len(ids)} file(s) uploaded successfully.",
                "data": serializer.data,
                "errors": errors if errors else None,
            },
            status=status.HTTP_201_CREATED,
        )
