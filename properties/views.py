import logging
import os

from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.mixins import ListModelMixin, CreateModelMixin, DestroyModelMixin
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework import status
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from accounts.models import RoleModel, Role
from .models import Property, PropertyFile, PropertyChatSession, PropertyChatMessage
from .serializers import (
    PropertySerializer, PropertyListSerializer, PropertyMapSerializer,
    PropertyFileSerializer,
    PropertyChatSessionSerializer, PropertyChatMessageSerializer,
    PropertyChatInputSerializer, PlaceSerializer,
)
from .permissions import IsSponsor, IsLender
from .validators import validate_documents, validate_images
from .chatbot import ask, ingest_file

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────
# Swagger schema helpers  (same pattern as accounts)
# ──────────────────────────────────────────────────────

def success_schema(description='Success'):
    return openapi.Response(description, openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'message': openapi.Schema(type=openapi.TYPE_STRING),
            'data':    openapi.Schema(type=openapi.TYPE_OBJECT),
        },
    ))


def error_schema(description='Error'):
    return openapi.Response(description, openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'message': openapi.Schema(type=openapi.TYPE_STRING),
            'errors':  openapi.Schema(type=openapi.TYPE_OBJECT),
        },
    ))


# ──────────────────────────────────────────────────────
# Shared helper
# ──────────────────────────────────────────────────────

def _get_sponsor_role():
    """Return the Sponsor RoleModel (or None if not yet seeded)."""
    return RoleModel.objects.filter(name=Role.SPONSOR).first()


# ══════════════════════════════════════════════════════
# Property ViewSet  (Sponsor CRUD)
# ══════════════════════════════════════════════════════

