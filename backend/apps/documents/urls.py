from django.urls import path

from .views import SubmitDocumentsView, RequestDocumentsView

urlpatterns = [
    path("candidates/<int:candidate_id>/submit-documents", SubmitDocumentsView.as_view(), name="submit-documents"),
    path("candidates/<int:candidate_id>/request-documents", RequestDocumentsView.as_view(), name="request-documents"),
]
