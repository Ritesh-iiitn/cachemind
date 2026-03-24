from django.shortcuts import get_object_or_404
from .models import Document
from ai_engine.parsers.pdf_parser import PDFParser
from ai_engine.embeddings.chunking import text_chunker
from vector_store.vector_manager import VectorManager
from ai_engine.rag.pipeline import RAGPipeline

class DocumentService:
    @staticmethod
    def process_document(document_id):
        """Processes the uploaded document: parses, chunks, embeds, and stores."""
        document = get_object_or_404(Document, id=document_id)
        
        # 1. Parse PDF
        parsed_text = PDFParser.extract_text(document.file.path)
        document.parsed_text = parsed_text
        document.save(update_fields=['parsed_text'])
        
        # 2. Chunk Text
        chunks = text_chunker(parsed_text, chunk_size=800, chunk_overlap=100)
        
        # 3. Embed & Store
        vector_manager = VectorManager()
        vector_manager.add_texts(
            texts=chunks,
            metadatas=[{"document_id": str(document.id)} for _ in chunks]
        )
        
        # Mark as processed
        document.is_processed = True
        document.save(update_fields=['is_processed'])
        
        return document
        
    @staticmethod
    def generate_summary(document_id):
        """Generates summary for a specific document."""
        document = get_object_or_404(Document, id=document_id)
        if not document.is_processed:
            raise ValueError("Document not yet processed.")
            
        pipeline = RAGPipeline()
        summary = pipeline.summarize_document(document.parsed_text)
        return summary
