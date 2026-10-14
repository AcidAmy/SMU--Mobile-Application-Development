# MarkItDown 深度学习文档图像二分类路由模块 (Section 5.1)

本项目严格按照 `agent.md` 第 5.1 节要求实现，位于 `backend/classifier/`，基于 **PyTorch** 实现了一个专用于文档图像与格式预判的轻量级二分类模型体系，为 MarkItDown 核心引擎提供高效的“前置动态路由”能力。

---

## 1. 核心目标与二分类标签定义

在大模型文档转换（RAG / Document-to-Markdown）场景中，直接调用视觉大模型（OCR / Vision LLM）成本高昂且延迟大；而直接使用传统纯文本解析器遇到扫描件、复杂表格、倾斜收据时则会出现大量内容丢失与表格塌缩。

本分类器通过对输入文档渲染首页或关键页面图像进行毫秒级深度学习预判，实现**轻重分离、按需调度**：

| 类别标签 (Label) | 类别名称 (Class Name) | 典型文档形态 | 推荐处理策略 (Downstream Routing) |
| :---: | :---: | :--- | :--- |
| **0** | `standard` (普通文档) | 标准可编辑 PDF、电子版 Word、Excel、PPT、排版规范的纯文本排版页 | 直接调用 MarkItDown 本地高速解析引擎 (`convert_local` / `convert_stream`)，纯本地零 API 成本毫秒级转换 |
| **1** | `scanned_or_complex` (扫描/复杂图表文档) | 扫描件 PDF、拍照票据、发票、医疗报告影印件、多栏复杂图文排版页 | 触发 `markitdown-ocr` 插件或外部多模态视觉大模型 (LLM Vision) 进行高精度 OCR 识别与排版还原 |

---

## 2. 模型架构设计 (`model.py`)

模块同时内置了两种工业级轻量化网络，可通过参数无缝切换：

### 2.1 自定义 3 层卷积神经网络 (`DocumentClassifierCNN`)
- **设计初衷**：极轻量、零第三方预训练权重网络依赖、启动即用、无冷启动延迟，非常适合 CPU 环境与轻量容器镜像。
- **输入维度**：`(B, 3, 224, 224)` 标准 RGB 图像。
- **网络结构**：
  1. **Conv Block 1**: `Conv2d(3, 32, k=3, p=1)` $\rightarrow$ `BatchNorm2d(32)` $\rightarrow$ `ReLU` $\rightarrow$ `MaxPool2d(2, 2)`
  2. **Conv Block 2**: `Conv2d(32, 64, k=3, p=1)` $\rightarrow$ `BatchNorm2d(64)` $\rightarrow$ `ReLU` $\rightarrow$ `MaxPool2d(2, 2)`
  3. **Conv Block 3**: `Conv2d(64, 128, k=3, p=1)` $\rightarrow$ `BatchNorm2d(128)` $\rightarrow$ `ReLU` $\rightarrow$ `MaxPool2d(2, 2)`
  4. **Pooling & Classification Head**: `AdaptiveAvgPool2d((4, 4))` $\rightarrow$ `Flatten` (2048维) $\rightarrow$ `Linear(2048, 128)` $\rightarrow$ `BatchNorm1d(128)` $\rightarrow$ `ReLU` $\rightarrow$ `Dropout(0.3)` $\rightarrow$ `Linear(128, 2)`

### 2.2 MobileNetV3-Small (`MobileNetV3Classifier`)
- **设计初衷**：经典轻量级移动端 Backbone，具有高效的 Inverted Residual Block 和 Squeeze-and-Excitation (SE) 模块。
- **网络结构**：采用 `torchvision.models.mobilenet_v3_small` 作为特征抽取器，并将分类头定制为 `Linear(in_features, 128)` $\rightarrow$ `Hardswish` $\rightarrow$ `Dropout(0.2)` $\rightarrow$ `Linear(128, 2)`。

---

## 3. 训练脚本 (`train.py`)

