from django.urls import path
from .views import (
    PropertyViewSet,
    PropertyImageViewSet,
    PropertyDocumentViewSet,
    PropertyMapView,
    PlaceView,
    PropertyChatView,
    PropertyChatSessionListView,
    PropertyChatSessionDetailView,
)

app_name = 'properties'

# ── ViewSet method → HTTP verb mappings ───────────────────────

# Property (pk = property id)
_property_list   = PropertyViewSet.as_view({'get': 'list',     'post': 'create'})
_property_detail = PropertyViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'})

# Images (property_pk = parent property, pk = image id)
_image_list   = PropertyImageViewSet.as_view({'get': 'list', 'post': 'create'})
_image_detail = PropertyImageViewSet.as_view({'delete': 'destroy'})

# Documents (property_pk = parent property, pk = document id)
_doc_list   = PropertyDocumentViewSet.as_view({'get': 'list', 'post': 'create'})
_doc_detail = PropertyDocumentViewSet.as_view({'delete': 'destroy'})

# ── URL patterns ───────────────────────────────────────────────

urlpatterns = [
    # Map & Places  (no property_pk prefix — must come BEFORE <int:pk>/)
    path('map/',    PropertyMapView.as_view(), name='property-map'),
    path('places/', PlaceView.as_view(),       name='property-places'),

    # Property CRUD
    path('',          _property_list,   name='property-list-create'),
    path('<int:pk>/', _property_detail, name='property-detail'),

    # Images  (key: 'images')
    path('<int:property_pk>/images/',           _image_list,   name='property-image-list-create'),
    path('<int:property_pk>/images/<int:pk>/',  _image_detail, name='property-image-delete'),

    # Documents  (key: 'files')
    path('<int:property_pk>/documents/',           _doc_list,   name='property-document-list-create'),
    path('<int:property_pk>/documents/<int:pk>/',  _doc_detail, name='property-document-delete'),

    # AI Chat
    path('<int:property_pk>/chat/',                              PropertyChatView.as_view(),              name='property-chat'),
    path('<int:property_pk>/chat/sessions/',                     PropertyChatSessionListView.as_view(),   name='property-chat-session-list'),
    path('<int:property_pk>/chat/sessions/<int:session_id>/',    PropertyChatSessionDetailView.as_view(), name='property-chat-session-detail'),
]
