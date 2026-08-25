import os
import logging
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from properties.models import Property
from memorandums.models import Memorandum, MemorandumSection
from memorandums.serializers import (
    GenerateMemorandumSerializer,
    MemorandumListSerializer,
    MemorandumDetailSerializer,
    MemorandumUpdateSerializer,
    MemorandumSectionUpdateSerializer,
    SectionImageSerializer,
    RegenerateSectionSerializer,
)
from memorandums.permissions import IsSponsor, IsMemorandumOwner

logger = logging.getLogger(__name__)


# ─── Helpers


def _get_memorandum_or_403(request, pk):
    """Fetch memorandum and check ownership. Returns (memorandum, error_response)."""
    memorandum = get_object_or_404(
        Memorandum.objects.select_related("property", "sponsor"), pk=pk
    )
    perm = IsMemorandumOwner()
    if not perm.has_object_permission(request, None, memorandum):
        return None, Response(
            {"message": "You do not have permission to access this memorandum."},
            status=status.HTTP_403_FORBIDDEN,
        )
    return memorandum, None


def _get_section(memorandum, section_id):
    return get_object_or_404(MemorandumSection, pk=section_id, memorandum=memorandum)


# ─── Common Schema Definitions for Swagger

MEMORANDUM_LIST_RESPONSE = openapi.Response(
    "List of memorandums retrieved successfully.",
    openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "message": openapi.Schema(type=openapi.TYPE_STRING),
            "data": openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "property": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "property_name": openapi.Schema(type=openapi.TYPE_STRING),
                        "title": openapi.Schema(type=openapi.TYPE_STRING),
                        "status": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            enum=["Generating", "Draft", "Failed", "Published"],
                        ),
                        "mode": openapi.Schema(
                            type=openapi.TYPE_STRING, enum=["Editor", "Preview"]
                        ),
                        "section_count": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "created_at": openapi.Schema(
                            type=openapi.TYPE_STRING, format="date-time"
                        ),
                        "updated_at": openapi.Schema(
                            type=openapi.TYPE_STRING, format="date-time"
                        ),
                    },
                ),
            ),
        },
    ),
)


MEMORANDUM_DETAIL_RESPONSE = openapi.Response(
    "Memorandum detail retrieved successfully.",
    openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "message": openapi.Schema(type=openapi.TYPE_STRING),
            "data": openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "property": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "property_name": openapi.Schema(type=openapi.TYPE_STRING),
                    "title": openapi.Schema(type=openapi.TYPE_STRING),
                    "status": openapi.Schema(type=openapi.TYPE_STRING),
                    "mode": openapi.Schema(type=openapi.TYPE_STRING),
                    "created_at": openapi.Schema(
                        type=openapi.TYPE_STRING, format="date-time"
                    ),
                    "updated_at": openapi.Schema(
                        type=openapi.TYPE_STRING, format="date-time"
                    ),
                    "sections": openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                "section_key": openapi.Schema(type=openapi.TYPE_STRING),
                                "label": openapi.Schema(type=openapi.TYPE_STRING),
                                "section_type": openapi.Schema(
                                    type=openapi.TYPE_STRING, enum=["text", "table"]
                                ),
                                "is_regeneratable": openapi.Schema(
                                    type=openapi.TYPE_BOOLEAN,
                                    description="True if AI regeneration is allowed",
                                ),
                                "content": openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    description="Populated for text sections",
                                ),
                                "table_data": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    description="Populated for table sections",
                                    properties={
                                        "columns": openapi.Schema(
                                            type=openapi.TYPE_ARRAY,
                                            items=openapi.Schema(
                                                type=openapi.TYPE_STRING
                                            ),
                                        ),
                                        "rows": openapi.Schema(
                                            type=openapi.TYPE_ARRAY,
                                            items=openapi.Schema(
                                                type=openapi.TYPE_ARRAY,
                                                items=openapi.Schema(
                                                    type=openapi.TYPE_STRING
                                                ),
                                            ),
                                        ),
                                    },
                                ),
                                "image": openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    format="uri",
                                    nullable=True,
                                ),
                                "order": openapi.Schema(type=openapi.TYPE_INTEGER),
                            },
                        ),
                    ),
                },
            ),
        },
    ),
)


