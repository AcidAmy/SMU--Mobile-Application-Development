# MarkItDown

[![PyPI](https://img.shields.io/pypi/v/markitdown.svg)](https://pypi.org/project/markitdown/)
![PyPI - Downloads](https://img.shields.io/pypi/dd/markitdown)

> [!IMPORTANT]
> MarkItDown performs I/O with the privileges of the current process. Like open() or requests.get(), it will access resources that the process itself can access. Sanitize your inputs in untrusted environments, and call the narrowest `convert_*` function needed for your use case (e.g., `convert_stream()`, or `convert_local()`). See the [Security Considerations](#security-considerations) section of the documentation for more information.

---

## 🎓 Full-Stack Course Project Guide (全栈项目架构与实训指南)

> [!NOTE]
> 本项目基于微软开源项目 `MarkItDown` 进行全栈工程化扩展开发，遵循 `agent.md` 开发规范，集成了 **FastAPI 异步后端**、**PyTorch 深度学习文档图像二分类路由**、**外部多模态大模型 (Vision LLM) OCR 扩展**、**SQLite 持久化与 JWT 身份认证**、**CLI / MCP (Model Context Protocol) 协议桥接** 以及 **HTML5 + Vue3 + Axios 响应式前端工作台**，是一套企业级端到端智能文档转换平台。

---

### 1. 全栈项目系统架构说明 (System Architecture)

本项目采用松耦合、高内聚的分层微服务与容器化编排架构，整体数据流向与模块划分如下图所示：

```mermaid
flowchart TD
    User["用户客户端 / 开发者"] -->|访问 Web 界面 :8080| NginxProxy["Nginx 反向代理服务器 (Port 8080)"]
    User -->|直接调用 REST API / Swagger :8000| BackendFastAPI
    User -->|CLI 命令行 / 管道操作| LocalCLI["MarkItDown CLI 引擎"]
    User -->|MCP 协议交互 (STDIO/SSE)| MCPService["MarkItDown MCP 服务 (packages/markitdown-mcp)"]

    subgraph FrontendApp ["前端工作台 (frontend/ :8080 / :5173)"]
        NginxProxy -->|静态页面分发| VueApp["Vue3 + Axios 单页应用 (SPA)"]
        VueApp --> UploadModule["拖拽上传 / URL抓取 / 格式检测"]
        VueApp --> ClassifierCard["PyTorch 分类置信度动态展示卡片"]
        VueApp --> SplitViewer["Markdown 源码与富文本实时双栏对比"]
        VueApp --> AuthHistory["JWT 鉴权登录弹窗 & 历史记录抽屉"]
    end

    NginxProxy -->|反向代理 /api/*| BackendFastAPI["FastAPI 异步服务 (backend/main.py :8000)"]

    subgraph BackendCore ["后端核心服务层 (backend/)"]
        BackendFastAPI --> SecurityLayer["安全校验层: 白名单检测 + Anti-SSRF 防御"]
        BackendFastAPI --> AuthJWT["身份认证模块: Bcrypt 加密 + JWT 签发/校验"]
        BackendFastAPI --> HistoryDB["数据持久化: SQLAlchemy ORM + SQLite (markitdown.db)"]
        
        SecurityLayer --> ConverterService["转换路由中心 (services/converter_service.py)"]
        
        subgraph DLRouter ["PyTorch 深度学习二分类引擎 (backend/classifier/)"]
            ConverterService --> DocClassifier["DocumentClassifier (CNN / MobileNetV3)"]
            DocClassifier -->|Label 0: standard (原生电子文档)| FastPath["本地极速转换 (convert_stream / convert_local)"]
            DocClassifier -->|Label 1: scanned_or_complex (扫描件/复杂报表)| SlowPath["智能 OCR / 视觉大模型增强通道"]
        end
        
        FastPath --> EngineCore["MarkItDown 转换核心 (packages/markitdown)"]
        SlowPath --> OCRPlugin["markitdown-ocr 插件 / OpenAI GPT-4o Vision API"]
        OCRPlugin --> MarkdownOutput["结构化 Markdown 产物"]
        EngineCore --> MarkdownOutput
    end

    MarkdownOutput --> BackendFastAPI
    BackendFastAPI -->|JSON 响应 + 渲染流| VueApp
```

#### 核心分层与组件职责

| 层级 (Layer) | 核心组件与文件路径 | 技术栈 | 职责与设计要点 |
| :--- | :--- | :--- | :--- |
| **前端工作台** | `frontend/` (`index.html`, `src/`) | HTML5, Vue 3, Axios, CSS3 | 提供现代 SaaS 风格 UI、拖拽上传、文件格式校验、分类置信度展示、双栏同步滚动对比与历史记录管理。支持纯 Python 静态服务与 Vite 双模启动。 |
| **网关与反代** | `frontend/nginx.conf`, `Dockerfile` | Nginx (Alpine) | 统一暴露 `8080` 端口，实现前端静态资源极速托管与 `/api/` 路径至 FastAPI 容器的反向代理，规避跨域并限制请求大小（50MB）。 |
| **后端 API** | `backend/main.py`, `backend/services/` | FastAPI, Pydantic, Uvicorn | 提供文档转换、智能分类、用户鉴权、历史管理与服务诊断 RESTful API，严格遵循窄化 API (`convert_stream`, `convert_local`) 原则。 |
| **AI 路由中心** | `backend/classifier/` | PyTorch, PyMuPDF, Torchvision | 毫秒级文档图像特征分析，自动区分普通电子文档与扫描件，实现计算成本与转换保真度的最佳平衡。 |
| **持久化与审计** | `backend/database.py`, `models.py` | SQLite, SQLAlchemy ORM | 存储用户账号（Bcrypt 散列）、转换流水（分类结果、执行耗时、状态、Markdown 产物），实现租户数据隔离。 |
| **协议扩展层** | `packages/markitdown-mcp/` | Python, MCP SDK | 支持 Model Context Protocol，可无缝接入 Claude Desktop、Cursor 等大模型宿主环境作为专用转换工具。 |

#### 安全红线设计 (Security Red Lines)
1. **严格使用窄化接口**：禁止对不可信网络输入使用宽泛的 `convert()`。文件上传强制使用二进制流接口 `md.convert_stream(stream, stream_info=...)`，本地安全文件使用 `md.convert_local()`，远程抓取使用 `md.convert_response()`。
2. **格式白名单与体积限制**：强制白名单限制（仅支持 `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.jpg`, `.png`, `.html`, `.csv`, `.json`, `.xml`, `.zip`, `.epub` 等），单文件体积上限限制为 50MB。
3. **全方位 Anti-SSRF 防御**：对远程 URL 请求严格执行 DNS 预解析与 IP 范围拦截，杜绝回环地址（`127.0.0.1`, `localhost`）、私有网络（`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`）及链路本地地址（`169.254.0.0/16`）访问。

---

### 2. 前后端启动指南 (How to Start Frontend & Backend)

系统提供 **Docker Compose 一键容器化编排** 与 **本地命令独立开发运行** 两种启动方式。

#### 方案一：通过 Docker Compose 一键启动 (推荐，生产/评测模式)

项目根目录包含完整的 `docker-compose.yml` 编排文件，涵盖后端服务、前端 Nginx 反代与 MCP 服务：

```bash
# 1. 进入项目根目录
cd markitdown

# 2. (可选) 配置环境变量：如需使用视觉大模型 OCR，可创建 .env 文件注入 API Key
# echo "OPENAI_API_KEY=sk-your-openai-key" > .env
# echo "OPENAI_MODEL=gpt-4o" >> .env

# 3. 构建并后台启动全部容器集群
docker compose up --build -d

# 4. 查看各容器健康状态 (等待 backend 与 frontend 均显示 healthy)
docker compose ps
```

**服务访问端点总览**：
- 🌐 **前端交互工作台**：[http://localhost:8080](http://localhost:8080)
- 📖 **后端交互式 Swagger UI**：[http://localhost:8000/api/docs](http://localhost:8000/api/docs)
- 📑 **后端 ReDoc 接口文档**：[http://localhost:8000/api/redoc](http://localhost:8000/api/redoc)
- 💓 **系统健康与诊断接口**：[http://localhost:8000/api/health](http://localhost:8000/api/health)

**常用维护命令**：
```bash
# 查看后端实时日志
docker compose logs -f markitdown-backend

# 查看前端实时日志
docker compose logs -f markitdown-frontend

# 停止并移除容器集群
docker compose down
```

---

#### 方案二：通过本地命令直接启动 (本地开发调试模式)

##### 步骤 1：准备 Python 虚拟环境与依赖安装
本项目要求 Python 3.10 ~ 3.14（推荐 **Python 3.12**）：

```bash
# 1. 创建虚拟环境并激活
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
# Windows CMD: .venv\Scripts\activate.bat
# Windows PowerShell: .venv\Scripts\Activate.ps1

# 2. 安装核心转换库及其全部可选格式扩展
pip install -e 'packages/markitdown[all]'

# 3. 安装 OCR 插件与 MCP 服务组件
pip install -e 'packages/markitdown-ocr'
pip install -e 'packages/markitdown-mcp'

# 4. 安装后端 API 与 PyTorch 深度学习依赖
pip install -r backend/requirements.txt
```

> [!TIP]
> 如果本地下载 PyTorch 较慢，推荐使用 CPU 轻量轮子：
> `pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu`

##### 步骤 2：启动 FastAPI 后端服务
在激活虚拟环境的状态下，在项目根目录下执行：

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
- 后端服务将在 `http://127.0.0.1:8000` 启动；
- 启动时生命周期钩子（Lifespan）会自动初始化 SQLite 数据库表，并预热加载 PyTorch 分类模型；
- 可直接访问 [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs) 进行在线接口测试。

##### 步骤 3：启动前端 Web 界面
前端提供两种运行方式：

- **方式 A (极速启动，纯 Python 零依赖，推荐)**：
  ```bash
  # 无需安装 Node.js 或 npm，直接运行内置轻量服务器
  python frontend/serve.py
  ```
  在浏览器访问：[http://localhost:5173](http://localhost:5173) 即可畅享完整的前端交互！页面会自动连接本地 `http://127.0.0.1:8000/api`。

- **方式 B (基于 Vite 模块化调试，需 Node.js)**：
  ```bash
  cd frontend
  npm install
  npm run dev
  ```

---

### 3. PyTorch 深度学习二分类模块设计原理 (Classifier Design)

模块代码位于 `backend/classifier/`，是整个平台实现“**轻重分离、成本与延时最优调度**”的核心智能枢纽。

#### 3.1 设计初衷与业务痛点
1. **传统解析局限**：常规文本解析器（如 pdfminer、docx 提取器）解析规范电子文档极快（<100ms），但在遇到**纯图片扫描件、倾斜票据、跨页复杂财务报表**时，提取结果会出现大面积文本缺失、表格严重塌缩甚至解析失败。
2. **大模型成本与延时困境**：直接将所有文档无差别调用视觉多模态大模型（Vision LLM）或 OCR 插件，虽然识别率高，但每页转换成本陡增、延时高达数秒至数十秒，存在巨大资源浪费。
3. **解决方案**：引入轻量级深度学习前置二分类器，在正式转换前对文档进行**毫秒级图像判别**，根据预测置信度动态分流。

#### 3.2 标签体系与路由决策

| 类别标签 (Label) | 类别名称 (Class Name) | 典型输入特征 | 触发下游处理策略 (Downstream Routing) |
| :---: | :---: | :--- | :--- |
| **0** | `standard`<br>(常规电子文档) | 包含原生文本矢量流、标准排版的 PDF/Word/PPT/Excel 等 | **极速本地解析通道**：直接调用 MarkItDown 本地解析引擎 (`convert_stream` / `convert_local`)，纯本地 CPU 处理，**0 API 成本，50~200ms 毫秒级输出**。 |
| **1** | `scanned_or_complex`<br>(扫描件/复杂报表) | 扫描图像、拍照发票、手写倾斜票据、密集多栏嵌套表格 | **多模态增强通道**：动态调度 `markitdown-ocr` 插件或外部多模态大模型（OpenAI GPT-4o 等），执行版面还原与智能 OCR 文本重构。 |

#### 3.3 双模型网络架构实现 (`backend/classifier/model.py`)

模块同时内置了两种工业级轻量模型，可通过环境变量 `CLASSIFIER_MODEL_TYPE=cnn` 或 `mobilenet_v3` 无缝切换：

1. **自研 3 层卷积神经网络 (`DocumentClassifierCNN`，系统默认)**：
   - **设计理念**：极致轻量、零第三方预训练权重网络依赖、启动即用、无网络拉取失败风险，CPU 推理时间 $< 15\text{ms}$，模型参数量 $< 1\text{MB}$。
   - **输入规格**：`(Batch, 3, 224, 224)` 标准归一化 RGB 图像。
   - **特征抽取层**：
     - Block 1: `Conv2d(3, 32, k=3, p=1)` $\rightarrow$ `BatchNorm2d(32)` $\rightarrow$ `ReLU` $\rightarrow$ `MaxPool2d(2, 2)`
     - Block 2: `Conv2d(32, 64, k=3, p=1)` $\rightarrow$ `BatchNorm2d(64)` $\rightarrow$ `ReLU` $\rightarrow$ `MaxPool2d(2, 2)`
     - Block 3: `Conv2d(64, 128, k=3, p=1)` $\rightarrow$ `BatchNorm2d(128)` $\rightarrow$ `ReLU` $\rightarrow$ `MaxPool2d(2, 2)`
   - **自适应池化与分类头**：
     - `AdaptiveAvgPool2d((4, 4))` 降维锁定尺寸，展平为 2048 维向量；
     - `Linear(2048, 128)` $\rightarrow$ `BatchNorm1d(128)` $\rightarrow$ `ReLU` $\rightarrow$ `Dropout(p=0.3)` $\rightarrow$ `Linear(128, 2)`；
     - 输出经过 Softmax 后分别对应两类的预测概率。
   - **参数初始化**：卷积层采用 Kaiming Normal（He 正态分布），线性层采用 Xavier Normal，确保在无预训练权重时冷启动快速收敛。

2. **MobileNetV3-Small (`MobileNetV3Classifier`)**：
   - 基于深度可分离卷积（Depthwise Separable Convolution）与 Squeeze-and-Excitation (SE) 通道注意力机制；
   - 定制顶层全连接头为 `Linear(in_features, 128)` $\rightarrow$ `Hardswish` $\rightarrow$ `Dropout(0.2)` $\rightarrow$ `Linear(128, 2)`，适配更复杂的大规模跨域文档判别场景。

#### 3.4 训练与数据增强管道 (`backend/classifier/train.py`)
- **多格式渲染管道**：基于 `PyMuPDF (fitz)` 将各类测试 PDF 文档自适应渲染为 150 DPI 高清位图，并自动聚合测试数据集（`packages/markitdown/tests/test_files` 与 `packages/markitdown-ocr/tests/ocr_test_data`）。
- **专业领域数据增强**：
  - **模拟扫描仪进纸微小倾斜**：随机小角度旋转 ($\pm 6^\circ$)；
  - **模拟影印光照与墨迹不均**：随机亮度与对比度扰动 (`ColorJitter`)；
  - **模拟低分辨率扫描传感器噪点**：对扫描件样本注入随机高斯模糊 (`GaussianBlur`)。
- **训练超参数与策略**：采用 `CrossEntropyLoss` 交叉熵损失函数，结合 `AdamW` 权重衰减优化器与 `CosineAnnealingLR` 余弦退火学习率调度，最佳模型权重自动持久化至 `weights/best_model.pth`。

#### 3.5 命令行推理验证
```bash
# 预测普通 PDF 文档 (预期输出 label: 0)
python backend/classifier/predict.py --input packages/markitdown/tests/test_files/test.pdf --json

# 预测扫描件 PDF 文档 (预期输出 label: 1, requires_ocr: true)
python backend/classifier/predict.py --input packages/markitdown-ocr/tests/ocr_test_data/pdf_scanned_invoice.pdf --json
```

---

### 4. 系统测试账号与密码 (Test Accounts & Credentials)

系统内置 SQLite 数据库已自动预置基础测试账号，同时也支持无缝访客模式与自主注册：

#### 4.1 预置测试账号信息

| 用户名 (Username) | 登录密码 (Password) | 邮箱 (Email) | 账户状态 | 权限与用途 |
| :--- | :--- | :--- | :---: | :--- |
| **`demouser`** | **`password123`** | *(可选留空)* | ✅ 激活 (Active) | **系统默认测试演示账号**。登录后享有专属独立转换历史记录存储、跨设备查询与安全删除权限。 |
| **`Deepseek1`** | *(注册设定密码)* | `Deepseek@gmail.com` | ✅ 激活 (Active) | 演示已绑邮箱的历史测试账户。 |

#### 4.2 访客免密体验模式 (Guest Mode)
- **免登录直接使用**：未登录的访客用户可直接进入前端工作台，享受文档拖拽上传、PyTorch 智能分类预判、本地极速解析以及 Markdown 实时双栏预览等全部核心功能。
- **注册新账号**：用户可在前端右上角点击“登录/注册”弹窗随时自主注册新账号（密码长度 $\ge 6$ 位），系统通过 `bcrypt` 自动盐值哈希加密入库，并自动签发 JWT Bearer Token。

#### 4.3 API 与 Swagger UI 快速鉴权测试
在后端文档界面 [http://localhost:8000/api/docs](http://localhost:8000/api/docs) 中：
1. 点击右上角绿色的 **`Authorize`** 按钮；
2. 在弹出窗口的 `username` 中填入 **`demouser`**，`password` 中填入 **`password123`**；
3. 点击 **Authorize** 授权，后续对 `/api/records` 等受保护路由的请求将自动附带 JWT Bearer Token。

---

MarkItDown is a lightweight Python utility for converting various files to Markdown for use with LLMs and related text analysis pipelines. To this end, it is most comparable to [textract](https://github.com/deanmalmgren/textract), but with a focus on preserving important document structure and content as Markdown (including: headings, lists, tables, links, etc.) While the output is often reasonably presentable and human-friendly, it is meant to be consumed by text analysis tools -- and may not be the best option for high-fidelity document conversions for human consumption.

MarkItDown currently supports the conversion from:

- PDF
- PowerPoint
- Word
- Excel
- Images (EXIF metadata and OCR)
- Audio (EXIF metadata and speech transcription)
- HTML
- Text-based formats (CSV, JSON, XML)
- ZIP files (iterates over contents)
- YouTube URLs
- EPubs
- ... and more!

## Why Markdown?

Markdown is extremely close to plain text, with minimal markup or formatting, but still
provides a way to represent important document structure. Mainstream LLMs, such as
OpenAI's GPT-4o, natively "_speak_" Markdown, and often incorporate Markdown into their
responses unprompted. This suggests that they have been trained on vast amounts of
Markdown-formatted text, and understand it well. As a side benefit, Markdown conventions
are also highly token-efficient.

## Prerequisites
MarkItDown requires Python 3.10 through 3.14. It is recommended to use a virtual environment to avoid dependency conflicts.

With the standard Python installation, you can create and activate a virtual environment using the following commands:

```bash
python -m venv .venv
source .venv/bin/activate
```

If using `uv`, you can create a virtual environment with:

```bash
uv venv --python=3.12 .venv
source .venv/bin/activate
# NOTE: Be sure to use 'uv pip install' rather than just 'pip install' to install packages in this virtual environment
```

If you are using Anaconda, you can create a virtual environment with:

```bash
conda create -n markitdown python=3.12
conda activate markitdown
```

## Installation

To install MarkItDown, use pip: `pip install 'markitdown[all]'`. Alternatively, you can install it from the source:

```bash
git clone git@github.com:microsoft/markitdown.git
cd markitdown
pip install -e 'packages/markitdown[all]'
```

## Usage

### Command-Line

```bash
markitdown path-to-file.pdf > document.md
```

Or use `-o` to specify the output file:

```bash
markitdown path-to-file.pdf -o document.md
```

You can also pipe content:

```bash
cat path-to-file.pdf | markitdown
```

### Optional Dependencies
MarkItDown has optional dependencies for activating various file formats. Earlier in this document, we installed all optional dependencies with the `[all]` option. However, you can also install them individually for more control. For example:

```bash
pip install 'markitdown[pdf, docx, pptx]'
```

will install only the dependencies for PDF, DOCX, and PPTX files.

At the moment, the following optional dependencies are available:

* `[all]` Installs all optional dependencies
* `[pptx]` Installs dependencies for PowerPoint files
* `[docx]` Installs dependencies for Word files
* `[xlsx]` Installs dependencies for Excel files
* `[xls]` Installs dependencies for older Excel files
* `[pdf]` Installs dependencies for PDF files
* `[outlook]` Installs dependencies for Outlook messages
* `[az-doc-intel]` Installs dependencies for Azure Document Intelligence
* `[az-content-understanding]` Installs dependencies for Azure Content Understanding
* `[audio-transcription]` Installs dependencies for audio transcription of wav and mp3 files
* `[youtube-transcription]` Installs dependencies for fetching YouTube video transcription

### Plugins

MarkItDown also supports 3rd-party plugins. Plugins are disabled by default. To list installed plugins:

```bash
markitdown --list-plugins
```

To enable plugins use:

```bash
markitdown --use-plugins path-to-file.pdf
```

To find available plugins, search GitHub for the hashtag `#markitdown-plugin`. To develop a plugin, see `packages/markitdown-sample-plugin`.

#### markitdown-ocr Plugin

The `markitdown-ocr` plugin adds OCR support to PDF, DOCX, PPTX, and XLSX converters, extracting text from embedded images using LLM Vision — the same `llm_client` / `llm_model` pattern that MarkItDown already uses for image descriptions. No new ML libraries or binary dependencies required.

**Installation:**

```bash
pip install markitdown-ocr
pip install openai  # or any OpenAI-compatible client
```

**Usage:**

Pass the same `llm_client` and `llm_model` you would use for image descriptions:

```python
from markitdown import MarkItDown
from openai import OpenAI

md = MarkItDown(
    enable_plugins=True,
    llm_client=OpenAI(),
    llm_model="gpt-4o",
)
result = md.convert("document_with_images.pdf")
print(result.markdown)
```

If no `llm_client` is provided the plugin still loads, but OCR is silently skipped and the standard built-in converter is used instead.

See [`packages/markitdown-ocr/README.md`](packages/markitdown-ocr/README.md) for detailed documentation.

### Azure Content Understanding

[Azure Content Understanding](https://learn.microsoft.com/azure/ai-services/content-understanding/) provides higher-quality conversion with structured field extraction (YAML front matter), multi-modal support (documents, images, audio, video), and configurable analyzers.

Install: `pip install 'markitdown[az-content-understanding]'`

#### When to use Content Understanding

Content Understanding is ideal when you need capabilities beyond what built-in or Document Intelligence converters provide:

- **Audio and video files** — CU is the only option for video, and the higher-quality cloud option for audio. Built-in converters have no video support and only basic audio transcription.
- **Structured field extraction** — [Prebuilt](https://learn.microsoft.com/azure/ai-services/content-understanding/concepts/prebuilt-analyzers) or [custom-built](https://learn.microsoft.com/azure/ai-services/content-understanding/how-to/customize-analyzer-content-understanding-studio?tabs=portal) analyzers extract domain-specific fields (invoice amounts, receipt dates, contract clauses) serialized as YAML front matter. Neither built-in nor Doc Intel integration exposes fields.
- **Higher-quality document extraction** — Cloud-based layout analysis and OCR for scanned PDFs, complex tables, and multi-page documents.
- **Single API for all modalities** — One `cu_endpoint` handles documents, images, audio, and video with automatic analyzer routing.

| Capability | Built-in converters | Azure Document Intelligence | Azure Content Understanding |
|------------|---------------------|-----------------------------|-----------------------------|
| Document conversion | Offline, format-specific extraction | Cloud layout extraction | Cloud multimodal extraction |
| Structured fields | Not available | Not exposed by this integration | YAML front matter from analyzer fields |
| Custom analyzers | Not available | Not configurable in this integration | Supported with `cu_analyzer_id` |
| Audio and video | Basic audio, no video | Not supported | Audio and video analyzers |
| Cost | Local compute only | Billable Azure API calls | Billable Azure API calls |

**CLI:**

```bash
markitdown path-to-file.pdf --use-cu --cu-endpoint "<content_understanding_endpoint>"
```

The endpoint can also be set once in the environment, so callers only need `--use-cu`:

```bash
export MARKITDOWN_CU_ENDPOINT="<content_understanding_endpoint>"
markitdown path-to-file.pdf --use-cu
```

**Python API:**

```python
from markitdown import MarkItDown

# Zero-config — auto-selects analyzer per file type
md = MarkItDown(cu_endpoint="<content_understanding_endpoint>")
result = md.convert("report.pdf")   # documents → prebuilt-documentSearch
result = md.convert("meeting.mp4")  # video → prebuilt-videoSearch
result = md.convert("call.wav")     # audio → prebuilt-audioSearch
print(result.markdown)
```

**With a custom analyzer** (for domain-specific field extraction):

```python
md = MarkItDown(
    cu_endpoint="<content_understanding_endpoint>",
    cu_analyzer_id="my-invoice-analyzer",
)
result = md.convert("invoice.pdf")
print(result.markdown)
# Output includes YAML front matter with extracted fields:
# ---
# contentType: document
# fields:
#   VendorName: CONTOSO LTD.
#   InvoiceDate: '2019-11-15'
# ---
# <!-- page 1 -->
# ...
```

When `cu_analyzer_id` is set, the converter automatically scopes it to compatible file types based on the analyzer's modality. Incompatible types (e.g., audio files with a document analyzer) auto-route to default prebuilt analyzers.

**Cost note:** Each `convert()` call for a CU-routed format is a billable Azure API call. Use `cu_file_types` to restrict which formats route to CU:

```python
from markitdown.converters import ContentUnderstandingFileType

md = MarkItDown(
    cu_endpoint="<content_understanding_endpoint>",
    cu_file_types=[ContentUnderstandingFileType.PDF],  # only PDFs use CU
)
```

More information about Azure Content Understanding can be found [here](https://learn.microsoft.com/azure/ai-services/content-understanding/).

### Azure Document Intelligence

To use Microsoft Document Intelligence for conversion:

```bash
markitdown path-to-file.pdf -o document.md -d -e "<document_intelligence_endpoint>"
```

The endpoint can also be set once in the environment, so callers only need `-d`:

```bash
export MARKITDOWN_DOCINTEL_ENDPOINT="<document_intelligence_endpoint>"
markitdown path-to-file.pdf -o document.md -d
```

More information about how to set up an Azure Document Intelligence Resource can be found [here](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/how-to-guides/create-document-intelligence-resource?view=doc-intel-4.0.0)

### Python API

Basic usage in Python:

```python
from markitdown import MarkItDown

md = MarkItDown(enable_plugins=False) # Set to True to enable plugins
result = md.convert("test.xlsx")
print(result.markdown)
```

Document Intelligence conversion in Python:

```python
from markitdown import MarkItDown

md = MarkItDown(docintel_endpoint="<document_intelligence_endpoint>")
result = md.convert("test.pdf")
print(result.markdown)
```

To use Large Language Models for image descriptions (currently only for pptx and image files), provide `llm_client` and `llm_model`:

```python
from markitdown import MarkItDown
from openai import OpenAI

client = OpenAI(max_retries=5)
md = MarkItDown(llm_client=client, llm_model="gpt-4o", llm_prompt="optional custom prompt")
result = md.convert("example.jpg")
print(result.markdown)
```

`max_retries` controls the OpenAI client's automatic retries for retryable errors (the default is 2); `5` allows up to six attempts with backoff. See the [OpenAI SDK retry documentation](https://github.com/openai/openai-python#retries).

If any attempt succeeds, image conversion continues normally. If the client raises an error after exhausting its retries, or encounters a non-retryable error, MarkItDown tries other applicable converters and raises `FileConversionException` only if none succeeds.

### Docker

```sh
docker build -t markitdown:latest .
docker run --rm -i markitdown:latest < ~/your-file.pdf > output.md
```

## Contributing

Before starting significant work, please read [What to Contribute](#what-to-contribute), which describes what is in and out of scope for this repository.

This project welcomes contributions and suggestions. Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

### What to Contribute

MarkItDown is a Python utility for converting files to Markdown for use with LLMs and related text analysis pipelines. This repository is intended to provide Python libraries that can be incorporated into other systems — not the end-user applications built on top of them.

#### In scope

- Improvements to the fidelity of existing converters (New formats are added sparingly -- especially if they incur new dependencies. In most cases, new formats can be better supported via [3rd-party plugins](#extending-markitdown-without-changing-this-repository).)
- Bug fixes, performance improvements, and security fixes
- The `markitdown` command-line interface
- The `markitdown-mcp` package
- Tests, documentation, and developer tooling

#### Out of scope

We cannot accept additional applications, services, or servers. This includes:

- Web servers, REST or HTTP APIs, and hosted conversion services
- Web frontends and browser-based user interfaces
- Desktop and mobile applications (PyQt, PySide, Tkinter, Electron, Flutter, and similar)

Projects like these are genuinely useful, and we would rather see them thrive than be turned away. If you are interested in providing a web service, API, or graphical application for MarkItDown, please maintain it as a separate package or project that depends on [`markitdown` from PyPI](https://pypi.org/project/markitdown/).

### Extending MarkItDown Without Changing This Repository

MarkItDown supports 3rd-party plugins, so support for a new format can be published and installed independently of this repository:

```sh
markitdown --list-plugins
markitdown --use-plugins path-to-file.pdf
```

See `packages/markitdown-sample-plugin` to get started, and tag your repository `#markitdown-plugin` so that others can find it.

### How to Contribute

You can help by looking at issues or helping review PRs. We have also marked some issues as 'open for contribution' and PRs as 'open for reviewing' to help facilitate community contributions. These labels are suggestions; contributions within the scope described above are welcome.

<div align="center">

|            | All                                                          | Especially Needs Help from Community                                                                                                      |
| ---------- | ------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------- |
| **Issues** | [All Issues](https://github.com/microsoft/markitdown/issues) | [Issues open for contribution](https://github.com/microsoft/markitdown/issues?q=is%3Aissue+is%3Aopen+label%3A%22open+for+contribution%22) |
| **PRs**    | [All PRs](https://github.com/microsoft/markitdown/pulls)     | [PRs open for reviewing](https://github.com/microsoft/markitdown/pulls?q=is%3Apr+is%3Aopen+label%3A%22open+for+reviewing%22)              |

</div>

### Running Tests and Checks

- Navigate to the MarkItDown package:

  ```sh
  cd packages/markitdown
  ```

- Install `hatch` in your environment and run tests:

  ```sh
  pip install hatch  # Other ways of installing hatch: https://hatch.pypa.io/dev/install/
  hatch shell
  hatch test
  ```

  (Alternative) Use the Devcontainer which has all the dependencies installed:

  ```sh
  # Reopen the project in Devcontainer and run:
  hatch test
  ```

- Run pre-commit checks before submitting a PR: `pre-commit run --all-files`

### Security Considerations

MarkItDown performs I/O with the privileges of the current process. Like `open()` or `requests.get()`, it will access resources that the process itself can access.

**Sanitize your inputs:** Do not pass untrusted input directly to MarkItDown. If any part of the input may be controlled by an untrusted user or system, such as in hosted or server-side applications, it must be validated and restricted before calling MarkItDown. Depending on your environment, this may include restricting file paths, limiting URI schemes and network destinations, and blocking access to private, loopback, link-local, or metadata-service addresses.

**Call only the conversion method you need:** Prefer the narrowest conversion API that fits your use case. MarkItDown's `convert()` method is intentionally permissive and can handle local files, remote URIs, and byte streams. If your application only needs to read local files, call `convert_local()` instead. If you need more control over URI fetching, call `requests.get()` yourself and pass the response object to `convert_response()`. For maximum control, open a stream to the input you want converted and call `convert_stream()`.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft
trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
