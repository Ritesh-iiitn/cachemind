import hashlib
import re
from typing import List, Optional
from backend.app.models.schemas import DocumentChunk
from backend.app.ingestion.parser import ParsedPage

class TextChunker:
    """
    Token-aware text chunker with sliding window overlap, structural metadata attachment,
    and deterministic chunk identifiers for idempotent indexing.
    """
    def __init__(self, target_chunk_size: int = 500, chunk_overlap: int = 100):
        self.target_chunk_size = target_chunk_size
        self.chunk_overlap = chunk_overlap

    @staticmethod
    def generate_chunk_id(document_id: str, document_version: int, chunk_index: int) -> str:
        """
        Generate deterministic chunk ID: hash(document_id + document_version + chunk_index).
        Guarantees that re-chunking an identical document yields identical IDs.
        """
        digest = hashlib.sha256(f"{document_id}:{document_version}:{chunk_index}".encode("utf-8")).hexdigest()
        return f"chk_{digest[:16]}"

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
                    chunk_id = self.generate_chunk_id(document_id, document_version, chunk_idx)
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
                chunk_id = self.generate_chunk_id(document_id, document_version, chunk_idx)
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