训练脚本能够自动索引并解析 MarkItDown 内置的测试数据集：
- `packages/markitdown/tests/test_files` (如 `test.pdf`, `movie-theater-booking-2024.pdf`, `equations.docx`, `MEDRPT-2024-PAT-3847_medical_report_scan.pdf` 等)
- `packages/markitdown-ocr/tests/ocr_test_data` (如 `pdf_scanned_invoice.pdf`, `pdf_scanned_report.pdf`, `pdf_complex_layout.pdf` 等)

### 3.1 核心训练流程
1. **多格式渲染管道**：使用 `PyMuPDF (fitz)` 或 `pypdfium2` 动态将 PDF 文档渲染为高质量 RGB 图像（支持 DPI=150 自适应缩放），并读取图片（JPG/PNG）。
2. **数据增强机制 (Data Augmentation)**：
   - 随机小角度旋转 ($\pm 6^\circ$) 模拟纸张扫描倾斜；
   - 亮度/对比度随机扰动模拟光照与影印不均；
   - 扫描类别样本引入高斯模糊模拟扫描传感器噪点。
3. **优化目标**：CrossEntropyLoss + AdamW 优化器 + CosineAnnealing 学习率退火策略。
4. **指标监控与权重持久化**：计算 Train/Val Loss、Accuracy、Precision、Recall 以及 F1-score，自动保存 `weights/best_model.pth` 与 `weights/latest_model.pth`。

### 3.2 运行训练命令
```bash
# 使用自定义 3 层 CNN 进行训练 (默认)
python backend/classifier/train.py --model-type cnn --epochs 10 --batch-size 8

# 使用 MobileNetV3-Small 进行训练
python backend/classifier/train.py --model-type mobilenet_v3 --epochs 15 --batch-size 8 --lr 0.0005
```

---

## 4. 推理预判接口 (`predict.py`)

提供简单易用的 Python API 与 CLI 命令行调用方式，支持传入 **图片文件、PDF 路径、PIL Image 对象或二进制字节流**。

### 4.1 CLI 命令行快速预测
```bash
# 预测普通 PDF 文档
python backend/classifier/predict.py --input packages/markitdown/tests/test_files/test.pdf

# 预测扫描件 PDF 并输出标准 JSON
python backend/classifier/predict.py --input packages/markitdown-ocr/tests/ocr_test_data/pdf_scanned_invoice.pdf --json
```

输出示例：
```json
{
  "file_path": "packages/markitdown-ocr/tests/ocr_test_data/pdf_scanned_invoice.pdf",
  "label": 1,
  "class_name": "scanned_or_complex",
  "confidence": 0.9854,
  "probabilities": {
    "standard": 0.0146,
    "scanned_or_complex": 0.9854
  },
  "requires_ocr": true,
  "pages_analyzed": 1,
  "model_type": "cnn"
}
```

### 4.2 Python 代码中集成调用

```python
from backend.classifier import DocumentClassifier, predict_document

# 方式一：快速静态函数调用
result = predict_document("sample_invoice.pdf")
print("是否需要触发 OCR 插件:", result["requires_ocr"])

# 方式二：常驻实例批量预测
classifier = DocumentClassifier(model_type="cnn")
result = classifier.predict("document.pdf")
if result["requires_ocr"]:
    # 动态分发至视觉大模型 OCR
    pass
else:
    # 动态分发至本地轻量转换器
    pass
```

---

## 5. 目录文件结构

```text
backend/classifier/
├── __init__.py          # 模块导出定义
├── model.py             # 3 层 CNN 与 MobileNetV3-Small 网络定义及 Checkpoint 加载
├── train.py             # 自动化渲染与训练脚本 (利用 tests/test_files 与 ocr_test_data)
├── predict.py           # 推理与分类路由接口 (支持 PDF 与各类图片)
├── test_classifier.py   # 单元测试与集成测试套件
├── README.md            # 本说明文档
└── weights/             # 存放训练好的模型权重 (.pth)
```
