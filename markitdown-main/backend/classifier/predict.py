"""
Inference API for Document Image Binary Classifier.
Performs binary classification on images and documents:
- Class 0 (Standard Document): Fast local text/structure extraction via MarkItDown.
- Class 1 (Scanned / Complex Layout Document): Requires OCR / Vision LLM pipeline.
"""

import argparse
import io
import json
import logging
from pathlib import Path
from typing import Dict, Any, Union, Optional, List

from PIL import Image
import torch
import torch.nn.functional as F
import torchvision.transforms as transforms

# Import model definitions (support direct script execution and package import)
if __package__ is None or __package__ == "":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from model import build_classifier, load_checkpoint, safe_pil_to_tensor
else:
    from .model import build_classifier, load_checkpoint, safe_pil_to_tensor

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("DocumentPredictor")

CLASS_NAMES = {
    0: "standard",
    1: "scanned_or_complex",
}


class DocumentClassifier:
    """
    Lightweight document binary classifier inference wrapper.
    """

    def __init__(
        self,
        weights_path: Optional[Union[str, Path]] = None,
        model_type: str = "cnn",
        device: Optional[torch.device] = None,
    ):
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = device

        self.model_type = model_type
        self.weights_path = self._resolve_weights_path(weights_path)

        # Standard document transform matching training
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            safe_pil_to_tensor,
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        self.model = self._load_model()

    def _resolve_weights_path(self, path: Optional[Union[str, Path]]) -> Optional[Path]:
        if path is not None:
            p = Path(path)
            if p.exists():
                return p
            logger.warning(f"Specified weights path not found: {path}")

        # Check default paths
        current_dir = Path(__file__).resolve().parent
        candidates = [
            current_dir / "weights" / "best_model.pth",
            current_dir / "weights" / "latest_model.pth",
        ]
        for c in candidates:
            if c.exists():
                return c

        return None

    def _load_model(self) -> torch.nn.Module:
        if self.weights_path and self.weights_path.exists():
            logger.info(f"Loading weights from: {self.weights_path}")
            model = load_checkpoint(str(self.weights_path), device=self.device, default_model_type=self.model_type)
        else:
            logger.warning(
                "No trained weights file found in 'weights/best_model.pth'. "
                f"Initializing untrained '{self.model_type}' model for inference testing. "
                "Run train.py to train and save model weights."
            )
            model = build_classifier(model_type=self.model_type, num_classes=2, pretrained=False)
            model.to(self.device)
            model.eval()

        return model

    def _render_pdf(self, pdf_path: Union[str, Path], max_pages: int = 3) -> List[Image.Image]:
        images = []
        try:
            import pymupdf  # type: ignore
            doc = pymupdf.open(str(pdf_path))
            num_pages = min(len(doc), max_pages)
            for i in range(num_pages):
                page = doc[i]
                pix = page.get_pixmap(dpi=150)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                images.append(img)
            doc.close()
            return images
        except Exception:
            pass

        try:
            import pypdfium2  # type: ignore
            pdf = pypdfium2.PdfDocument(str(pdf_path))
            num_pages = min(len(pdf), max_pages)
            for i in range(num_pages):
                img = pdf[i].render(scale=1.5).to_pil().convert("RGB")
                images.append(img)
            return images
        except Exception as e:
            logger.error(f"Failed to render PDF: {e}")

        return images

    def predict_image(self, image: Image.Image) -> Dict[str, Any]:
        """
        Runs binary classification on a single PIL Image.
        """
        img_rgb = image.convert("RGB")
        tensor = self.transform(img_rgb).unsqueeze(0).to(self.device)

        with torch.no_grad():
            logits = self.model(tensor)
            probs = F.softmax(logits, dim=1).squeeze(0)
            pred_idx = torch.argmax(probs).item()

        conf = probs[pred_idx].item()
        p0 = probs[0].item()
        p1 = probs[1].item()

        return {
            "label": pred_idx,
            "class_name": CLASS_NAMES[pred_idx],
            "confidence": round(conf, 4),
            "probabilities": {
                CLASS_NAMES[0]: round(p0, 4),
                CLASS_NAMES[1]: round(p1, 4),
            },
            "requires_ocr": bool(pred_idx == 1),
            "model_type": getattr(self.model, "model_type", self.model_type),
        }

    def predict(self, file_input: Union[str, Path, bytes, io.BytesIO, Image.Image]) -> Dict[str, Any]:
        """
        Predicts document category for a file path, byte stream, or PIL Image.
        """
        if isinstance(file_input, Image.Image):
            return self.predict_image(file_input)

        if isinstance(file_input, (bytes, io.BytesIO)):
            stream = io.BytesIO(file_input) if isinstance(file_input, bytes) else file_input
            try:
                img = Image.open(stream)
                return self.predict_image(img)
            except Exception as e:
                raise ValueError(f"Could not parse image stream: {e}")

        path = Path(file_input)
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {path}")

        suffix = path.suffix.lower()

        # Image files
        if suffix in [".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"]:
            with Image.open(path) as img:
                res = self.predict_image(img)
                res["file_path"] = str(path)
                return res

        # PDF files
        if suffix == ".pdf":
            rendered_pages = self._render_pdf(path, max_pages=3)
            if not rendered_pages:
                # Fallback if rendering fails: default to standard text
                return {
                    "file_path": str(path),
                    "label": 0,
                    "class_name": CLASS_NAMES[0],
                    "confidence": 0.5,
                    "probabilities": {CLASS_NAMES[0]: 0.5, CLASS_NAMES[1]: 0.5},
                    "requires_ocr": False,
                    "model_type": getattr(self.model, "model_type", self.model_type),
                    "note": "PDF could not be rendered to images; default fallback applied",
                }

            page_results = [self.predict_image(page_img) for page_img in rendered_pages]

            # Overall decision: If any scanned page detected with high confidence or majority
            is_scanned = any(r["label"] == 1 and r["confidence"] > 0.55 for r in page_results)
            overall_label = 1 if is_scanned else 0
            overall_conf = max(r["confidence"] for r in page_results if r["label"] == overall_label)

            return {
                "file_path": str(path),
                "label": overall_label,
                "class_name": CLASS_NAMES[overall_label],
                "confidence": overall_conf,
                "probabilities": {
                    CLASS_NAMES[0]: round(1.0 - overall_conf if overall_label == 1 else overall_conf, 4),
                    CLASS_NAMES[1]: round(overall_conf if overall_label == 1 else 1.0 - overall_conf, 4),
                },
                "requires_ocr": bool(overall_label == 1),
                "pages_analyzed": len(rendered_pages),
                "page_details": page_results,
                "model_type": getattr(self.model, "model_type", self.model_type),
            }

        # Other office formats (docx, pptx, xlsx, etc.):
        # In MarkItDown architecture, these are natively structured text unless flagged.
        return {
            "file_path": str(path),
            "label": 0,
            "class_name": CLASS_NAMES[0],
            "confidence": 0.95,
            "probabilities": {CLASS_NAMES[0]: 0.95, CLASS_NAMES[1]: 0.05},
            "requires_ocr": False,
            "model_type": getattr(self.model, "model_type", self.model_type),
            "note": "Structured document format handled via native converter",
        }


