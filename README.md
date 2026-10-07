# Smart-Toolkit

> 一堆解决具体小问题的实用工具。
> 每个工具都遵循三条原则：**默认安全、出问题能回滚、说人话的文档。**

---

## filekit —— 文件整理工具箱

**在浏览器里点几下**：选文件夹 → 预览 → 确认执行 → 随时回退。

```
文档1.docx           →  DOC_合同_文档1_2610071530.docx
工作簿1.xlsx          →  XLS_报价单_工作簿1_2610071530.xlsx
Logo image 头像.png   →  IMG_Logo_image_头像_2610071530.png
扫描件001.png         →  IMG_发票_扫描件001_2610071530.png     ← 图片 OCR
方案 最终版.docx       →  DOC_方案_方案_2610071530.docx
```

三件事：
1. **规范文件名** —— 去空格/废话词，加类型前缀，加时间戳
2. **读内容归类** —— 38 个分类（合同/发票/方案/需求/测试报告…），支持 Word/Excel/PPT/PDF/图片OCR
3. **可回退** —— 每次操作写日志，随时一键还原

---

## 一条命令启动

| 系统 | 命令 |
|---|---|
| **Windows** | 双击 `start.bat` |
| **Linux / macOS** | `bash start.sh` |
| **已有 Python 环境** | `python3 server.py` |

启动后**浏览器自动打开**（地址 `http://127.0.0.1:8765`），页面：

```
[整理文件]  ① 选择文件夹（可加多个 = 批量）→ ② 处理方式 → ③ 预览 → 确认执行
[回退]      ① 选文件夹 → ② 选历史记录 → 点回退
```

**首次运行**会自动装 Python 依赖（`start.sh` / `start.bat` 会做这件事）；
只用重命名功能的话，连依赖都不用装。

### 常用参数

```bash
python3 server.py                 # 默认端口 8765，自动开浏览器
python3 server.py --port 8899     # 换端口
python3 server.py --no-browser    # 不自动开浏览器
bash start.sh --deps              # 只装依赖，不启动
```

---

## 代码更新后，页面怎么自动生效（热更新）

**浏览器收不到服务端主动推送**（HTTP 无状态），所以用 **SSE（Server-Sent Events）** 保持一条长连接，
服务端盯着自己的源码文件，一有变化就推一条消息给所有打开的页面。

| 你改了什么 | 页面会怎样 |
|---|---|
| 前端 `web/index.html` | 服务端推送 → 页面 **3 秒后自动刷新**（有未提交的改名时会先问你，避免丢输入）|
| 后端 `server.py` / `filekit.py` | 底部弹出提示条：**「检测到后端代码更新　[立即重启服务] [仅刷新页面]」** |
| 上游 GitHub 有新版本 | 启动时后台查一次，有新版就提示 **「上游已有新版本 vX.Y　[查看更新]」**（连不上则静默跳过）|

**「立即重启服务」** = 服务原地重启（`os.execv`），**端口不变、页面自动重连**，不用关窗口重开。

> 手动更新也一样省事：`bash start.sh` 会自动检测并停掉旧实例，再起新版本。
> 页头右上角永远显示当前版本号（如 `v3.3`），一眼就能确认跑的是不是新版。

## 不用网页？命令行一样用

```bash
python3 tools/filekit/filekit.py auto --dir "./我的文件夹" --verbose      # 预览
python3 tools/filekit/filekit.py auto --dir "./我的文件夹" --apply        # 执行
python3 tools/filekit/filekit.py rollback "./文件夹/_filekit_log_xxx.json" # 回退
python3 tools/filekit/filekit.py doctor                                   # 检查环境
```

| 模式 | 用途 |
|---|---|
| `rename` | 只按文件名规范（**零依赖**）|
| `classify` | 读内容归类 |
| `auto` | 智能：能读内容就归类，否则按文件名 |

---

## 功能一览