class PropertyViewSet(ModelViewSet):
    """
    Full CRUD for the requesting Sponsor's own properties.
    get_queryset() already filters by sponsor, so every object
    access is automatically ownership-checked.
    """
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    permission_classes = [IsAuthenticated, IsSponsor]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        return PropertyListSerializer if self.action == 'list' else PropertySerializer

    def get_queryset(self):
        qs = Property.objects.select_related('sponsor', 'sponsor_role')
        
        # Superuser can see everything; regular Sponsor only sees their own
        if not self.request.user.is_superuser:
            qs = qs.filter(sponsor=self.request.user)
            
        # Only prefetch heavy file relations when actually needed
        if self.action in ('retrieve', 'partial_update', 'destroy'):
            return qs.prefetch_related(
                'files',
                'files__uploaded_by',
                'files__uploaded_by_role',
            )
        return qs.prefetch_related('files')

    def perform_create(self, serializer):
        serializer.save(sponsor=self.request.user, sponsor_role=_get_sponsor_role())

    # ── Swagger-decorated action overrides ────────────────────

    @swagger_auto_schema(
        operation_summary='List my properties',
        tags=['Properties'],
        responses={200: success_schema('Properties retrieved successfully.')},
    )
    def list(self, request, *args, **kwargs):
        qs = self.get_queryset().order_by('-created_at')
        serializer = self.get_serializer(qs, many=True, context={'request': request})
        return Response({'message': 'Properties retrieved successfully.', 'data': serializer.data})

    @swagger_auto_schema(
        operation_summary='Create a property',
        tags=['Properties'],
        request_body=PropertySerializer,
        responses={
            201: success_schema('Property created successfully.'),
            400: error_schema('Validation failed.'),
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(
                {'message': 'Property creation failed.', 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_create(serializer)
        return Response(
            {'message': 'Property created successfully.', 'data': serializer.data},
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary='Get property detail',
        tags=['Properties'],
        responses={
            200: success_schema('Property retrieved successfully.'),
            404: error_schema('Not found.'),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object(), context={'request': request})
        return Response({'message': 'Property retrieved successfully.', 'data': serializer.data})

    @swagger_auto_schema(
        operation_summary='Update a property (partial)',
        tags=['Properties'],
        request_body=PropertySerializer,
        responses={
            200: success_schema('Property updated successfully.'),
            400: error_schema('Validation failed.'),
        },
    )
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=True, context={'request': request}
        )
        if not serializer.is_valid():
            return Response(
                {'message': 'Property update failed.', 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        return Response({'message': 'Property updated successfully.', 'data': serializer.data})

    @swagger_auto_schema(
        operation_summary='Delete a property',
        tags=['Properties'],
        responses={200: success_schema('Property deleted successfully.')},
    )
    def destroy(self, request, *args, **kwargs):
        self.get_object().delete()
        return Response({'message': 'Property deleted successfully.'})


# ══════════════════════════════════════════════════════
# PropertyFile base ViewSet  (shared by Image & Document viewsets)
# ══════════════════════════════════════════════════════

class PropertyFileViewSet(ListModelMixin, CreateModelMixin, DestroyModelMixin, GenericViewSet):
    """
    Base ViewSet for PropertyFile endpoints.
    Subclasses set FILE_CATEGORY = PropertyFile.CATEGORY_IMAGE or CATEGORY_DOCUMENT.
    URL must include property_pk (parent) and pk (file).
    """
    permission_classes = [IsAuthenticated, IsSponsor]
    parser_classes     = [MultiPartParser, FormParser]
    serializer_class   = PropertyFileSerializer
    FILE_CATEGORY      = None   # overridden in subclasses

    # ── Ownership helper ──────────────────────────────

    def _get_property(self):
        """
        Lightweight property fetch + sponsor ownership check.
        Raises PermissionDenied if the requesting user doesn't own the property.
        """
        prop = get_object_or_404(
            Property.objects.only('id', 'sponsor_id'),
            pk=self.kwargs['property_pk'],
        )
        if prop.sponsor_id != self.request.user.id and not self.request.user.is_superuser:
            raise PermissionDenied('You do not have permission to access this property.')
        return prop

    # ── Queryset + object lookup ──────────────────────

    def get_queryset(self):
        return (
            PropertyFile.objects
            .filter(property=self._get_property(), category=self.FILE_CATEGORY)
            .select_related('uploaded_by', 'uploaded_by_role')
            .order_by('uploaded_at')
        )

    def get_object(self):
        """Lookup file by pk within the already-filtered queryset."""
        return get_object_or_404(self.get_queryset(), pk=self.kwargs['pk'])

    # ── Shared list / destroy ─────────────────────────

    def list(self, request, *args, **kwargs):
        label = 'Images' if self.FILE_CATEGORY == PropertyFile.CATEGORY_IMAGE else 'Documents'
        serializer = self.get_serializer(
            self.get_queryset(), many=True, context={'request': request}
        )
        return Response({'message': f'{label} retrieved successfully.', 'data': serializer.data})

    def destroy(self, request, *args, **kwargs):
        label = 'Image' if self.FILE_CATEGORY == PropertyFile.CATEGORY_IMAGE else 'Document'
        self.get_object().delete()
        return Response({'message': f'{label} deleted successfully.'})


# ── Image ViewSet ─────────────────────────────────────

class PropertyImageViewSet(PropertyFileViewSet):
    FILE_CATEGORY = PropertyFile.CATEGORY_IMAGE

    @swagger_auto_schema(
        operation_summary='List property images',
        tags=['Property Files'],
        responses={200: success_schema('Images retrieved successfully.')},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary='Upload property images',
        tags=['Property Files'],
        manual_parameters=[
            openapi.Parameter(
                'images', openapi.IN_FORM,
                description='One or more image files (PNG, JPG, JPEG, WEBP, GIF)',
                type=openapi.TYPE_FILE, required=True,
            ),
        ],
        responses={
            201: success_schema('Image(s) uploaded successfully.'),
            400: error_schema('Validation failed.'),
        },
    )
    def create(self, request, *args, **kwargs):
        prop  = self._get_property()
        files = request.FILES.getlist('images')

        if not files:
            return Response(
                {'message': "No images provided. Use the 'images' field."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        valid_files, errors = validate_images(files)
        if errors:
            return Response(
                {'message': 'Validation failed. No files were saved.', 'errors': errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sponsor_role = _get_sponsor_role()
        ids = []
        for f in valid_files:
            ext = os.path.splitext(f.name)[1].lstrip('.').lower()
            pf  = PropertyFile.objects.create(
                property         = prop,
                file             = f,
                category         = PropertyFile.CATEGORY_IMAGE,
                file_name        = f.name,
                file_type        = ext,
                image_source     = PropertyFile.SOURCE_MANUAL,
                uploaded_by      = request.user,
                uploaded_by_role = sponsor_role,
            )
            ids.append(pf.id)

        # Re-fetch with select_related for clean serializer output
        saved_qs   = PropertyFile.objects.filter(pk__in=ids).select_related('uploaded_by', 'uploaded_by_role')
        serializer = self.get_serializer(saved_qs, many=True, context={'request': request})
        return Response(
            {'message': f'{len(ids)} image(s) uploaded successfully.', 'data': serializer.data},
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary='Delete a property image',
        tags=['Property Files'],
        responses={200: success_schema('Image deleted successfully.'), 404: error_schema('Not found.')},
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


# ── Document ViewSet ──────────────────────────────────

class PropertyDocumentViewSet(PropertyFileViewSet):
    FILE_CATEGORY = PropertyFile.CATEGORY_DOCUMENT

    @swagger_auto_schema(
        operation_summary='List property documents',
        tags=['Property Files'],
        responses={200: success_schema('Documents retrieved successfully.')},
    )
    def list(self, request, *args, **kwargs):
        # Documents default to newest first
        qs = self.get_queryset().order_by('-uploaded_at')
        serializer = self.get_serializer(qs, many=True, context={'request': request})
        return Response({'message': 'Documents retrieved successfully.', 'data': serializer.data})

    @swagger_auto_schema(
        operation_summary='Upload property documents',
        tags=['Property Files'],
        manual_parameters=[
            openapi.Parameter(
                'files', openapi.IN_FORM,
                description='One or more files (PDF, DOCX, XLSX, PPTX, TXT, CSV)',
                type=openapi.TYPE_FILE, required=True,
            ),
        ],
        responses={
            201: success_schema('Document(s) uploaded and indexed for AI.'),
            400: error_schema('Validation failed.'),
        },
    )
    def create(self, request, *args, **kwargs):
        prop  = self._get_property()
        files = request.FILES.getlist('files')

        if not files:
            return Response(
                {'message': "No files provided. Use the 'files' field."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        valid_files, errors = validate_documents(files)
        if errors:
            return Response(
                {'message': 'Validation failed. No files were saved.', 'errors': errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sponsor_role = _get_sponsor_role()
        ids = []
        for f in valid_files:
            ext = os.path.splitext(f.name)[1].lstrip('.').lower()
            pf  = PropertyFile.objects.create(
                property         = prop,
                file             = f,
                category         = PropertyFile.CATEGORY_DOCUMENT,
                file_name        = f.name,
                file_type        = ext,
                uploaded_by      = request.user,
                uploaded_by_role = sponsor_role,
            )
            ids.append(pf.id)

        # Auto-ingest: chunk + embed for AI context (synchronous)
        for file_id in ids:
            try:
                ingest_file(file_id)
            except Exception as exc:
                logger.warning('ingest_file failed for file %s: %s', file_id, exc)

        # Re-fetch with select_related for clean serializer output
        saved_qs   = PropertyFile.objects.filter(pk__in=ids).select_related('uploaded_by', 'uploaded_by_role')
        serializer = self.get_serializer(saved_qs, many=True, context={'request': request})
        return Response(
            {'message': f'{len(ids)} document(s) uploaded successfully.', 'data': serializer.data},
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_summary='Delete a property document',
        tags=['Property Files'],
        responses={200: success_schema('Document deleted successfully.'), 404: error_schema('Not found.')},
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


# ══════════════════════════════════════════════════════
# Map view  (Lender read-only)
# ══════════════════════════════════════════════════════

class PropertyMapView(APIView):
    """Lightweight map-marker data for the Lender's map view."""
    permission_classes = [IsAuthenticated, IsLender]

    @swagger_auto_schema(
        operation_summary='Get all properties for map',
        tags=['Properties'],
        responses={
            200: success_schema('Properties retrieved successfully.'),
            403: error_schema('Lender access required.'),
        },
    )
    def get(self, request):
        props = (
            Property.objects
            .only('id', 'property_name', 'property_address', 'property_type', 'latitude', 'longitude')
            .prefetch_related('files')
        )
        serializer = PropertyMapSerializer(props, many=True, context={'request': request})
        return Response({'message': 'Properties retrieved successfully.', 'data': serializer.data})


# ══════════════════════════════════════════════════════
# Place view  (map handoff — validate & return)
# ══════════════════════════════════════════════════════

class PlaceView(APIView):
    """
    Validates Google Maps place data from the frontend.
    Frontend uses the response to pre-fill the property form,
    then POSTs to /properties/ separately.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary='Validate & return map place data',
        tags=['Properties'],
        request_body=PlaceSerializer,
        responses={
            200: success_schema('Place data received successfully.'),
            400: error_schema('Invalid place data.'),
        },
    )
    def post(self, request):
        serializer = PlaceSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'message': 'Invalid place data.', 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({'message': 'Place data received successfully.', 'data': serializer.validated_data})


# ══════════════════════════════════════════════════════
# AI Chat  (OpenAI gpt-4o-mini, all property docs in context)
# ══════════════════════════════════════════════════════

class PropertyChatView(APIView):
    """
    Send a chat message about a property.
    ALL uploaded documents for the property are automatically used as AI context.
    No per-document selection needed — just select a property and chat.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary='Send a chat message about a property',
        tags=['Property Chat'],
        request_body=PropertyChatInputSerializer,
        responses={
            201: openapi.Response(
                'Message sent successfully.',
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message':    openapi.Schema(type=openapi.TYPE_STRING),
                        'session_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'reply':      openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            400: error_schema('Invalid request.'),
            503: error_schema('AI service unavailable.'),
        },
    )
    def post(self, request, property_pk):
        prop = get_object_or_404(Property.objects.only('id', 'property_name'), pk=property_pk)

        serializer = PropertyChatInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'message': 'Invalid request.', 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_message = serializer.validated_data['message']
        session_id   = serializer.validated_data.get('session_id')

        # ── Resolve or create session ───────────────────────────
        if session_id:
            session = get_object_or_404(
                PropertyChatSession.objects.select_related('user'),
                pk=session_id, property=prop,
            )
            if session.user_id != request.user.id and not request.user.is_superuser:
                return Response(
                    {'detail': 'You do not have permission to access this session.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
        else:
            session = PropertyChatSession.objects.create(property=prop, user=request.user)

        # Build history BEFORE saving the new user message (correct order)
        history = list(session.messages.order_by('created_at').values('role', 'content'))

        # Persist user message
        PropertyChatMessage.objects.create(session=session, role='user', content=user_message)

        # ── Call AI ─────────────────────────────────────────────
        try:
            reply = ask(prop.id, user_message, history)
        except RuntimeError:
            return Response(
                {'message': 'AI service is temporarily unavailable. Please try again later.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as exc:
            logger.exception('Unexpected chatbot error: %s', exc)
            return Response(
                {'message': 'An unexpected error occurred.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Persist assistant reply
        PropertyChatMessage.objects.create(session=session, role='assistant', content=reply)

        # Auto-set title from first user message
        if not history:
            session.title = user_message[:60].strip()
        session.save(update_fields=['title', 'updated_at'])

        return Response(
            {'message': 'Message sent successfully.', 'session_id': session.id, 'reply': reply},
            status=status.HTTP_201_CREATED,
        )


class PropertyChatSessionListView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary='List chat sessions for a property',
        tags=['Property Chat'],
        responses={200: success_schema('Chat sessions retrieved successfully.')},
    )
    def get(self, request, property_pk):
        prop     = get_object_or_404(Property.objects.only('id'), pk=property_pk)
        
        sessions = PropertyChatSession.objects.filter(property=prop)
        if not request.user.is_superuser:
            sessions = sessions.filter(user=request.user)
            
        sessions = (
            sessions
            .only('id', 'property_id', 'title', 'created_at', 'updated_at')
            .order_by('-updated_at')
        )
        return Response({
            'message': 'Chat sessions retrieved successfully.',
            'data':    PropertyChatSessionSerializer(sessions, many=True).data,
        })

    @swagger_auto_schema(
        operation_summary='Create a new chat session',
        tags=['Property Chat'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={'title': openapi.Schema(type=openapi.TYPE_STRING, description='Optional title')},
        ),
        responses={201: success_schema('Chat session created successfully.')},
    )
    def post(self, request, property_pk):
        prop    = get_object_or_404(Property.objects.only('id'), pk=property_pk)
        session = PropertyChatSession.objects.create(
            property = prop,
            user     = request.user,
            title    = request.data.get('title', '').strip() or 'New Chat',
        )
        return Response(
            {'message': 'Chat session created successfully.', 'data': PropertyChatSessionSerializer(session).data},
            status=status.HTTP_201_CREATED,
        )


class PropertyChatSessionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_session(self, request, property_pk, session_id):
        prop    = get_object_or_404(Property.objects.only('id'), pk=property_pk)
        session = get_object_or_404(
            PropertyChatSession.objects.select_related('user'),
            pk=session_id, property=prop,
        )
        if session.user_id != request.user.id and not request.user.is_superuser:
            return None, Response(
                {'detail': 'You do not have permission to access this session.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return session, None

    @swagger_auto_schema(
        operation_summary='Get messages in a chat session',
        tags=['Property Chat'],
        responses={
            200: success_schema('Messages retrieved successfully.'),
            403: error_schema('Permission denied.'),
        },
    )
    def get(self, request, property_pk, session_id):
        session, err = self._get_session(request, property_pk, session_id)
        if err:
            return err
        return Response({
            'message': 'Messages retrieved successfully.',
            'data':    PropertyChatMessageSerializer(session.messages.all(), many=True).data,
        })

    @swagger_auto_schema(
        operation_summary='Delete a chat session',
        tags=['Property Chat'],
        responses={
            200: success_schema('Chat session deleted successfully.'),
            403: error_schema('Permission denied.'),
        },
    )
    def delete(self, request, property_pk, session_id):
        session, err = self._get_session(request, property_pk, session_id)
        if err:
            return err
        session.delete()
        return Response({'message': 'Chat session deleted successfully.'})
