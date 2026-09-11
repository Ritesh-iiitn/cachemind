import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import fitz  # PyMuPDF

class ParsedPage:
    def __init__(self, page_number: int, text: str, section: Optional[str] = None):
        self.page_number = page_number
        self.text = text
        self.section = section

class DocumentParser:
    """
    Robust multi-format document parser extracting structural text,
    page boundaries, and header sections from PDF, TXT, MD, DOCX.
    """
    
    @staticmethod
    def parse_pdf(file_path: Path) -> List[ParsedPage]:
        pages = []
        doc = fitz.open(file_path)
        current_section = "Introduction"
        
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            text = page.get_text("text")
            
            # Simple section heuristic: lines that look like headings
            lines = text.split("\n")
            for line in lines[:5]:
                clean_line = line.strip()
                if clean_line and (clean_line.isupper() or re.match(r"^(\d+\.|\#+)\s+", clean_line)):
                    current_section = clean_line[:80]
                    break
                    
            if text.strip():
                pages.append(ParsedPage(page_number=page_idx + 1, text=text, section=current_section))
        doc.close()
        return pages

    @staticmethod
    def parse_text(file_path: Path) -> List[ParsedPage]:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        
        # Split into logical sections or pages if large
        paragraphs = content.split("\n\n")
        pages = []
        current_page_text = []
        page_num = 1
        current_section = "General"
        
        for p in paragraphs:
            if p.startswith("# ") or p.startswith("## "):
                current_section = p.split("\n")[0].strip("# ").strip()
            current_page_text.append(p)
            if len("\n\n".join(current_page_text)) > 2000:
                pages.append(ParsedPage(page_number=page_num, text="\n\n".join(current_page_text), section=current_section))
                current_page_text = []
                page_num += 1
                
        if current_page_text:
            pages.append(ParsedPage(page_number=page_num, text="\n\n".join(current_page_text), section=current_section))
            
        return pages

    @classmethod
    def parse(cls, file_path: Path) -> List[ParsedPage]:
        ext = file_path.suffix.lower()
        if ext == ".pdf":
            return cls.parse_pdf(file_path)
        elif ext in [".txt", ".md", ".markdown", ".csv", ".json", ".docx"]:
            return cls.parse_text(file_path)
        else:
            return cls.parse_text(file_path)
