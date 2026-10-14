"""
Training script for the lightweight document image binary classifier.
Class 0: Standard Document (clean, text-based layout)
Class 1: Scanned / Complex Document (scanned receipt, invoices, multi-column complex scans)

Utilizes sample datasets from:
- packages/markitdown/tests/test_files
- packages/markitdown-ocr/tests/ocr_test_data
"""

import argparse
import logging
import os
import random
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

from PIL import Image, ImageEnhance, ImageFilter

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as transforms

# Import model definitions (support direct script execution and package import)
if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from model import build_classifier, save_checkpoint, safe_pil_to_tensor
else:
    from .model import build_classifier, save_checkpoint, safe_pil_to_tensor

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ClassifierTrainer")


# Standard vs Scanned/Complex file categorization rules for MarkItDown test data
CLASS_0_PATTERNS = [
    "test.pdf",
    "movie-theater-booking-2024.pdf",
    "masterformat_partial_numbering.pdf",
    "pdf_image_start.pdf",
    "pdf_image_middle.pdf",
    "pdf_image_end.pdf",
    "pdf_multipage.pdf",
    "equations.docx",
    "test.docx",
    "test.pptx",
    "test.xlsx",
]

CLASS_1_PATTERNS = [
    "medrpt-2024-pat-3847_medical_report_scan",
    "receipt-2024-txn-98765_retail_purchase",
    "repair-2022-inv-001_multipage",
    "sparse-2024-inv-1234_borderless_table",
    "pdf_scanned_invoice",
    "pdf_scanned_meeting_minutes",
    "pdf_scanned_minimal",
    "pdf_scanned_report",
    "pdf_scanned_sales_report",
    "pdf_complex_layout",
    "docx_complex_layout",
    "pptx_complex_layout",
    "xlsx_complex_layout",
    "multiple_images",
    "test.jpg",
    "test_llm.jpg",
]


def render_pdf_to_images(pdf_path: Path, max_pages: int = 3) -> List[Image.Image]:
    """Renders PDF pages to PIL Images using pymupdf or pypdfium2."""
    images = []
    # Try pymupdf (fitz)
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

    # Try pypdfium2
    try:
        import pypdfium2  # type: ignore
        pdf = pypdfium2.PdfDocument(str(pdf_path))
        num_pages = min(len(pdf), max_pages)
        for i in range(num_pages):
            page = pdf[i]
            pil_image = page.render(scale=1.5).to_pil().convert("RGB")
            images.append(pil_image)
        return images
    except Exception:
        pass

    return images


def load_raw_samples(data_dirs: List[Path]) -> List[Tuple[Image.Image, int, str]]:
    """
    Collects and renders document image samples from given directories.
    Returns: List of (PIL Image, label, source_filename)
    """
    samples: List[Tuple[Image.Image, int, str]] = []

    for d in data_dirs:
        if not d.exists():
            continue
        for file_path in d.iterdir():
            if not file_path.is_file():
                continue
            name_lower = file_path.name.lower()
            suffix = file_path.suffix.lower()

            # Determine ground-truth label based on naming and characteristics
            label: Optional[int] = None
            for p in CLASS_1_PATTERNS:
                if p in name_lower:
                    label = 1
                    break
            if label is None:
                for p in CLASS_0_PATTERNS:
                    if p in name_lower:
                        label = 0
                        break

            # If still undetermined, check keywords
            if label is None:
                if any(k in name_lower for k in ["scan", "ocr", "receipt", "invoice", "complex"]):
                    label = 1
                elif suffix in [".pdf", ".docx", ".xlsx", ".pptx", ".html"]:
                    label = 0

            if label is None:
                continue

            # Process file into PIL image(s)
            if suffix in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]:
                try:
                    with Image.open(file_path) as img:
                        samples.append((img.convert("RGB"), label, file_path.name))
                except Exception as e:
                    logger.warning(f"Could not open image {file_path}: {e}")
            elif suffix == ".pdf":
                rendered = render_pdf_to_images(file_path, max_pages=3)
                for page_idx, img in enumerate(rendered):
                    samples.append((img, label, f"{file_path.name}_p{page_idx}"))

    return samples


