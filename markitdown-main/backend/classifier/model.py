"""
PyTorch Deep Learning Binary Classifier for Document Routing.
Distinguishes between:
- Class 0: Standard Document (Clean text / structured docs for fast local extraction)
- Class 1: Scanned / Complex Document (Requires OCR / Vision LLM pipeline)

Supports both a custom 3-layer CNN (ultra-lightweight, zero external dependencies)
and MobileNetV3-Small (lightweight mobile architecture).
"""

from typing import Dict, Any, Optional
import torch
import torch.nn as nn


class DocumentClassifierCNN(nn.Module):
    """
    Custom 3-layer Convolutional Neural Network for lightweight document classification.
    Input shape: (B, 3, 224, 224)
    """

    def __init__(self, num_classes: int = 2, dropout: float = 0.3):
        super().__init__()
        self.model_type = "cnn"
        self.num_classes = num_classes

        # Conv Block 1: (3, 224, 224) -> (32, 112, 112)
        self.conv1 = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, stride=1, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),
        )

        # Conv Block 2: (32, 112, 112) -> (64, 56, 56)
        self.conv2 = nn.Sequential(
            nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),
        )

        # Conv Block 3: (64, 56, 56) -> (128, 28, 28)
        self.conv3 = nn.Sequential(
            nn.Conv2d(64, 128, kernel_size=3, stride=1, padding=1, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),
        )

        # Adaptive pooling to handle flexible sizes if needed
        self.adaptive_pool = nn.AdaptiveAvgPool2d((4, 4))

        # Fully Connected Classifier Head
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128 * 4 * 4, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout),
            nn.Linear(128, num_classes),
        )

        self._initialize_weights()

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode="fan_out", nonlinearity="relu")
            elif isinstance(m, (nn.BatchNorm2d, nn.BatchNorm1d)):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)
            elif isinstance(m, nn.Linear):
                nn.init.xavier_normal_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        x = self.adaptive_pool(x)
        logits = self.classifier(x)
        return logits


class MobileNetV3Classifier(nn.Module):
    """
    MobileNetV3-Small backbone with a custom binary classification head.
    """

    def __init__(self, num_classes: int = 2, pretrained: bool = True, dropout: float = 0.2):
        super().__init__()
        self.model_type = "mobilenet_v3"
        self.num_classes = num_classes

        try:
            import torchvision.models as models
            if pretrained:
                try:
                    weights = models.MobileNet_V3_Small_Weights.DEFAULT
                    base_model = models.mobilenet_v3_small(weights=weights)
                except Exception:
                    # In offline or restricted network environments
                    base_model = models.mobilenet_v3_small(weights=None)
            else:
                base_model = models.mobilenet_v3_small(weights=None)
        except ImportError as e:
            raise ImportError(
                "torchvision is required for MobileNetV3Classifier. "
                "Install it via `pip install torchvision`."
            ) from e

        # Extract feature extractor
        self.features = base_model.features
        self.avgpool = base_model.avgpool

        # Custom classification head
        in_features = base_model.classifier[0].in_features
        self.classifier = nn.Sequential(
            nn.Linear(in_features, 128),
            nn.Hardswish(),
            nn.Dropout(p=dropout),
            nn.Linear(128, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        logits = self.classifier(x)
        return logits


def build_classifier(
    model_type: str = "cnn",
    num_classes: int = 2,
    pretrained: bool = True,
    dropout: Optional[float] = None,
) -> nn.Module:
    """
    Factory function to construct a document binary classifier.

    Args:
        model_type: "cnn" (default 3-layer CNN) or "mobilenet_v3"
        num_classes: Number of target classes (default 2)
        pretrained: Whether to use pretrained weights for MobileNetV3
        dropout: Optional custom dropout rate
    """
    norm_type = model_type.lower().strip()
    if norm_type in ("cnn", "custom_cnn", "simple_cnn", "3layer_cnn"):
        p = 0.3 if dropout is None else dropout
        return DocumentClassifierCNN(num_classes=num_classes, dropout=p)
    elif norm_type in ("mobilenet", "mobilenet_v3", "mobilenet_v3_small", "mbv3"):
        p = 0.2 if dropout is None else dropout
        return MobileNetV3Classifier(num_classes=num_classes, pretrained=pretrained, dropout=p)
    else:
        raise ValueError(
            f"Unsupported model_type: '{model_type}'. Choose 'cnn' or 'mobilenet_v3'."
        )


def save_checkpoint(
    model: nn.Module,
    path: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Saves model state dict with configuration metadata.
    """
    model_type = getattr(model, "model_type", "cnn")
    num_classes = getattr(model, "num_classes", 2)
    checkpoint = {
        "model_type": model_type,
        "num_classes": num_classes,
        "state_dict": model.state_dict(),
        "metadata": metadata or {},
    }
    torch.save(checkpoint, path)


def load_checkpoint(
    path: str,
    device: Optional[torch.device] = None,
    default_model_type: str = "cnn",
) -> nn.Module:
    """
    Loads a checkpoint and instantiates the matching model.
    """
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    checkpoint = torch.load(path, map_location=device)

    # Check if this is a full checkpoint dictionary or raw state_dict
    if isinstance(checkpoint, dict) and "state_dict" in checkpoint:
        m_type = checkpoint.get("model_type", default_model_type)
        n_classes = checkpoint.get("num_classes", 2)
        model = build_classifier(model_type=m_type, num_classes=n_classes, pretrained=False)
        model.load_state_dict(checkpoint["state_dict"])
    elif isinstance(checkpoint, dict):
        # Raw state_dict
        model = build_classifier(model_type=default_model_type, num_classes=2, pretrained=False)
        model.load_state_dict(checkpoint)
    else:
        raise ValueError(f"Unrecognized checkpoint format in '{path}'")

    model.to(device)
    model.eval()
    return model


def safe_pil_to_tensor(pic: Any) -> torch.Tensor:
    """
    Safely converts a PIL Image to a float32 torch.Tensor of shape (C, H, W) normalized to [0, 1].
    Directly converts image bytes to tensor via PyTorch C++ buffer, bypassing NumPy C-API
    to prevent 'RuntimeError: Numpy is not available' when NumPy >= 2.0 is paired with PyTorch.
    """
    if isinstance(pic, torch.Tensor):
        return pic
    if hasattr(pic, "convert") and hasattr(pic, "tobytes"):
        rgb = pic.convert("RGB")
        b = bytearray(rgb.tobytes())
        tensor = torch.frombuffer(b, dtype=torch.uint8).view(rgb.height, rgb.width, 3)
        return tensor.permute(2, 0, 1).float().div(255.0)

    import torchvision.transforms.functional as TF
    return TF.to_tensor(pic)

