"""
Document Classifier Package for MarkItDown.
Provides lightweight deep learning binary classification for document routing:
- Class 0: Standard Document (Clean text / structured docs for fast local extraction)
- Class 1: Scanned / Complex Document (Requires OCR / Vision LLM pipeline)
"""

from .model import DocumentClassifierCNN, MobileNetV3Classifier, build_classifier
from .predict import DocumentClassifier, predict_document

__all__ = [
    "DocumentClassifierCNN",
    "MobileNetV3Classifier",
    "build_classifier",
    "DocumentClassifier",
    "predict_document",
]
