# Phase 16 — AI 与算法识别分类：设计规范

> 2026-05-29 | 状态：待实施
> 范围：12 项 AI/算法能力——图像、语音、文档、应用识别与分类

---

## 目标

引入本地 AI/算法层，实现图像内容分类、OCR 文字提取、人脸检测、语音转文字、文档主题分类、摘要提取、PE 元数据解析、安装包检测、恶意软件启发式评分——全部本地运行，零云依赖，AI 输出始终为建议。

## 铁律

- **全部本地运行**——不联网，不调用云端 API
- **AI 输出始终为建议**——用户手动接受后才写入分类/元数据
- **模型文件不提交到 git**——使用 .gitignore 排除，首次运行时自动下载
- **优雅降级**——模型未安装时功能不可用但不影响核心流程
- **最小依赖**——优先使用轻量模型（ONNX ≤ 50MB、Whisper small ≤ 500MB）

---

## 批次 A：图像识别（4 项）

### A1：图像内容分类

**文件：** `apps/backend/app/workers/vision/classifier.py`（新文件）

**方案：**
- 使用 ONNX Runtime + MobileNetV3 或 EfficientNet-Lite（预训练，≤20MB）
- 分类标签：动漫/漫画、照片、截图、表情包/梗图、文档扫描、图表、空白/纯色
- 输入：图像文件路径。输出：`[{label, confidence}]` 排序列表
- 模型放置：`apps/backend/data/models/image_classify.onnx`
- 通过 `/files/{id}/classify-image` API 暴露
- 前端：详情面板中显示"图片内容类型：{动漫/照片/…} (置信度 {N}%)"，含"接受"按钮写入文件标签

**边界：** 不识别具体物体（人物、车辆等）——仅做内容大类。不实时视频分析。

---

### A2：OCR 文字提取

**文件：** `apps/backend/app/workers/vision/ocr.py`（新文件）

**方案：**
- 使用 Tesseract OCR（Windows 便携版 `tesseract.exe`，随应用打包 ≈ 15MB）
- 输入：图像文件路径。输出：`{text, language, confidence}`
- 语言包：英文 (eng) + 中文简体 (chi_sim)，首次安装时下载
- 通过 `/files/{id}/ocr` API 暴露
- 前端：详情面板中显示"提取文字：{前 200 字…}"，可展开全文。含"复制全文"按钮。

**边界：** 不手写体识别。不表格结构化提取。仅限英文+中文。

---

### A3：NSFW 检测

**文件：** `apps/backend/app/workers/vision/nsfw.py`（新文件）

**方案：**
- 使用 ONNX 轻量 NSFW 模型（~5MB，基于 MobileNet 微调）
- 输出：`{sfw_score, nsfw_score}` 0-1 范围
- 通过 `/files/{id}/nsfw-check` API 暴露
- 前端：如果 nsfw_score > 0.7，在详情面板中显示黄色警告"可能包含敏感内容"。用户可手动标记或忽略。

**边界：** 不自动隐藏/删除文件。仅提供信息标记。不替代用户判断。

---

### A4：人脸检测

**文件：** `apps/backend/app/workers/vision/face_detect.py`（新文件）

**方案：**
- 使用 ONNX UltraFace 或 similar lightweight face detector（~1.5MB）
- 输出：`{face_count, faces: [{x, y, w, h, confidence}]}`
- 通过 `/files/{id}/detect-faces` API 暴露
- 前端：详情面板中显示"检测到 {N} 张人脸"，含位置标注（矩形叠加在缩略图上）

**边界：** 不人脸识别（不做身份匹配）。不情绪检测。仅计数和位置。

---

## 批次 B：语音识别（2 项）

### B1：语音转文字（STT）

**文件：** `apps/backend/app/workers/audio/transcribe.py`（新文件）

**方案：**
- 使用 `whisper-cpp`（C++ 实现，通过 Python subprocess 调用或 `whisper` Python 包绑定）
- 模型：`small`（约 500MB）或 `base`（约 150MB）——用户在首次使用时选择
- 支持格式：`.mp3`、`.wav`、`.m4a`、`.ogg`、`.flac`
- 语言：自动检测，输出语言代码 + 转录文本
- 通过 `/files/{id}/transcribe` API 暴露（后台耗时任务，使用已有的 Task 模型追踪进度）
- 前端：详情面板中显示"转录文字：{文本}"，含"复制全文"按钮。进度条展示转录进度。

**边界：** 不实时语音转文字。不说话人分离。不翻译。仅限音频文件 > 1 秒且 < 4 小时。

---

### B2：音频语言检测

**文件：** `apps/backend/app/workers/audio/lang_detect.py`（新文件）

**方案：**
- 使用 Whisper 的 `detect_language` 方法（已在 B1 中安装无需额外依赖）
- 输入：音频文件前 30 秒。输出：`{language, language_name, confidence}`
- 通过 `/files/{id}/detect-audio-language` API 暴露
- 前端：详情面板中显示"检测语言：{中文/英文/日文/…}"

**边界：** 仅 B1 模型支持的语言。Whisper 支持约 100 种语言。

---

## 批次 C：文档识别（3 项）

