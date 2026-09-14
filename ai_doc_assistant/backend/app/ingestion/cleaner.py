import re
import unicodedata
import logging
from typing import List
from backend.app.ingestion.parser import ParsedPage

logger = logging.getLogger("cachemind.ingestion.cleaner")


class TextCleaner:
    """
    Robust text cleaner and normalizer for extracted document text.
    Handles Unicode normalization, control character stripping, whitespace collapse,
    and boilerplate artifact removal while preserving structural markup and headings.
    """

    @staticmethod
    def clean_text(text: str) -> str:
        if not text:
            return ""

        # 1. Unicode NFKC normalization
        normalized = unicodedata.normalize("NFKC", text)

        # 2. Strip non-printable/control characters (preserve newlines and tabs)
        cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", normalized)

        # 3. Normalize bullet points and dashes
        cleaned = re.sub(r"[•●▪◆]", "- ", cleaned)
        cleaned = re.sub(r"[–—]", "-", cleaned)

        # 4. Collapse runs of spaces/tabs (preserving newlines)
        cleaned = re.sub(r"[ \t]+", " ", cleaned)

        # 5. Collapse excessive line breaks (more than 2 consecutive newlines)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

        # 6. Trim leading/trailing whitespace
        return cleaned.strip()

    @classmethod
    def clean_pages(cls, pages: List[ParsedPage]) -> List[ParsedPage]:
        """
        Cleans text across all parsed pages. Filters out blank or degenerate pages.
        """
        cleaned_pages: List[ParsedPage] = []
        for p in pages:
            cleaned_text = cls.clean_text(p.text)
            if cleaned_text:
                clean_section = cls.clean_text(p.section) if p.section else None
                cleaned_pages.append(
                    ParsedPage(
                        page_number=p.page_number,
                        text=cleaned_text,
                        section=clean_section
                    )
                )
        return cleaned_pages


text_cleaner = TextCleaner()
