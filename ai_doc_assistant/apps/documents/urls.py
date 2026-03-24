from django.urls import path
from .views import DocumentUploadView, DocumentListView, DocumentSummaryView

urlpatterns = [
    path('upload/', DocumentUploadView.as_view(), name='document-upload'),
    path('list/', DocumentListView.as_view(), name='document-list'),
    path('<uuid:document_id>/summary/', DocumentSummaryView.as_view(), name='document-summary'),
]