### C1：文档主题分类

**文件：** `apps/backend/app/workers/nlp/classifier.py`（新文件）

**方案：**
- 使用 ONNX 文本分类模型（基于 DistilBERT 或 fastText，~50MB）
- 分类标签：合同/法律、论文/学术、简历/CV、手册/指南、财务/发票、小说/文学、新闻/博客、其他
- 输入：从 PDF/DOCX/TXT 提取的文本（复用已有的 PDF `pypdfium2` 和 EPUB `EpubParser` 进行文本提取）
- 通过 `/files/{id}/classify-document` API 暴露
- 前端：详情面板中显示"文档类型：{合同/论文/…} (置信度 {N}%)"

**边界：** 不翻译。不多语言分类——仅分类为标签。

---

### C2：文档摘要提取

**文件：** `apps/backend/app/workers/nlp/summarizer.py`（新文件）

**方案：**
- 使用 TF-IDF + 句子评分（提取式摘要，不生成新句子）
- 不需要模型文件——纯算法
- 输入：文档文本。输出：`{summary: "...", sentence_count: N}`（前 3-5 句）
- 通过 `/files/{id}/summarize` API 暴露
- 前端：详情面板中显示"摘要：{前 200 字…}"，可展开

**边界：** 不生成新句子（非抽象式摘要）。不对短文档（< 5 句）做摘要。

---

### C3：文档语言检测

**文件：** `apps/backend/app/workers/nlp/lang_detect.py`（新文件）

**方案：**
- 使用 `fasttext-langdetect` 或 `langdetect` 库（轻量，~2MB 模型）
- 输入：文档文本。输出：`{language, language_name, confidence}`
- 通过 `/files/{id}/detect-document-language` API 暴露
- 前端：详情面板中显示"文档语言：{中文/英文/日文/…}"

**边界：** 代码文件不检测语言（已有 `file_type` 处理）。

---

## 批次 D：应用识别（3 项）

### D1：PE 文件元数据解析

**文件：** `apps/backend/app/workers/executable/pe_parser.py`（新文件）

**方案：**
- 使用 `pefile` Python 库（无模型文件需求，~200KB）
- 解析字段：`original_filename`、`file_description`、`product_name`、`company_name`、`file_version`、`product_version`、`machine_type`（x86/x64/ARM）、`timestamp`
- 通过 `/files/{id}/pe-metadata` API 暴露
- 前端：详情面板中显示"应用名称：{ProductName} · 版本：{FileVersion} · 公司：{CompanyName}"

**边界：** Windows-only（PE 格式）。不解析 ELF（Linux）或 Mach-O（macOS）。

---

### D2：安装包检测

**文件：** `apps/backend/app/workers/executable/installer_detect.py`（新文件）

**方案：**
- 二进制签名扫描：检测 NSIS Nullsoft Installer、Inno Setup、WiX/MSI、InstallShield 签名字节序列
- 脚本安装器检测：检查 `.bat`/`.cmd`/`.ps1`/`.sh` 脚本中的关键词（`setup`、`install`、`INSTALLDIR` 等）
- 输出：`{installer_type, confidence}`
- 通过 `/files/{id}/detect-installer` API 暴露
- 前端：详情面板中显示"安装程序类型：{NSIS/WiX/Inno/…}"

**边界：** 不提取安装参数。不模拟安装。仅做类型检测。

---

### D3：恶意软件启发式评分

**文件：** `apps/backend/app/workers/executable/malware_heuristic.py`（新文件）

**方案：**
- 基于规则（无模型文件）：检查高风险模式——检测到打包器（UPX、ASPack）、反调试字符串、可疑 API 导入（CreateRemoteThread、WriteProcessMemory）、高危文件扩展名伪装
- 输出：`{risk_score: 0-100, findings: [...]}`
- 通过 `/files/{id}/malware-heuristic` API 暴露
- 前端：如果 risk_score > 50，详情面板中显示橙色警告"可能存在风险——{N} 项异常发现"

**边界：** 不用作 AV 替代品。不执行文件。不内存扫描。仅作信息提示。

---

## 依赖关系

```
批次 A（图像）——无依赖，4 项可并行
批次 B（语音）——无依赖，2 项可并行。B2 依赖 B1 的 Whisper 安装
批次 C（文档）——无依赖，3 项可并行
批次 D（应用）——无依赖，3 项可并行

全部 4 个批次可完全并行——互不干扰
```

## 模型管理策略

- 模型文件存放路径：`apps/backend/data/models/`
- `.gitignore` 排除：`apps/backend/data/models/*`
- 首次使用时检查模型文件是否存在，若不存在则自动下载
- 下载源：GitHub Releases 或 Hugging Face（使用 `httpx` 流式下载）
- 下载进度通过已有的 Task 模型追踪
- 模型版本锁定——在 `settings.py` 或独立配置文件中指定 URL + SHA-256

## 验证

- 后端：所有已有测试通过，新增各 worker 的单元测试
- 前端：所有已有测试通过，无新的 TS 错误
- 手动冒烟：各 AI 功能对实际文件产生合理输出
- 模型下载：在干净环境中验证自动下载流程