def augment_sample(img: Image.Image, label: int) -> Image.Image:
    """Applies synthetic augmentations mimicking document variations."""
    img = img.copy()

    # Slight random rotation (-5 to 5 degrees)
    angle = random.uniform(-6.0, 6.0)
    img = img.rotate(angle, resample=Image.Resampling.BILINEAR, fillcolor=(255, 255, 255))

    # Brightness / Contrast jitter
    enh_b = ImageEnhance.Brightness(img)
    img = enh_b.enhance(random.uniform(0.85, 1.15))
    enh_c = ImageEnhance.Contrast(img)
    img = enh_c.enhance(random.uniform(0.85, 1.20))

    # For scanned documents, occasionally simulate blur or noise
    if label == 1 and random.random() < 0.35:
        img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.5, 1.2)))

    return img


class DocumentImageDataset(Dataset):
    """PyTorch Dataset for document image binary classification."""

    def __init__(
        self,
        samples: List[Tuple[Image.Image, int, str]],
        transform: Optional[transforms.Compose] = None,
        target_size: int = 120,
        is_train: bool = True,
    ):
        self.transform = transform
        self.is_train = is_train
        self.data: List[Tuple[Image.Image, int, str]] = []

        # Balance and expand data to reach target_size with augmentations
        class_0 = [s for s in samples if s[1] == 0]
        class_1 = [s for s in samples if s[1] == 1]

        target_per_class = target_size // 2

        for pool, label in [(class_0, 0), (class_1, 1)]:
            if not pool:
                continue
            count = 0
            while count < target_per_class:
                base_img, _, name = random.choice(pool)
                if is_train and count >= len(pool):
                    aug_img = augment_sample(base_img, label)
                else:
                    aug_img = base_img.copy()
                self.data.append((aug_img, label, name))
                count += 1

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        img, label, _ = self.data[idx]
        if self.transform is not None:
            tensor = self.transform(img)
        else:
            tensor = safe_pil_to_tensor(img)
        return tensor, label


def get_default_data_dirs() -> List[Path]:
    """Finds available test data directories in markitdown workspace."""
    base_dir = Path(__file__).resolve().parent.parent.parent  # markitdown-main or workspace
    candidates = [
        base_dir / "packages" / "markitdown" / "tests" / "test_files",
        base_dir / "packages" / "markitdown-ocr" / "tests" / "ocr_test_data",
        base_dir.parent / "markitdown-main" / "packages" / "markitdown" / "tests" / "test_files",
        base_dir.parent / "markitdown-main" / "packages" / "markitdown-ocr" / "tests" / "ocr_test_data",
    ]
    seen = set()
    result = []
    for p in candidates:
        if p.exists():
            resolved = p.resolve()
            if resolved not in seen:
                seen.add(resolved)
                result.append(resolved)
    return result


