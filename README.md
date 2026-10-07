# Smart-Toolkit

> 一堆解决具体小问题的实用工具。
> 每个工具都遵循三条原则：**默认安全、出问题能回滚、说人话的文档。**

---

## 目录

- [filekit 是什么](#filekit-是什么)
- [方式一：网页版（推荐，无需命令行）](#方式一网页版推荐无需命令行)
- [方式二：命令行版](#方式二命令行版)
- [功能一览](#功能一览)
- [三平台安装](#三平台安装)
- [打独立可执行程序（分发给别人）](#打独立可执行程序分发给别人)
- [目录结构](#目录结构)

---

## filekit 是什么

**filekit** 帮你整理文件：

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

## 方式一：网页版（推荐，无需命令行）

**在浏览器里点几下就完成**：选文件夹 → 预览 → 确认 → 完成；回退同理。

```bash
# Linux / macOS
bash install.sh

# Windows：双击 install.bat
```

启动后**浏览器自动打开**，页面长这样：

| 区域 | 做什么 |
|---|---|
| **整理文件** | 添加文件夹（可加多个 = 批量）→ 选处理方式 → 预览 → 确认执行 |
| **回退** | 选择文件夹 → 列出历史记录 → 点「回退」还原 |

**特点**：
- 全程**本地运行**（监听 `127.0.0.1`，文件不出本机）
- 支持**单个文件夹**和**批量多个文件夹**
- 预览时能看到「原文件名 → 新文件名 + 识别类别」
- 执行前二次确认；执行后可随时回退
- 零 Web 框架依赖（只用 Python 标准库）

---

## 方式二：命令行版

不想开浏览器的话，命令行一样能用：

```bash
python tools/filekit/filekit.py auto --dir "./我的文件夹" --verbose   # 预览
python tools/filekit/filekit.py auto --dir "./我的文件夹" --apply     # 执行
python tools/filekit/filekit.py rollback "./文件夹/_filekit_log_xxx.json"  # 回退
python tools/filekit/filekit.py doctor                               # 检查环境
```

三种模式：
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
| **图片 OCR** | 图片中文 OCR 后再判断类别（发票、合同扫描件）| classify / auto | 是（**系统级**）|
| **时间戳入名** | 文件名末尾加 `YYMMDDHHMM`（精确到分钟）| 全部 | 否 |
| **版本号保留** | 原文件名里的 `v1`/`v2` 原样保留 | 全部 | 否 |
| **数字补零** | `头像1` → `头像01`（排序正确）| 全部 | 否 |
| **三级防冲突** | 时间戳 → 序号 → 疑似同名报告 | 全部 | 否 |
| **疑似同名报告** | 发现同一文档多份时，列清单由你决定 | 全部 | 否 |
| **预览模式** | 默认不改任何文件，只看会改成什么 | 全部 | 否 |
| **日志留痕** | 每次执行写 JSON 日志（谁改成了什么）| 全部 | 否 |
| **一键回退** | 按日志逆序还原到改动前（网页版可按文件夹回退）| 全部 | 否 |
| **批量文件夹** | 网页版一次可添加多个文件夹统一处理 | 网页版 | 否 |
| **环境自检** | `doctor` 检查依赖，缺什么提示装什么 | 全部 | 否 |

---

## 三平台安装

### Linux（Ubuntu / Debian）
```bash
bash install.sh
# 如提示缺系统依赖：
sudo apt install poppler-utils tesseract-ocr tesseract-ocr-chi-sim
```

### Linux（CentOS / RHEL / openEuler）
```bash
bash install.sh
# 如提示缺系统依赖：
sudo dnf install poppler-utils tesseract tesseract-langpack-chi_sim
```

### macOS
```bash
bash install.sh
# 如提示缺系统依赖：
brew install poppler tesseract tesseract-lang
```

### Windows
```
双击 install.bat
# PDF/图片 OCR 需要额外装 Tesseract（可选）：
#   https://github.com/UB-Mannheim/tesseract/wiki
```

> **只用重命名功能的话，什么都不用装**（`rename` 模式零依赖）。
> 缺依赖不会崩溃 —— 对应格式标「未分类」，其它格式照常。

---

## 打独立可执行程序（分发给别人）

不想让别人装 Python？在**对应系统上**运行打包脚本，生成单文件可执行程序（含全部 Python 依赖）：

| 系统 | 脚本 | 产物 |
|---|---|---|
| Windows | `build\build_windows.bat` | `dist\filekit.exe` |
| macOS | `bash build/build_macos.sh` | `dist/filekit` |
| Linux | `bash build/build_linux.sh` | `dist/filekit` |

产物可直接发给别人，**双击运行** → 浏览器自动打开。

> ⚠️ 注意：PyInstaller 不能交叉编译 —— Windows 的 exe 必须在 Windows 上打，macOS 的必须在 macOS 上打。
> 所以三个脚本各自在本平台运行。

---

## 目录结构

```
Smart-Toolkit/
├── README.md                 ← 本文件
├── requirements.txt          ← Python 依赖
├── install.sh                ← Linux/macOS 一键安装
├── install.bat               ← Windows 一键安装
├── server.py                 ← 网页版服务（本地 HTTP，标准库）
├── web/
│   └── index.html            ← 网页界面（无外部依赖）
├── tools/filekit/
│   ├── filekit.py            ← 核心引擎（命令行也可直接用）
│   └── README.md             ← 命令行版详细文档
└── build/
    ├── build_windows.bat     ← Windows 打包
    ├── build_macos.sh        ← macOS 打包
    └── build_linux.sh        ← Linux 打包
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
| **本地运行** | 网页版只监听 127.0.0.1，文件不出本机 |

---

## 许可

[MIT](LICENSE) —— 自由使用、修改、分发。
