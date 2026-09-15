"""
document_reader.py - Facade / Re-export Module

Module này re-export các hàm từ input_handler.py để đảm bảo tương thích ngược 
(backward compatibility) với các script và bộ test hiện có.
"""

from input_handler import (
    get_ocr_reader,
    classify_text_element,
    read_pdf,
    read_docx,
    read_xlsx,
    read_image,
    read_document,
)

__all__ = [
    "get_ocr_reader",
    "classify_text_element",
    "read_pdf",
    "read_docx",
    "read_xlsx",
    "read_image",
    "read_document",
]
