from loan.views.request_views import (
    LoanRequestListCreateView,
    LoanRequestDetailView,
)
from loan.views.quote_views import (
    LoanQuoteListCreateView,
    LenderQuoteListView,
    LoanQuoteDetailView,
    AcceptQuoteView,
    DeclineQuoteView,
)
from loan.views.dashboard_views import (
    LenderDashboardView,
    SponsorDashboardView,
)

__all__ = [
    "LoanRequestListCreateView",
    "LoanRequestDetailView",
    "LoanQuoteListCreateView",
    "LenderQuoteListView",
    "LoanQuoteDetailView",
    "AcceptQuoteView",
    "DeclineQuoteView",
    "LenderDashboardView",
    "SponsorDashboardView",
]
