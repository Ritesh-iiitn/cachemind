from django.shortcuts import get_object_or_404
from apps.documents.models import Document
from ai_engine.rag.pipeline import RAGPipeline

class QuizService:
    @staticmethod
    def generate_quiz(document_id):
        document = get_object_or_404(Document, id=document_id)
        if not document.is_processed:
            raise ValueError("Document not yet processed.")
            
        pipeline = RAGPipeline()
        quiz = pipeline.generate_quiz(document.parsed_text)
        return quiz
