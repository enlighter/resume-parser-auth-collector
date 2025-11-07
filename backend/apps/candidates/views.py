from __future__ import annotations

import mimetypes

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Candidate, Resume, Extraction
from .serializers import (
    CandidateListSerializer,
    CandidateDetailSerializer,
    ResumeUploadSerializer,
    ResumeUploadResponseSerializer,
)
from .parsing import queue_parse_resume


class CandidateListView(generics.ListAPIView):
    queryset = Candidate.objects.order_by("-created_at")
    serializer_class = CandidateListSerializer


class CandidateDetailView(generics.RetrieveAPIView):
    queryset = Candidate.objects.all()
    serializer_class = CandidateDetailSerializer


class UploadResumeView(APIView):
    """
    POST /candidates/upload
    Accepts a PDF/DOCX, creates a Candidate+Resume, and kicks off parsing in a background thread.
    """
    def post(self, request, *args, **kwargs):
        serializer = ResumeUploadSerializer(
            data=request.data, context={"MAX_UPLOAD_MB": getattr(settings, "MAX_UPLOAD_MB", 10)}
        )
        serializer.is_valid(raise_exception=True)
        f = serializer.validated_data["file"]

        # Create a blank candidate; parsing will fill it.
        candidate = Candidate.objects.create(extraction_status=Candidate.ExtractionStatus.PARSING)

        # Store resume locally
        resume = Resume(
            candidate=candidate,
            original_name=getattr(f, "name", "") or "",
            mime_type=getattr(f, "content_type", "") or (mimetypes.guess_type(getattr(f, "name", ""))[0] or ""),
            size_bytes=getattr(f, "size", 0) or 0,
            status=Resume.Status.PARSING,
        )
        resume.file.save(getattr(f, "name", "resume"), f, save=True)

        # After transaction commits, kick off parse (threaded)
        transaction.on_commit(lambda: queue_parse_resume(resume.id))

        payload = {
            "candidate_id": candidate.id,
            "resume_id": resume.id,
            "status": "PARSING",
            "message": "Resume uploaded; parsing started.",
        }
        return Response(ResumeUploadResponseSerializer(payload).data, status=status.HTTP_201_CREATED)
