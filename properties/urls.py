from django.urls import path
from .views import (
    PropertyViewSet,
    PropertyFileViewSet,
    PropertyMapView,
    PlaceView,
    PropertyChatView,
    PropertyChatSessionListView,
    PropertyChatSessionDetailView,
)

app_name = "properties"


# Property (pk = property id)
_property_list = PropertyViewSet.as_view({"get": "list", "post": "create"})
_property_detail = PropertyViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
)

# Files (images and documents unified)
_file_list = PropertyFileViewSet.as_view({"get": "list", "post": "create"})
_file_detail = PropertyFileViewSet.as_view({"delete": "destroy"})

# ── URL patterns

urlpatterns = [
    path("map/", PropertyMapView.as_view(), name="property-map"),
    path("places/", PlaceView.as_view(), name="property-places"),
    path("", _property_list, name="property-list-create"),
    path("<int:pk>/", _property_detail, name="property-detail"),
    path("<int:property_pk>/files/", _file_list, name="property-file-list-create"),
    path(
        "<int:property_pk>/files/<int:pk>/", _file_detail, name="property-file-delete"
    ),
    path("<int:property_pk>/chat/", PropertyChatView.as_view(), name="property-chat"),
    path(
        "<int:property_pk>/chat/sessions/",
        PropertyChatSessionListView.as_view(),
        name="property-chat-session-list",
    ),
    path(
        "<int:property_pk>/chat/sessions/<int:session_id>/",
        PropertyChatSessionDetailView.as_view(),
        name="property-chat-session-detail",
    ),
]
