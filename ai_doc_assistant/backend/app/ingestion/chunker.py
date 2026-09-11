import uuid
import re
from typing import List, Optional
from backend.app.models.schemas import DocumentChunk
from backend.app.ingestion.parser import ParsedPage

class TextChunker:
    """
    Token-aware text chunker with sliding window overlap and structural metadata attachment.
    """
    def __init__(self, target_chunk_size: int = 500, chunk_overlap: int = 100):
        self.target_chunk_size = target_chunk_size
        self.chunk_overlap = chunk_overlap

    def _approx_token_count(self, text: str) -> int:
        # 1 token ≈ 4 characters or word count * 1.3
        words = text.split()
        return max(1, int(len(words) * 1.3))

    def chunk_document(
        self,
        pages: List[ParsedPage],
        document_id: str,
        kb_id: str,
        document_version: int = 1
    ) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        chunk_idx = 0
        
        for page in pages:
            text = page.text.strip()
            if not text:
                continue
                
            paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
            current_chunk_words: List[str] = []
            
            for para in paragraphs:
                para_words = para.split()
                if not para_words:
                    continue
                    
                if len(current_chunk_words) + len(para_words) > self.target_chunk_size and current_chunk_words:
                    chunk_text = " ".join(current_chunk_words)
                    chunk_id = f"chk_{uuid.uuid4().hex[:12]}"
                    chunks.append(
                        DocumentChunk(
                            id=chunk_id,
                            document_id=document_id,
                            kb_id=kb_id,
                            document_version=document_version,
                            chunk_index=chunk_idx,
                            page_number=page.page_number,
                            section=page.section,
                            text=chunk_text,
                            token_count=self._approx_token_count(chunk_text)
                        )
                    )
                    chunk_idx += 1
                    # Keep overlap words
                    overlap_count = min(self.chunk_overlap, len(current_chunk_words))
                    current_chunk_words = current_chunk_words[-overlap_count:] + para_words
                else:
                    current_chunk_words.extend(para_words)
                    
            if current_chunk_words:
                chunk_text = " ".join(current_chunk_words)
                chunk_id = f"chk_{uuid.uuid4().hex[:12]}"
                chunks.append(
                    DocumentChunk(
                        id=chunk_id,
                        document_id=document_id,
                        kb_id=kb_id,
                        document_version=document_version,
                        chunk_index=chunk_idx,
                        page_number=page.page_number,
                        section=page.section,
                        text=chunk_text,
                        token_count=self._approx_token_count(chunk_text)
                    )
                )
                chunk_idx += 1
                
        return chunks
