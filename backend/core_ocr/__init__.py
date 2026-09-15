import os
import sys

CORE_OCR_DIR = os.path.dirname(os.path.abspath(__file__))
subdirs = [
    CORE_OCR_DIR,
    os.path.join(CORE_OCR_DIR, "schemas"),
    os.path.join(CORE_OCR_DIR, "extractors"),
    os.path.join(CORE_OCR_DIR, "summary"),
    os.path.join(CORE_OCR_DIR, "renderer"),
]
for d in subdirs:
    if d not in sys.path:
        sys.path.insert(0, d)
