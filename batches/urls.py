from django.urls import path

from .views import (
    BatchArchiveToggleView,
    BatchCreateView,
    BatchDeleteView,
    BatchDetailView,
    BatchListView,
    BatchUpdateView,
    FermentTypeCreateView,
    FermentTypeUpdateView,
    RatioCalculatorView,
    RatioTemplateCreateView,
    RatioTemplateUpdateView,
    ReferenceLibraryView,
)

urlpatterns = [
    path("", BatchListView.as_view(), name="batch_list"),
    path("new/", BatchCreateView.as_view(), name="batch_create"),
    path("<int:pk>/", BatchDetailView.as_view(), name="batch_detail"),
    path("<int:pk>/edit/", BatchUpdateView.as_view(), name="batch_edit"),
    path("<int:pk>/archive/", BatchArchiveToggleView.as_view(), name="batch_archive_toggle"),
    path("<int:pk>/delete/", BatchDeleteView.as_view(), name="batch_delete"),
    path("calculator/", RatioCalculatorView.as_view(), name="ratio_calculator"),
    path("categories/", ReferenceLibraryView.as_view(), name="reference_library"),
    path("categories/new/", FermentTypeCreateView.as_view(), name="ferment_type_create"),
    path(
        "categories/<int:pk>/edit/",
        FermentTypeUpdateView.as_view(),
        name="ferment_type_edit",
    ),
    path("templates/new/", RatioTemplateCreateView.as_view(), name="ratio_template_create"),
    path(
        "templates/<int:pk>/edit/",
        RatioTemplateUpdateView.as_view(),
        name="ratio_template_edit",
    ),
]