def predict_document(
    file_path: Union[str, Path],
    weights_path: Optional[str] = None,
    model_type: str = "cnn",
) -> Dict[str, Any]:
    """Convenience function for document classification."""
    classifier = DocumentClassifier(weights_path=weights_path, model_type=model_type)
    return classifier.predict(file_path)


def main():
    parser = argparse.ArgumentParser(description="Predict Document Classification (Standard vs Scanned)")
    parser.add_argument("--input", "-i", type=str, required=True, help="Path to document or image file")
    parser.add_argument("--weights", "-w", type=str, default=None, help="Path to model weights (.pth)")
    parser.add_argument(
        "--model-type",
        "-m",
        type=str,
        default="cnn",
        choices=["cnn", "mobilenet_v3"],
        help="Model architecture: 'cnn' or 'mobilenet_v3'",
    )
    parser.add_argument("--json", action="store_true", help="Output pure JSON format")

    args = parser.parse_args()

    classifier = DocumentClassifier(weights_path=args.weights, model_type=args.model_type)
    result = classifier.predict(args.input)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("\n=== Document Classification Result ===")
        print(f"File:        {result.get('file_path', args.input)}")
        print(f"Prediction:  Class {result['label']} ({result['class_name']})")
        print(f"Confidence:  {result['confidence'] * 100:.2f}%")
        print(f"Requires OCR: {result['requires_ocr']}")
        print(f"Probabilities: {result['probabilities']}")
        if "pages_analyzed" in result:
            print(f"Pages Analyzed: {result['pages_analyzed']}")
        print("======================================\n")


if __name__ == "__main__":
    main()
