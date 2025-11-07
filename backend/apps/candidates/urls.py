from django.urls import path

from .views import CandidateListView, CandidateDetailView, UploadResumeView

urlpatterns = [
    path("candidates/upload", UploadResumeView.as_view(), name="upload-resume"),
    path("candidates", CandidateListView.as_view(), name="candidates-list"),
    path("candidates/<int:pk>", CandidateDetailView.as_view(), name="candidates-detail"),
]
