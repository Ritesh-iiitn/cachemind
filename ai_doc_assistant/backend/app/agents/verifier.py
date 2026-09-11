import logging
from typing import List, Dict, Any, Tuple
from backend.app.models.schemas import DocumentChunk, Citation

logger = logging.getLogger("cachemind.verifier")

class AnswerVerifier:
    """
    Evaluates generated responses against retrieved context chunks to verify
    factual grounding, citation validity, and hallucination absence.
    """
    def verify(
        self,
        query: str,
        answer: str,
        chunks: List[DocumentChunk]
    ) -> Tuple[bool, str, List[Citation]]:
        if not chunks:
            # If no chunks were retrieved, answer cannot be grounded
            return False, "no_retrieved_evidence", []

        if not answer.strip():
            return False, "empty_answer", []

        # Extract keywords from answer
        ans_terms = set(answer.lower().split())
        citations: List[Citation] = []
        supported_chunks_count = 0

        for chunk in chunks:
            chunk_terms = set(chunk.text.lower().split())
            overlap = len(ans_terms.intersection(chunk_terms))
            
            # If significant term overlap exists, generate citation
            if overlap >= 3:
                supported_chunks_count += 1
                snippet = chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text
                citations.append(
                    Citation(
                        document_id=chunk.document_id,
                        filename=chunk.section or f"Doc-{chunk.document_id[:6]}",
                        chunk_id=chunk.id,
                        page_number=chunk.page_number,
                        section=chunk.section,
                        snippet=snippet
                    )
                )

        if supported_chunks_count > 0:
            logger.info(f"[Verifier PASSED] Verified answer with {len(citations)} citations.")
            return True, "verified_grounded", citations
        else:
            logger.warning("[Verifier FAILED] Answer lacked direct overlap with retrieved context.")
            return False, "insufficient_evidence_overlap", citations

verifier = AnswerVerifier()
