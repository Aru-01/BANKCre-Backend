from django.db.models import Sum, Count, Min, Max, Q
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from loan.models import LoanRequest, LoanQuote
from loan.serializers import (
    LenderDashboardRequestSerializer,
    SponsorQuoteCardSerializer,
)
from loan.permissions import IsSponsor, IsLender


class LenderDashboardView(APIView):
    """
    GET /api/v1/loans/dashboard/lender/ — Lender dashboard metrics and active loan requests
    """

    permission_classes = [IsAuthenticated, IsLender]

    @swagger_auto_schema(
        operation_summary="Get Lender Dashboard",
        operation_description="Returns aggregated metrics for the lender and a list of active available loan requests (excluding lender's own properties).",
        tags=["Loans Dashboard"],
        responses={
            200: openapi.Response("Lender dashboard retrieved successfully."),
            403: "Lender access required.",
        },
    )
    def get(self, request):
        user = request.user

        # Active loan requests available in the marketplace (excluding own properties)
        available_requests_qs = (
            LoanRequest.objects.filter(status=LoanRequest.STATUS_ACTIVE)
            .exclude(sponsor=user)
            .exclude(property__sponsor=user)
            .select_related("property")
            .prefetch_related("property__files")
        )

        active_requests_count = available_requests_qs.count()

        # Quotes metrics for the logged-in lender
        quotes_stats = LoanQuote.objects.filter(lender=user).aggregate(
            total=Count("id"),
            under_review=Count("id", filter=Q(status=LoanQuote.STATUS_UNDER_REVIEW)),
            accepted=Count("id", filter=Q(status=LoanQuote.STATUS_ACCEPTED)),
        )

        requests_serializer = LenderDashboardRequestSerializer(
            available_requests_qs, many=True, context={"request": request}
        )

        data = {
            "header_stats": {
                "active_requests": active_requests_count,
                "quotes_provided": quotes_stats["total"] or 0,
                "pending_review": quotes_stats["under_review"] or 0,
                "accepted_quotes": quotes_stats["accepted"] or 0,
            },
            "available_loan_requests": requests_serializer.data,
        }
        return Response(
            {
                "message": "Lender dashboard retrieved successfully.",
                "data": data,
            },
            status=status.HTTP_200_OK,
        )


class SponsorDashboardView(APIView):
    """
    GET /api/v1/loans/dashboard/sponsor/ — Sponsor dashboard metrics, quote cards, and comparison
    """

    permission_classes = [IsAuthenticated, IsSponsor]

    @swagger_auto_schema(
        operation_summary="Get Sponsor Dashboard",
        operation_description="Returns sponsor portfolio stats, quote card view, and side-by-side quote comparison metrics.",
        tags=["Loans Dashboard"],
        responses={
            200: openapi.Response("Sponsor dashboard retrieved successfully."),
            403: "Sponsor access required.",
        },
    )
    def get(self, request):
        user = request.user

        total_properties = user.properties.count()
        documents_count = sum(
            p.files.filter(category="document").count() for p in user.properties.all()
        )
        portfolio_value = (
            LoanRequest.objects.filter(
                sponsor=user, status=LoanRequest.STATUS_ACTIVE
            ).aggregate(total=Sum("requested_amount"))["total"]
            or 0
        )

        # All quotes on sponsor's loan requests
        all_quotes = (
            LoanQuote.objects.filter(loan_request__sponsor=user)
            .select_related("loan_request__property", "lender")
            .order_by("-submitted_at")
        )

        quotes_received = all_quotes.count()

        quote_serializer = SponsorQuoteCardSerializer(
            all_quotes, many=True, context={"request": request}
        )
        quote_list = quote_serializer.data

        # Comparison metrics
        comparison_stats = all_quotes.aggregate(
            best_rate=Min("interest_rate"),
            highest_ltv=Max("max_as_is_ltv"),
        )

        data = {
            "header_stats": {
                "total_properties": total_properties,
                "quotes_received": quotes_received,
                "documents_count": documents_count,
                "portfolio_value": portfolio_value,
            },
            "quote_card_view": quote_list,
            "quote_comparison": {
                "total_quotes": quotes_received,
                "best_rate": comparison_stats["best_rate"],
                "highest_ltv": comparison_stats["highest_ltv"],
                "quotes": quote_list,
            },
        }
        return Response(
            {
                "message": "Sponsor dashboard retrieved successfully.",
                "data": data,
            },
            status=status.HTTP_200_OK,
        )
