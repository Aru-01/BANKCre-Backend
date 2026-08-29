from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from accounts.models import Role, RoleModel
from loan.models import LoanRequest
from loan.serializers import (
    LoanRequestCreateSerializer,
    LoanRequestListSerializer,
    LoanRequestDetailSerializer,
    LoanRequestUpdateSerializer,
)
from loan.permissions import IsSponsorOrLender


class LoanRequestListCreateView(APIView):
    """
    GET  /api/v1/loans/requests/  — List loan requests
    POST /api/v1/loans/requests/  — Create a new loan request (Sponsor only)
    """

    permission_classes = [IsAuthenticated, IsSponsorOrLender]

    @swagger_auto_schema(
        operation_summary="List loan requests",
        operation_description=(
            "Sponsors see their own loan requests. "
            "Lenders see all active loan requests available for quoting (excluding their own properties)."
        ),
        tags=["Loans"],
        manual_parameters=[
            openapi.Parameter(
                "view_as",
                openapi.IN_QUERY,
                description="Force view context: 'sponsor' or 'lender' (useful for users with dual roles)",
                type=openapi.TYPE_STRING,
                required=False,
            ),
        ],
        responses={
            200: openapi.Response("Loan requests retrieved successfully."),
            403: "Permission denied.",
        },
    )
    def get(self, request):
        user = request.user
        # Automatically switch behavior based on active_role
        if getattr(user, "active_role", None) == Role.LENDER:
            # Lender mode: see all active loan requests, excluding own properties
            queryset = (
                LoanRequest.objects.filter(status=LoanRequest.STATUS_ACTIVE)
                .exclude(sponsor=user)
                .exclude(property__sponsor=user)
                .select_related("property")
                .prefetch_related("property__files")
                .annotate(quotes_count_annotated=Count("quotes"))
            )
        else:
            # Sponsor mode: see own loan requests
            queryset = (
                LoanRequest.objects.filter(sponsor=user)
                .select_related("property")
                .prefetch_related("property__files")
                .annotate(quotes_count_annotated=Count("quotes"))
            )

        serializer = LoanRequestListSerializer(
            queryset, many=True, context={"request": request}
        )
        return Response(
            {
                "message": "Loan requests retrieved successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @swagger_auto_schema(
        operation_summary="Create a new loan request",
        operation_description="Sponsors create a loan financing request for one of their properties.",
        tags=["Loans"],
        request_body=LoanRequestCreateSerializer,
        responses={
            201: openapi.Response("Loan request created successfully."),
            400: "Validation error.",
            403: "Only Sponsor accounts can create loan requests.",
        },
    )
    def post(self, request):
        if not request.user.has_role(Role.SPONSOR):
            return Response(
                {"message": "Only Sponsor accounts can create loan requests."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = LoanRequestCreateSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(
                {
                    "message": "Loan request creation failed.",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        sponsor_role = RoleModel.objects.filter(name=Role.SPONSOR).first()

        loan_request = serializer.save(
            sponsor=request.user,
            sponsor_role=sponsor_role,
            status=LoanRequest.STATUS_ACTIVE,
        )

        out = LoanRequestDetailSerializer(loan_request, context={"request": request})
        return Response(
            {
                "message": "Loan request created successfully.",
                "data": out.data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoanRequestDetailView(APIView):
    """
    GET    /api/v1/loans/requests/<pk>/ — Retrieve loan request details
    PATCH  /api/v1/loans/requests/<pk>/ — Update loan request (Sponsor owner only)
    DELETE /api/v1/loans/requests/<pk>/ — Delete loan request (Sponsor owner only)
    """

    permission_classes = [IsAuthenticated, IsSponsorOrLender]

    def _get_request(self, pk):
        return get_object_or_404(
            LoanRequest.objects.select_related(
                "property", "sponsor", "sponsor_role"
            ).prefetch_related("property__files", "property__memorandums"),
            pk=pk,
        )

    @swagger_auto_schema(
        operation_summary="Get loan request details",
        operation_description="Retrieve full details of a loan request including property info, documents, and memorandums.",
        tags=["Loans"],
        responses={
            200: openapi.Response("Loan request retrieved successfully."),
            403: "Permission denied.",
            404: "Loan request not found.",
        },
    )
    def get(self, request, pk):
        loan_request = self._get_request(pk)

        is_owner = loan_request.sponsor_id == request.user.id
        is_lender = request.user.has_role(Role.LENDER)

        if not is_owner:
            if (
                not is_lender
                or loan_request.status != LoanRequest.STATUS_ACTIVE
                or loan_request.property.sponsor_id == request.user.id
            ):
                return Response(
                    {"message": "Loan request not found or not accessible."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        serializer = LoanRequestDetailSerializer(
            loan_request, context={"request": request}
        )
        return Response(
            {
                "message": "Loan request retrieved successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @swagger_auto_schema(
        operation_summary="Update loan request",
        operation_description="Sponsors update amount, term, LTV or status. Closed requests cannot be updated.",
        tags=["Loans"],
        request_body=LoanRequestUpdateSerializer,
        responses={
            200: openapi.Response("Loan request updated successfully."),
            400: "Validation error.",
            403: "Permission denied.",
        },
    )
    def patch(self, request, pk):
        loan_request = self._get_request(pk)
        if loan_request.sponsor_id != request.user.id:
            return Response(
                {"message": "You do not have permission to update this loan request."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = LoanRequestUpdateSerializer(
            loan_request, data=request.data, partial=True
        )
        if not serializer.is_valid():
            return Response(
                {"message": "Update failed.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save()
        out = LoanRequestDetailSerializer(loan_request, context={"request": request})
        return Response(
            {
                "message": "Loan request updated successfully.",
                "data": out.data,
            },
            status=status.HTTP_200_OK,
        )

    @swagger_auto_schema(
        operation_summary="Delete loan request",
        operation_description="Sponsor deletes their loan request.",
        tags=["Loans"],
        responses={
            200: openapi.Response("Loan request deleted successfully."),
            403: "Permission denied.",
        },
    )
    def delete(self, request, pk):
        loan_request = self._get_request(pk)
        if loan_request.sponsor_id != request.user.id:
            return Response(
                {"message": "You do not have permission to delete this loan request."},
                status=status.HTTP_403_FORBIDDEN,
            )
        loan_request.delete()
        return Response(
            {"message": "Loan request deleted successfully."},
            status=status.HTTP_200_OK,
        )
