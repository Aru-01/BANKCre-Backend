import logging
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema

from properties.models import Property
from properties.serializers import PropertyMapSerializer, PlaceSerializer
from properties.permissions import IsLender
from properties.services.ai_services import extract_property_details
from properties.views.schemas import success_schema, error_schema

logger = logging.getLogger(__name__)


class PropertyMapView(APIView):
    """Lightweight map-marker data for the Lender's map view."""

    permission_classes = [IsAuthenticated, IsLender]

    @swagger_auto_schema(
        operation_summary="Get all properties for map",
        tags=["Properties"],
        responses={
            200: success_schema("Properties retrieved successfully."),
            403: error_schema("Lender access required."),
        },
    )
    def get(self, request):
        props = Property.objects.only(
            "id",
            "property_name",
            "property_address",
            "property_type",
            "latitude",
            "longitude",
        ).prefetch_related("files")
        serializer = PropertyMapSerializer(
            props, many=True, context={"request": request}
        )
        return Response(
            {"message": "Properties retrieved successfully.", "data": serializer.data}
        )


class PlaceView(APIView):
    """
    Validates Google Maps place data from the frontend.
    Frontend uses the response to pre-fill the property form,
    then POSTs to /properties/ separately.
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Validate & return map place data",
        tags=["Properties"],
        request_body=PlaceSerializer,
        responses={
            200: success_schema("Place data received successfully."),
            400: error_schema("Invalid place data."),
        },
    )
    def post(self, request):
        serializer = PlaceSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"message": "Invalid place data.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        extracted = extract_property_details(
            data.get("name", ""), data.get("address", "")
        )

        # Merge extracted details
        for key in [
            "property_type",
            "number_of_units",
            "rentable_area",
            "year_built",
            "occupancy_rate",
            "year_renovated",
            "parking_spaces",
        ]:
            data[key] = extracted.get(key, None)

        return Response({"message": "Place data received successfully.", "data": data})
