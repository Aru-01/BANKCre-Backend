from django.urls import path
from loan import views

app_name = "loan"

urlpatterns = [
    path(
        "requests/",
        views.LoanRequestListCreateView.as_view(),
        name="loan-request-list-create",
    ),
    path(
        "requests/<int:pk>/",
        views.LoanRequestDetailView.as_view(),
        name="loan-request-detail",
    ),
    # Quotes scoped to a loan request
    path(
        "requests/<int:pk>/quotes/",
        views.LoanQuoteListCreateView.as_view(),
        name="loan-quote-list-create",
    ),
    # Standalone quote endpoints
    path("quotes/", views.LenderQuoteListView.as_view(), name="lender-quote-list"),
    path(
        "quotes/<int:quote_id>/",
        views.LoanQuoteDetailView.as_view(),
        name="loan-quote-detail",
    ),
    path(
        "quotes/<int:quote_id>/accept/",
        views.AcceptQuoteView.as_view(),
        name="loan-quote-accept",
    ),
    path(
        "quotes/<int:quote_id>/decline/",
        views.DeclineQuoteView.as_view(),
        name="loan-quote-decline",
    ),
    # Dashboards
    path(
        "dashboard/lender/",
        views.LenderDashboardView.as_view(),
        name="lender-dashboard",
    ),
    path(
        "dashboard/sponsor/",
        views.SponsorDashboardView.as_view(),
        name="sponsor-dashboard",
    ),
]
