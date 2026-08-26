from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from accounts.models import Role, RoleModel
from loan.models import LoanRequest, LoanQuote
from loan.serializers import (
    LoanQuoteCreateSerializer,
    LoanQuoteSerializer,
    LoanQuoteUpdateSerializer,
)
from loan.permissions import (
    IsSponsor,
    IsLender,
    CanViewQuote,
)


class LoanQuoteListCreateView(APIView):
    """
    GET  /api/v1/loans/requests/<pk>/quotes/ — Sponsor views all quotes for this request
    POST /api/v1/loans/requests/<pk>/quotes/ — Lender submits a quote on an active loan request
    """

    permission_classes = [IsAuthenticated]

    def _get_loan_request(self, pk):
        return get_object_or_404(
            LoanRequest.objects.select_related("property", "sponsor"),
            pk=pk,
        )

    @swagger_auto_schema(
        operation_summary="List quotes on a loan request",
        operation_description="Sponsors retrieve all loan quotes submitted for their specific loan request.",
        tags=["Loan Quotes"],
        responses={
            200: openapi.Response("Quotes retrieved successfully."),
            403: "Permission denied.",
        },
    )
    def get(self, request, pk):
        loan_request = self._get_loan_request(pk)
        if loan_request.sponsor_id != request.user.id:
            return Response(
                {
                    "message": "Only the loan request owner can view all quotes on this request."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        quotes = loan_request.quotes.select_related(
            "lender", "loan_request__property"
        ).order_by("-submitted_at")
        serializer = LoanQuoteSerializer(
            quotes, many=True, context={"request": request}
        )
        return Response(
            {
                "message": "Quotes retrieved successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @swagger_auto_schema(
        operation_summary="Submit a loan quote",
        operation_description="Lenders submit a formal quote for an active loan request. Cannot submit on own property.",
        tags=["Loan Quotes"],
        request_body=LoanQuoteCreateSerializer,
        responses={
            201: openapi.Response("Quote submitted successfully."),
            400: "Validation error or request not active.",
            403: "Only Lender accounts can submit quotes or self-quoting disallowed.",
        },
    )
    def post(self, request, pk):
        is_lender = (
            request.user.roles.filter(name=Role.LENDER).exists()
            or getattr(request.user, "active_role", None) == Role.LENDER
        )
        if not is_lender:
            return Response(
                {"message": "Only Lender accounts can submit quotes."},
                status=status.HTTP_403_FORBIDDEN,
            )

        loan_request = self._get_loan_request(pk)

        # Prohibit self-quoting
        if (
            loan_request.sponsor_id == request.user.id
            or loan_request.property.sponsor_id == request.user.id
        ):
            return Response(
                {
                    "message": "You cannot submit a loan quote on your own property or loan request."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if loan_request.status != LoanRequest.STATUS_ACTIVE:
            return Response(
                {"message": "Quotes can only be submitted on Active loan requests."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = LoanQuoteCreateSerializer(
            data=request.data,
            context={"request": request, "loan_request": loan_request},
        )
        if not serializer.is_valid():
            return Response(
                {"message": "Quote submission failed.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lender_role = RoleModel.objects.filter(name=Role.LENDER).first()

        quote = serializer.save(
            loan_request=loan_request,
            lender=request.user,
            lender_role=lender_role,
            status=LoanQuote.STATUS_SUBMITTED,
        )

        out = LoanQuoteSerializer(quote, context={"request": request})
        return Response(
            {
                "message": "Quote submitted successfully.",
                "data": out.data,
            },
            status=status.HTTP_201_CREATED,
        )


class LenderQuoteListView(APIView):
    """
    GET /api/v1/loans/quotes/ — List all quotes submitted by the authenticated lender
    """

    permission_classes = [IsAuthenticated, IsLender]

    @swagger_auto_schema(
        operation_summary="List lender's submitted quotes",
        operation_description="Returns all loan quotes submitted by the logged-in lender across all loan requests.",
        tags=["Loan Quotes"],
        responses={
            200: openapi.Response("Quotes retrieved successfully."),
            403: "Lender access required.",
        },
    )
    def get(self, request):
        quotes = (
            LoanQuote.objects.filter(lender=request.user)
            .select_related("loan_request__property", "lender")
            .order_by("-submitted_at")
        )
        serializer = LoanQuoteSerializer(
            quotes, many=True, context={"request": request}
        )
        return Response(
            {
                "message": "Your quotes retrieved successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class LoanQuoteDetailView(APIView):
    """
    GET   /api/v1/loans/quotes/<quote_id>/ — View quote details
    PATCH /api/v1/loans/quotes/<quote_id>/ — Update quote (Lender only, if Submitted)
    """

    permission_classes = [IsAuthenticated]

    def _get_quote(self, quote_id):
        return get_object_or_404(
            LoanQuote.objects.select_related(
                "lender", "loan_request__sponsor", "loan_request__property"
            ),
            pk=quote_id,
        )

    @swagger_auto_schema(
        operation_summary="Get quote details",
        operation_description="View details of a quote. Accessible by the owning lender or the loan request sponsor.",
        tags=["Loan Quotes"],
        responses={
            200: openapi.Response("Quote retrieved successfully."),
            403: "Permission denied.",
            404: "Quote not found.",
        },
    )
    def get(self, request, quote_id):
        quote = self._get_quote(quote_id)
        if not CanViewQuote().has_object_permission(request, self, quote):
            return Response(
                {"message": "You do not have permission to view this quote."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = LoanQuoteSerializer(quote, context={"request": request})
        return Response(
            {
                "message": "Quote retrieved successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @swagger_auto_schema(
        operation_summary="Update quote",
        operation_description="Lender updates quote details. Only allowed when status is 'Submitted'.",
        tags=["Loan Quotes"],
        request_body=LoanQuoteUpdateSerializer,
        responses={
            200: openapi.Response("Quote updated successfully."),
            400: "Validation error.",
            403: "Permission denied.",
        },
    )
    def patch(self, request, quote_id):
        quote = self._get_quote(quote_id)
        if quote.lender_id != request.user.id:
            return Response(
                {"message": "You do not have permission to update this quote."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = LoanQuoteUpdateSerializer(quote, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(
                {"message": "Quote update failed.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save()
        out = LoanQuoteSerializer(quote, context={"request": request})
        return Response(
            {
                "message": "Quote updated successfully.",
                "data": out.data,
            },
            status=status.HTTP_200_OK,
        )


class AcceptQuoteView(APIView):
    """
    POST /api/v1/loans/quotes/<quote_id>/accept/ — Sponsor accepts a quote
    """

    permission_classes = [IsAuthenticated, IsSponsor]

    @swagger_auto_schema(
        operation_summary="Accept a loan quote",
        operation_description=(
            "Sponsor accepts a specific loan quote. Automatically marks this quote as 'Accepted', "
            "declines all other quotes on the same request, and closes the loan request."
        ),
        tags=["Loan Quotes"],
        responses={
            200: openapi.Response("Quote accepted and loan request closed."),
            400: "Loan request already closed.",
            403: "Permission denied.",
        },
    )
    def post(self, request, quote_id):
        quote = get_object_or_404(
            LoanQuote.objects.select_related(
                "loan_request__sponsor", "loan_request__property"
            ),
            pk=quote_id,
        )
        loan_request = quote.loan_request

        if loan_request.sponsor_id != request.user.id:
            return Response(
                {"message": "You do not have permission to accept this quote."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if loan_request.status == LoanRequest.STATUS_CLOSED:
            return Response(
                {"message": "This loan request is already closed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            # Mark this quote as accepted
            quote.status = LoanQuote.STATUS_ACCEPTED
            quote.save(update_fields=["status", "updated_at"])

            # Decline all other quotes on the same request and trigger decline notifications
            other_quotes = list(
                LoanQuote.objects.filter(loan_request=loan_request)
                .exclude(pk=quote.pk)
                .select_related("loan_request__property", "lender")
            )
            for other_quote in other_quotes:
                if other_quote.status != LoanQuote.STATUS_DECLINED:
                    other_quote.status = LoanQuote.STATUS_DECLINED
                    other_quote.save(update_fields=["status", "updated_at"])

            # Close loan request
            loan_request.status = LoanRequest.STATUS_CLOSED
            loan_request.save(update_fields=["status", "updated_at"])

        serializer = LoanQuoteSerializer(quote, context={"request": request})
        return Response(
            {
                "message": "Quote accepted. Loan request is now closed.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class DeclineQuoteView(APIView):
    """
    POST /api/v1/loans/quotes/<quote_id>/decline/ — Sponsor declines a quote
    """

    permission_classes = [IsAuthenticated, IsSponsor]

    @swagger_auto_schema(
        operation_summary="Decline a loan quote",
        operation_description="Sponsor declines a specific loan quote. The loan request remains open for other quotes.",
        tags=["Loan Quotes"],
        responses={
            200: openapi.Response("Quote declined successfully."),
            400: "Quote is already accepted or declined.",
            403: "Permission denied.",
        },
    )
    def post(self, request, quote_id):
        quote = get_object_or_404(
            LoanQuote.objects.select_related("loan_request__sponsor"),
            pk=quote_id,
        )

        if quote.loan_request.sponsor_id != request.user.id:
            return Response(
                {"message": "You do not have permission to decline this quote."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if quote.status in (LoanQuote.STATUS_ACCEPTED, LoanQuote.STATUS_DECLINED):
            return Response(
                {"message": f"Quote is already {quote.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        quote.status = LoanQuote.STATUS_DECLINED
        quote.save(update_fields=["status", "updated_at"])

        serializer = LoanQuoteSerializer(quote, context={"request": request})
        return Response(
            {
                "message": "Quote declined successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
