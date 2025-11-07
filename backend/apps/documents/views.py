from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.candidates.models import Candidate
from .models import DocumentRequest
from .serializers import (
    SubmitDocumentsSerializer,
    SubmitDocumentsResponseSerializer,
    RequestDocumentsSerializer,
    RequestDocumentsResponseSerializer,
)


class SubmitDocumentsView(APIView):
    """
    POST /candidates/<id>/submit-documents
    Accepts uploads for PAN/Aadhaar (one or both).
    Optional fields: pan_number, aadhaar_number.
    """

    def post(self, request, candidate_id: int, *args, **kwargs):
        candidate = get_object_or_404(Candidate, pk=candidate_id)
        # if a request_id is passed, link submission back to it
        request_id = request.query_params.get("request_id")
        doc_req = None
        if request_id:
            doc_req = DocumentRequest.objects.filter(pk=request_id, candidate=candidate).first()

        serializer = SubmitDocumentsSerializer(
            data=request.data, context={"candidate": candidate, "document_request": doc_req}
        )
        serializer.is_valid(raise_exception=True)
        payload = serializer.save()
        return Response(SubmitDocumentsResponseSerializer(payload).data, status=status.HTTP_201_CREATED)


class RequestDocumentsView(APIView):
    """
    POST /candidates/<id>/request-documents
    Body: { "channel": "EMAIL" | "SMS" }
    Generates + logs a personalized request and sends via console email/SMS stub.
    """

    def post(self, request, candidate_id: int, *args, **kwargs):
        candidate = get_object_or_404(Candidate, pk=candidate_id)
        serializer = RequestDocumentsSerializer(data=request.data or {}, context={"candidate": candidate})
        serializer.is_valid(raise_exception=True)
        payload = serializer.save()
        return Response(RequestDocumentsResponseSerializer(payload).data, status=status.HTTP_201_CREATED)
