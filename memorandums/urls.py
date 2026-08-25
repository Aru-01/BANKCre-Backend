from django.urls import path
from memorandums.views import (
    GenerateMemorandumView,
    MemorandumListView,
    MemorandumDetailView,
    MemorandumSectionUpdateView,
    MemorandumSectionRegenerateView,
    SectionImageView,
)

app_name = "memorandums"

urlpatterns = [
    path("generate/", GenerateMemorandumView.as_view(), name="memorandum-generate"),
    path("", MemorandumListView.as_view(), name="memorandum-list"),
    path("<int:pk>/", MemorandumDetailView.as_view(), name="memorandum-detail"),
    path(
        "<int:pk>/sections/<int:section_id>/",
        MemorandumSectionUpdateView.as_view(),
        name="memorandum-section-update",
    ),
    path(
        "<int:pk>/sections/<int:section_id>/regenerate/",
        MemorandumSectionRegenerateView.as_view(),
        name="memorandum-section-regenerate",
    ),
    path(
        "<int:pk>/sections/<int:section_id>/image/",
        SectionImageView.as_view(),
        name="memorandum-section-image",
    ),
]