def train_classifier(
    model_type: str = "cnn",
    epochs: int = 10,
    batch_size: int = 8,
    lr: float = 1e-3,
    output_dir: str = "weights",
    val_split: float = 0.2,
    device: Optional[torch.device] = None,
) -> Path:
    """
    Main training workflow.
    """
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device} | Model architecture: {model_type}")

    # Locate datasets
    data_dirs = get_default_data_dirs()
    if not data_dirs:
        raise FileNotFoundError(
            "Could not locate MarkItDown test data directories. Ensure tests/test_files exists."
        )
    logger.info(f"Loading samples from: {[str(d) for d in data_dirs]}")

    raw_samples = load_raw_samples(data_dirs)
    c0 = sum(1 for s in raw_samples if s[1] == 0)
    c1 = sum(1 for s in raw_samples if s[1] == 1)
    logger.info(f"Loaded {len(raw_samples)} raw pages/images (Class 0: {c0}, Class 1: {c1})")

    if c0 == 0 or c1 == 0:
        raise ValueError(f"Insufficient class balance: Class 0 has {c0}, Class 1 has {c1}")

    # Train / Val Split
    random.seed(42)
    random.shuffle(raw_samples)
    split_idx = int(len(raw_samples) * (1.0 - val_split))
    train_raw = raw_samples[:split_idx]
    val_raw = raw_samples[split_idx:] if split_idx < len(raw_samples) else raw_samples

    # Image Transforms (safe_pil_to_tensor avoids NumPy 2.x C-API incompatibility)
    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(p=0.1),
        safe_pil_to_tensor,
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    val_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        safe_pil_to_tensor,
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    train_dataset = DocumentImageDataset(train_raw, transform=train_transform, target_size=120, is_train=True)
    val_dataset = DocumentImageDataset(val_raw, transform=val_transform, target_size=32, is_train=False)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    # Build model
    model = build_classifier(model_type=model_type, num_classes=2, pretrained=True)
    model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    best_weights_file = out_path / "best_model.pth"
    latest_weights_file = out_path / "latest_model.pth"

    best_val_acc = -1.0
    logger.info(f"Starting training for {epochs} epochs...")

    for epoch in range(1, epochs + 1):
        model.train()
        running_loss = 0.0
        correct_train = 0
        total_train = 0

        for images, labels in train_loader:
            images = images.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * images.size(0)
            _, preds = torch.max(outputs, 1)
            correct_train += (preds == labels).sum().item()
            total_train += labels.size(0)

        scheduler.step()

        train_loss = running_loss / max(total_train, 1)
        train_acc = correct_train / max(total_train, 1)

        # Validation
        model.eval()
        val_loss = 0.0
        correct_val = 0
        total_val = 0
        tp, fp, fn, tn = 0, 0, 0, 0

        with torch.no_grad():
            for images, labels in val_loader:
                images = images.to(device)
                labels = labels.to(device)
                outputs = model(images)
                loss = criterion(outputs, labels)

                val_loss += loss.item() * images.size(0)
                _, preds = torch.max(outputs, 1)
                correct_val += (preds == labels).sum().item()
                total_val += labels.size(0)

                for p_val, t_val in zip(preds.cpu().tolist(), labels.cpu().tolist()):
                    if p_val == 1 and t_val == 1:
                        tp += 1
                    elif p_val == 1 and t_val == 0:
                        fp += 1
                    elif p_val == 0 and t_val == 1:
                        fn += 1
                    else:
                        tn += 1

        val_loss = val_loss / max(total_val, 1)
        val_acc = correct_val / max(total_val, 1)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        logger.info(
            f"Epoch [{epoch:02d}/{epochs:02d}] "
            f"Train Loss: {train_loss:.4f} | Train Acc: {train_acc*100:.1f}% | "
            f"Val Loss: {val_loss:.4f} | Val Acc: {val_acc*100:.1f}% | F1: {f1:.3f}"
        )

        metadata = {
            "epoch": epoch,
            "val_acc": val_acc,
            "train_acc": train_acc,
            "f1": f1,
            "model_type": model_type,
        }

        save_checkpoint(model, str(latest_weights_file), metadata=metadata)
        if val_acc >= best_val_acc:
            best_val_acc = val_acc
            save_checkpoint(model, str(best_weights_file), metadata=metadata)
            logger.info(f" Saved new best model checkpoint (Val Acc: {best_val_acc*100:.1f}%)")

    logger.info(f"Training completed. Best weights saved to: {best_weights_file.resolve()}")
    return best_weights_file


def parse_args():
    parser = argparse.ArgumentParser(description="Train Document Image Binary Classifier")
    parser.add_argument(
        "--model-type",
        type=str,
        default="cnn",
        choices=["cnn", "mobilenet_v3"],
        help="Model architecture: 'cnn' (custom 3-layer CNN) or 'mobilenet_v3'",
    )
    parser.add_argument("--epochs", type=int, default=10, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=8, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(Path(__file__).resolve().parent / "weights"),
        help="Directory to save weights",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    train_classifier(
        model_type=args.model_type,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        output_dir=args.output_dir,
    )
