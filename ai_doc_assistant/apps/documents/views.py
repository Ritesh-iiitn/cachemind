from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Document
from .serializers import DocumentSerializer
from .services import DocumentService

class DocumentUploadView(generics.CreateAPIView):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    
    def perform_create(self, serializer):
        document = serializer.save()
        DocumentService.process_document(document.id)

class DocumentListView(generics.ListAPIView):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer

class DocumentSummaryView(APIView):
    def get(self, request, document_id):
        try:
            summary = DocumentService.generate_summary(document_id)
            return Response({"document_id": document_id, "summary": summary}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