| 功能 | 说明 | 可用模式 | 需要依赖 |
|---|---|---|---|
| **文件名清理** | 去空格、非法字符、括号；去"最终版/副本/final"等废话词 | 全部 | 否 |
| **类型前缀** | 按扩展名自动加 `IMG`/`DOC`/`XLS`/`PPT`/`PDF`/`AUD`/`VID`/`ZIP` | 全部 | 否 |
| **内容归类** | 读文档正文，判断属于 **38 类**中的哪一类 | classify / auto | 是 |
| **图片 OCR** | 图片中文 OCR 后再判断类别（发票、合同扫描件）| classify / auto | 是（**pip 可装**）|
| **时间戳入名** | 文件名末尾加 `YYMMDDHHMM`（精确到分钟）| 全部 | 否 |
| **版本号保留** | 原文件名里的 `v1`/`v2` 原样保留 | 全部 | 否 |
| **数字补零** | `头像1` → `头像01`（排序正确）| 全部 | 否 |
| **三级防冲突** | 时间戳 → 序号 → 疑似同名报告 | 全部 | 否 |
| **疑似同名报告** | 发现同一文档多份时，列清单由你决定 | 全部 | 否 |
| **预览模式** | 默认不改任何文件，只看会改成什么 | 全部 | 否 |
| **日志留痕** | 每次执行写 JSON 日志（谁改成了什么）| 全部 | 否 |
| **一键回退** | 按日志逆序还原；网页版可按文件夹选记录回退 | 全部 | 否 |
| **批量文件夹** | 网页版一次可添加多个文件夹统一处理 | 网页版 | 否 |
| **环境自检** | 启动时提示缺什么、怎么装（`doctor`）| 全部 | 否 |
| **热更新** | 代码一变，页面自动刷新 / 一键重启服务；上游有新版会提示 | 网页版 | 否 |

---

## 依赖说明

**全部是 Python 包 —— 不需要安装任何系统程序。**

```bash
pip install -r requirements.txt
```

| 功能 | 需要什么 | 怎么装 |
|---|---|---|
| 重命名（`rename` 模式）| **什么都不用** | — |
| 读 Word / Excel / PPT | python-docx / openpyxl / python-pptx | `pip install` |
| 读 PDF | pypdf（纯 Python）| `pip install` |
| **图片 OCR**（发票、扫描件）| **rapidocr-onnxruntime**（纯 Python 中文 OCR）| `pip install` |

`start.sh` / `start.bat` 会自动把上面这些装齐，**装完就直接能用，不用再折腾别的**。

> **为什么不用 tesseract 了**：tesseract 是系统程序，pip 装不了、也打不进包，是「别人下载用不了」的主要原因。
> 改用 rapidocr（纯 Python + onnxruntime，模型内置）后，实测中文识别 **14/14 全对**，而 tesseract 只有 8/14（连「增值税」都认成「雹值税」），速度还一样快。
>
> **可选增强**：系统里如果装了 `tesseract` / `poppler`，工具会在 rapidocr/pypdf 不可用时自动回退使用 —— 但不装也完全不影响。

启动时和网页右上角都会自检，缺什么直接告诉你装什么。

## 可选：打包成独立程序

不想让使用者装 Python 的话，在**对应系统上**运行打包脚本，生成单文件可执行程序：

| 系统 | 脚本 | 产物 | 实测体积 |
|---|---|---|---|
| Windows | `build\build_windows.bat` | `dist\filekit.exe` | — |
| macOS | `bash build/build_macos.sh` | `dist/filekit` | — |
| Linux | `bash build/build_linux.sh` | `dist/filekit` | **49 MB** |

产物含全部 Python 依赖，直接发给别人，双击运行 → 自动开浏览器。

> ✅ 因为依赖全是纯 Python 包，打包产物**自带 OCR 能力**，使用者什么都不用装。
>
> ⚠️ PyInstaller **不能交叉编译**：Windows 的 exe 必须在 Windows 上打。
> 另：图片 OCR 依赖的 tesseract 是系统程序，**打不进包**，仍需使用者自行安装。

---

## 目录结构

```
Smart-Toolkit/
├── README.md                 ← 本文件
├── start.sh / start.bat      ← 一键启动（自动装依赖 + 起服务）
├── server.py                 ← 网页服务（标准库实现，零 Web 框架）
├── web/index.html            ← 网页界面（无外部依赖）
├── requirements.txt          ← Python 依赖清单
├── tools/filekit/
│   ├── filekit.py            ← 核心引擎（命令行也可直接用）
│   └── README.md             ← 命令行版详细文档
└── build/                    ← 可选：三平台打包脚本
    ├── build_windows.bat
    ├── build_macos.sh
    └── build_linux.sh
```

---

## 安全设计

| 机制 | 说明 |
|---|---|
| **默认预览** | 不点"确认执行"，一个文件都不动 |
| **日志留痕** | 每次执行写 `_filekit_log_YYYYmmdd_HHMMSS.json` |
| **一键回退** | 网页版按文件夹选记录回退；命令行按日志文件回退 |
| **不覆盖** | 重名自动加 `_02 _03` |
| **不改内容** | 只动文件名，不碰文件内容 |
| **本地运行** | 网页版只监听 `127.0.0.1`，文件不出本机 |

---

## 许可

[MIT](LICENSE) —— 自由使用、修改、分发。
