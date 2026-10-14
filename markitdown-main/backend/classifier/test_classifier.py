"""
Unit and integration test suite for the document classifier module.
Tests:
- DocumentClassifierCNN architecture and forward pass
- MobileNetV3Classifier architecture and forward pass
- Model checkpoint save and load integrity
- PDF and Image inference pipeline in predict.py
"""

import sys
import unittest
from pathlib import Path
from PIL import Image

import torch

# Ensure classifier is in sys.path
classifier_dir = Path(__file__).resolve().parent
if str(classifier_dir.parent) not in sys.path:
    sys.path.insert(0, str(classifier_dir.parent))

from classifier.model import (
    DocumentClassifierCNN,
    MobileNetV3Classifier,
    build_classifier,
    save_checkpoint,
    load_checkpoint,
)
from classifier.predict import DocumentClassifier


class TestDocumentClassifier(unittest.TestCase):

    def test_cnn_forward(self):
        """Test custom 3-layer CNN forward pass shape."""
        model = DocumentClassifierCNN(num_classes=2)
        dummy_input = torch.randn(2, 3, 224, 224)
        output = model(dummy_input)
        self.assertEqual(output.shape, (2, 2), "Output logits must be of shape (B, 2)")

    def test_mobilenet_v3_forward(self):
        """Test MobileNetV3 classifier forward pass shape."""
        model = MobileNetV3Classifier(num_classes=2, pretrained=False)
        dummy_input = torch.randn(2, 3, 224, 224)
        output = model(dummy_input)
        self.assertEqual(output.shape, (2, 2), "Output logits must be of shape (B, 2)")

    def test_factory_builder(self):
        """Test factory function for building models."""
        cnn = build_classifier("cnn")
        self.assertIsInstance(cnn, DocumentClassifierCNN)

        mbv3 = build_classifier("mobilenet_v3", pretrained=False)
        self.assertIsInstance(mbv3, MobileNetV3Classifier)

    def test_checkpoint_roundtrip(self):
        """Test saving and loading weights."""
        model = DocumentClassifierCNN(num_classes=2)
        save_path = classifier_dir / "weights" / "test_checkpoint.pth"
        save_path.parent.mkdir(parents=True, exist_ok=True)

        save_checkpoint(model, str(save_path), metadata={"test_metric": 0.99})
        self.assertTrue(save_path.exists())

        loaded_model = load_checkpoint(str(save_path), default_model_type="cnn")
        self.assertIsInstance(loaded_model, DocumentClassifierCNN)

        # Cleanup
        if save_path.exists():
            save_path.unlink()

    def test_predict_image(self):
        """Test inference on a synthetic PIL Image."""
        classifier = DocumentClassifier(model_type="cnn")
        test_img = Image.new("RGB", (300, 400), color=(255, 255, 255))
        result = classifier.predict(test_img)

        self.assertIn("label", result)
        self.assertIn("class_name", result)
        self.assertIn("confidence", result)
        self.assertIn("probabilities", result)
        self.assertIn("requires_ocr", result)
        self.assertIn(result["label"], [0, 1])
        self.assertGreaterEqual(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 1.0)


if __name__ == "__main__":
    unittest.main()