class GenerateMemorandumView(APIView):
    """
    POST /memorandums/generate/
    Trigger AI generation of an Offering Memorandum for a property.
    Runs asynchronously via Celery. Immediately returns memorandum_id and status='Generating'.
    """

    permission_classes = [IsAuthenticated, IsSponsor]

    @swagger_auto_schema(
        operation_summary="Generate a Memorandum for a property",
        tags=["Memorandums"],
        request_body=GenerateMemorandumSerializer,
        responses={
            201: openapi.Response(
                "Generation started successfully.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="Memorandum generation started.",
                        ),
                        "memorandum_id": openapi.Schema(
                            type=openapi.TYPE_INTEGER, example=1
                        ),
                        "status": openapi.Schema(
                            type=openapi.TYPE_STRING, example="Generating"
                        ),
                    },
                ),
            ),
            400: openapi.Response(
                "Validation error.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "errors": openapi.Schema(type=openapi.TYPE_OBJECT),
                    },
                ),
            ),
            403: openapi.Response(
                "Permission denied.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={"message": openapi.Schema(type=openapi.TYPE_STRING)},
                ),
            ),
        },
    )
    def post(self, request):
        serializer = GenerateMemorandumSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"message": "Invalid request.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        property_id = serializer.validated_data["property_id"]
        prop = get_object_or_404(Property, pk=property_id)

        # Ownership check
        if prop.sponsor_id != request.user.id and not request.user.is_superuser:
            return Response(
                {
                    "message": "You do not have permission to generate a memorandum for this property."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        memorandum = Memorandum.objects.create(
            property=prop,
            sponsor=request.user,
            title=f"{prop.property_name} — Offering Memorandum",
            status=Memorandum.STATUS_GENERATING,
            mode="Editor",
        )

        from memorandums.tasks import generate_memorandum_task

        generate_memorandum_task.delay(memorandum.id)

        return Response(
            {
                "message": "Memorandum generation started.",
                "memorandum_id": memorandum.id,
                "status": memorandum.status,
            },
            status=status.HTTP_201_CREATED,
        )


class MemorandumListView(APIView):
    """
    GET /memorandums/
    List all memorandums owned by the requesting Sponsor.
    Superusers see all.
    """

    permission_classes = [IsAuthenticated, IsSponsor]

    @swagger_auto_schema(
        operation_summary="List my memorandums",
        tags=["Memorandums"],
        responses={200: MEMORANDUM_LIST_RESPONSE},
    )
    def get(self, request):
        qs = Memorandum.objects.select_related("property", "sponsor").prefetch_related(
            "sections"
        )
        if not request.user.is_superuser:
            qs = qs.filter(sponsor=request.user)
        serializer = MemorandumListSerializer(qs, many=True)
        return Response(
            {"message": "Memorandums retrieved successfully.", "data": serializer.data}
        )


class MemorandumDetailView(APIView):
    """
    GET    /memorandums/<id>/  — detail with all sections (any authenticated user can read)
    PATCH  /memorandums/<id>/  — update title or mode (sponsor only)
    DELETE /memorandums/<id>/  — delete (sponsor only)
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsSponsor()]

    @swagger_auto_schema(
        operation_summary="Get memorandum detail with all sections",
        tags=["Memorandums"],
        responses={200: MEMORANDUM_DETAIL_RESPONSE, 404: "Not found."},
    )
    def get(self, request, pk):
        memorandum = get_object_or_404(
            Memorandum.objects.select_related("property").prefetch_related("sections"),
            pk=pk,
        )
        serializer = MemorandumDetailSerializer(
            memorandum, context={"request": request}
        )
        return Response(
            {"message": "Memorandum retrieved successfully.", "data": serializer.data}
        )

    @swagger_auto_schema(
        operation_summary="Update memorandum title or mode",
        tags=["Memorandums"],
        request_body=MemorandumUpdateSerializer,
        responses={
            200: openapi.Response(
                "Updated successfully.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="Memorandum updated successfully.",
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "title": openapi.Schema(type=openapi.TYPE_STRING),
                                "mode": openapi.Schema(type=openapi.TYPE_STRING),
                            },
                        ),
                    },
                ),
            ),
            400: "Validation error.",
            403: "Permission denied.",
        },
    )
    def patch(self, request, pk):
        memorandum, err = _get_memorandum_or_403(request, pk)
        if err:
            return err
        serializer = MemorandumUpdateSerializer(
            memorandum, data=request.data, partial=True
        )
        if not serializer.is_valid():
            return Response(
                {"message": "Update failed.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        return Response(
            {"message": "Memorandum updated successfully.", "data": serializer.data}
        )

    @swagger_auto_schema(
        operation_summary="Delete a memorandum",
        tags=["Memorandums"],
        responses={
            200: openapi.Response(
                "Deleted successfully.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="Memorandum deleted successfully.",
                        )
                    },
                ),
            ),
            403: "Permission denied.",
        },
    )
    def delete(self, request, pk):
        memorandum, err = _get_memorandum_or_403(request, pk)
        if err:
            return err
        memorandum.delete()
        return Response({"message": "Memorandum deleted successfully."})


class MemorandumSectionUpdateView(APIView):
    """
    PATCH /memorandums/<pk>/sections/<section_id>/
    Manual edit of a TEXT section's content.
    Table sections cannot be manually edited.
    """

    permission_classes = [IsAuthenticated, IsSponsor]

    @swagger_auto_schema(
        operation_summary="Manually edit a section's content",
        tags=["Memorandum Sections"],
        manual_parameters=[
            openapi.Parameter(
                "pk",
                openapi.IN_PATH,
                description="Memorandum ID",
                type=openapi.TYPE_INTEGER,
            ),
            openapi.Parameter(
                "section_id",
                openapi.IN_PATH,
                description="Section ID",
                type=openapi.TYPE_INTEGER,
            ),
        ],
        request_body=MemorandumSectionUpdateSerializer,
        responses={
            200: openapi.Response(
                "Section updated successfully.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="Section updated successfully.",
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "content": openapi.Schema(type=openapi.TYPE_STRING)
                            },
                        ),
                    },
                ),
            ),
            400: "Validation error (e.g. trying to edit a table section).",
            403: "Permission denied.",
        },
    )
    def patch(self, request, pk, section_id):
        memorandum, err = _get_memorandum_or_403(request, pk)
        if err:
            return err
        section = _get_section(memorandum, section_id)
        serializer = MemorandumSectionUpdateSerializer(
            section, data=request.data, partial=True
        )
        if not serializer.is_valid():
            return Response(
                {"message": "Section update failed.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        return Response(
            {"message": "Section updated successfully.", "data": serializer.data}
        )


class MemorandumSectionRegenerateView(APIView):
    """
    POST /memorandums/<pk>/sections/<section_id>/regenerate/
    AI regenerate a single TEXT section (optionally with a custom instruction).
    Table sections are NOT allowed.
    """

    permission_classes = [IsAuthenticated, IsSponsor]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    @swagger_auto_schema(
        operation_summary="AI regenerate a single text section",
        tags=["Memorandum Sections"],
        manual_parameters=[
            openapi.Parameter(
                "pk",
                openapi.IN_PATH,
                description="Memorandum ID",
                type=openapi.TYPE_INTEGER,
            ),
            openapi.Parameter(
                "section_id",
                openapi.IN_PATH,
                description="Section ID",
                type=openapi.TYPE_INTEGER,
            ),
        ],
        request_body=RegenerateSectionSerializer,
        responses={
            202: openapi.Response(
                "Regeneration task started.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="Section regeneration started.",
                        ),
                        "section_id": openapi.Schema(
                            type=openapi.TYPE_INTEGER, example=10
                        ),
                        "section_key": openapi.Schema(
                            type=openapi.TYPE_STRING, example="executive_summary"
                        ),
                        "status": openapi.Schema(
                            type=openapi.TYPE_STRING, example="processing"
                        ),
                    },
                ),
            ),
            400: "Validation error or attempting to regenerate a table section.",
            403: "Permission denied.",
        },
    )
    def post(self, request, pk, section_id):
        memorandum, err = _get_memorandum_or_403(request, pk)
        if err:
            return err
        section = _get_section(memorandum, section_id)

        if not section.is_regeneratable:
            return Response(
                {
                    "message": (
                        f"Section '{section.section_key}' cannot be regenerated via AI. "
                        "Only narrative text sections can be regenerated."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Allow empty body or dictionary
        req_data = request.data if request.data else {}
        serializer = RegenerateSectionSerializer(data=req_data)
        if not serializer.is_valid():
            return Response(
                {"message": "Invalid request.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        custom_instruction = serializer.validated_data.get("custom_instruction", "")

        from memorandums.tasks import regenerate_section_task

        regenerate_section_task.delay(memorandum.id, section.id, custom_instruction)

        return Response(
            {
                "message": "Section regeneration started.",
                "section_id": section.id,
                "section_key": section.section_key,
                "status": "processing",
            },
            status=status.HTTP_202_ACCEPTED,
        )


class SectionImageView(APIView):
    """
    POST   /memorandums/<pk>/sections/<section_id>/image/  — upload image
    DELETE /memorandums/<pk>/sections/<section_id>/image/  — delete image
    """

    permission_classes = [IsAuthenticated, IsSponsor]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_summary="Upload an image for a section",
        tags=["Memorandum Sections"],
        manual_parameters=[
            openapi.Parameter(
                "pk",
                openapi.IN_PATH,
                description="Memorandum ID",
                type=openapi.TYPE_INTEGER,
            ),
            openapi.Parameter(
                "section_id",
                openapi.IN_PATH,
                description="Section ID",
                type=openapi.TYPE_INTEGER,
            ),
            openapi.Parameter(
                name="image",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                required=True,
                description="The image file to upload",
            ),
        ],
        responses={
            201: openapi.Response(
                "Image uploaded successfully.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="Section image uploaded successfully.",
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "image": openapi.Schema(
                                    type=openapi.TYPE_STRING, format="uri"
                                )
                            },
                        ),
                    },
                ),
            ),
            400: "Validation error.",
            403: "Permission denied.",
        },
    )
    def post(self, request, pk, section_id):
        memorandum, err = _get_memorandum_or_403(request, pk)
        if err:
            return err
        section = _get_section(memorandum, section_id)
        serializer = SectionImageSerializer(section, data=request.data)
        if not serializer.is_valid():
            return Response(
                {"message": "Image upload failed.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Delete old image file from disk before replacing
        if section.image:
            try:
                if os.path.isfile(section.image.path):
                    os.remove(section.image.path)
            except (ValueError, OSError):
                pass
            section.image = None
            section.save(update_fields=["image"])

        serializer.save()
        return Response(
            {
                "message": "Section image uploaded successfully.",
                "data": SectionImageSerializer(
                    section, context={"request": request}
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary="Delete a section image",
        tags=["Memorandum Sections"],
        manual_parameters=[
            openapi.Parameter(
                "pk",
                openapi.IN_PATH,
                description="Memorandum ID",
                type=openapi.TYPE_INTEGER,
            ),
            openapi.Parameter(
                "section_id",
                openapi.IN_PATH,
                description="Section ID",
                type=openapi.TYPE_INTEGER,
            ),
        ],
        responses={
            200: openapi.Response(
                "Image deleted successfully.",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            example="Section image deleted successfully.",
                        )
                    },
                ),
            ),
            404: "Image not found.",
            403: "Permission denied.",
        },
    )
    def delete(self, request, pk, section_id):
        memorandum, err = _get_memorandum_or_403(request, pk)
        if err:
            return err
        section = _get_section(memorandum, section_id)

        if not section.image:
            return Response(
                {"message": "This section has no image to delete."},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            if os.path.isfile(section.image.path):
                os.remove(section.image.path)
        except (ValueError, OSError):
            pass
        section.image = None
        section.save(update_fields=["image"])
        return Response({"message": "Section image deleted successfully."})
