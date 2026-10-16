# MarkItDown Vue3 + Axios 前端工作台 (Section 5.4)

本项目为 `MarkItDown` 全栈平台的前端用户交互界面，严格遵循 `agent.md` 第 5.4 节规范构建，基于 **Vue 3 + Axios** 打造了一款清爽干净、功能完备的现代文档智能转换与排版工作台。

---

## 🌟 核心功能亮点

1. **清爽现代的界面设计 (Modern Clean UI)**
   - 采用精致的 SaaS 级极简设计语言，以 Slate/Blue 为基调，配合 Emerald（常规文档）与 Amber（扫描件）动态色彩标识。
   - 具备卡片阴影、平滑动画微交互与 Toast 浮动提示通知。

2. **JWT 身份认证与权限管理 (JWT Auth Modal)**
   - 内置简洁优雅的模态弹窗，无缝支持“账号登录”与“新用户注册”。
   - 注册成功后自动登录并签发 JWT Access Token，持久化存储于本地。
   - Axios 请求拦截器全自动注入 `Authorization: Bearer <token>` 请求头。
   - Axios 响应拦截器监听 401 凭据失效事件，自动降级至访客模式并引导重新登录。
   - 完善的访客模式：无需登录即可自由转换并查看文档；登录后可永久保存专属转换记录并支持随时删除。

3. **拖拽上传与全格式支持 (Drag & Drop Upload)**
   - 直观的拖拽上传区域，支持拖拽悬浮高亮与点击文件选择。
   - 严格遵循 `agent.md` 第 3.2 节白名单限制，支持 `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.jpg`, `.png`, `.html`, `.csv`, `.json`, `.xml`, `.zip`, `.epub` 等多种格式。
   - 客户端前置体积检测（最大 50MB）与格式即时校验。
   - 包含独立子面板支持“远程 URL 网页/文档抓取”（协同后端 Anti-SSRF 严格防御机制）。

4. **PyTorch 深度学习二分类结果展示 (PyTorch Classifier Card)**
   - 实时呈现文档的深度学习二分类预判结果：
     - **“常规电子文档” (Standard Document - Label 0)**：翠绿色徽标，指示文档排版规范、含原生文本流，推荐执行本地轻量级零成本毫秒解析。
     - **“扫描件 / 复杂图表” (Scanned & Complex - Label 1)**：琥珀橙色徽标，指示文档具有扫描噪点、倾斜或多栏复杂表格，推荐调度多模态视觉大模型 OCR 还原。
   - 动态双色渐变置信度进度条（如 `98.6% 置信度`）及 `standard` / `scanned_or_complex` 各类别概率分布明细。
   - 提供“仅执行分类预判”快捷按钮，方便单测与算法路由验证。

5. **Markdown 源码与预览双栏对比 (Dual-Pane Split View)**
   - **左栏 (源码模式)**：等宽字体排版、代码行数与字符统计，提供一键复制代码与一键导出下载 `.md` 文件功能。
   - **右栏 (富文本渲染预览)**：基于 GitHub 风格渲染，完整支持标题层级、表格、引用块、代码语法高亮与任务清单。
   - **快捷控制栏**：支持“双栏对比”、“仅看源码”、“仅看预览”三种视图无缝切换，支持两栏“同步滚动 (Sync Scroll)”以及“全屏专注模式”。

6. **历史转换记录与管理 (Conversion History List)**
   - 呼出式历史记录抽屉，展示历史文件名、文件大小、PyTorch 分类标签、OCR 使用状态、处理耗时与创建时间。
   - 支持关键词即时搜索过滤。
   - 支持一键“查看预览”（将指定记录的内容载入双栏对比器查看）与登录用户专属的“删除记录”操作。

---

## 🚀 快速启动与运行

前端设计为“零编译依赖即可运行”与“支持 Vite 模块化构建”双重兼容架构，您可通过以下任意一种方式启动：

### 方式一：Python 极速启动 (推荐，无需安装 Node.js)
```bash
# 在项目根目录或 frontend 目录下运行：
python frontend/serve.py
```
启动后在浏览器打开：[http://localhost:5173](http://localhost:5173) 即可直接体验！

### 方式二：使用 Vite 启动 (若已安装 Node.js)
```bash
cd frontend
npm install
npm run dev
```

### 方式三：Docker 容器化部署 (Nginx 反向代理)
```bash
cd frontend
docker build -t markitdown-frontend .
docker run -d -p 80:80 --name markitdown-web markitdown-frontend
```

---

## 📁 目录结构说明

```text
frontend/
├── index.html                   # HTML 页面主入口
├── serve.py                     # Python 零依赖轻量本地开发服务器
├── package.json                 # npm 依赖与 scripts 配置
├── vite.config.js               # Vite 配置文件
├── Dockerfile                   # Nginx 容器镜像文件
├── nginx.conf                   # Nginx 反向代理与 SPA 路由配置
├── README.md                    # 本说明文档
└── src/
    ├── main.js                  # Vue3 实例挂载入口
    ├── App.js                   # 顶层页面主容器与全局状态响应
    ├── config.js                # API Base URL 自动探测与持久化配置
    ├── api/                     # Axios 模块封装
    │   ├── client.js            # Axios 实例与 JWT 拦截器 (Bearer Token / 401 处理)
    │   ├── auth.js              # 登录、注册、获取用户信息 API
    │   ├── convert.js           # 文件上传转换、URL 转换、独立分类预判 API
    │   ├── records.js           # 历史转换记录增删查 API
    │   └── system.js            # 后端服务健康与分类器状态检测 API
    ├── components/              # Vue3 组件库
    │   ├── Navbar.js            # 顶部导航栏 (品牌、后端状态、历史记录、登录状态)
    │   ├── AuthModal.js         # JWT 登录与注册弹窗
    │   ├── UploadArea.js        # 文件拖拽上传与 URL 转换配置面板
    │   ├── ClassifierCard.js    # PyTorch 分类预测结果与置信度卡片
    │   ├── MarkdownViewer.js    # Markdown 源码与预览双栏对比联动器
    │   ├── HistoryModal.js      # 历史记录列表弹窗
    │   ├── HealthModal.js       # 后端服务诊断与接口地址自定义弹窗
    │   └── Toast.js             # 消息轻提示系统
    └── css/
        └── style.css            # 现代 UI 完整样式体系
```
