# Smart-Toolkit

> 一堆解决具体小问题的实用工具。
> 每个工具都遵循三条原则：**默认安全、出问题能回滚、说人话的文档。**

---

## 工具列表

| 工具 | 作用 | 依赖 | 文档 |
|---|---|---|---|
| **[rename_kit](tools/rename_kit/)** | 文件批量重命名：按文件名规范（清理 + 类型前缀 + 时间戳）| **零依赖**（纯标准库）| [README](tools/rename_kit/README.md) |
| **[classify_kit](tools/classify_kit/)** | 读文档**内容**自动归类（38 类）并写进文件名 | 见下方依赖 | [README](tools/classify_kit/README.md) |

两个工具命令风格一致：**默认预览 → 加 `--apply` 执行 → 出问题一键回滚**。

---

## 设计原则

1. **默认安全** —— 破坏性操作默认是"预览"，加参数才真执行
2. **可回滚** —— 每次改动都写日志，一条命令还原
3. **不删文件** —— 只重命名，从不删除、从不覆盖（重名自动加序号）
4. **中文友好** —— 完整支持 UTF-8，中文文件名与内容都能处理
5. **说人话** —— 报错要能看懂，文档要有例子

---

## 快速使用

```bash
git clone https://github.com/xyg165/Smart-Toolkit.git
cd Smart-Toolkit

# 工具一：只按文件名规范（无需装依赖）
python tools/rename_kit/rename_kit.py --dir "/你的文件夹"          # 预览
python tools/rename_kit/rename_kit.py --dir "/你的文件夹" --apply  # 执行

# 工具二：读内容自动归类
python tools/classify_kit/classify_kit.py --dir "/你的文档" --verbose  # 预览
python tools/classify_kit/classify_kit.py --dir "/你的文档" --apply    # 执行
```

统一命名结果：
```
DOC_合同_采购合同_v1_2609151030.docx
  ↑    ↑      ↑      ↑      ↑
 类型  分类   原名   版本  YYMMDDHHMM（26年09月15日 10:30）
```

---

## 工具一：rename_kit

**解决什么**：文件名乱 —— 带空格、中英混杂、"最终版最终版2"、`头像1/头像10` 排序错乱。

```bash
python rename_kit.py --dir "./素材" --pad --apply
```

**效果**：
```
Logo image 头像 用于自媒体的头像图片.png  →  IMG_Logo_image_头像_用于自媒体的头像图片.png
双鱼封面 final 版.png                   →  IMG_双鱼封面.png
头像1.png / 头像10.png / 头像2.png       →  IMG_头像01.png / IMG_头像10.png / IMG_头像02.png
```

**零依赖** —— 复制走就能跑。

---

## 工具二：classify_kit

**解决什么**：文件名没信息（`文档1.docx`、`未命名.docx`、`扫描件001.png`），但内容能说明它是什么。

```bash
python classify_kit.py --dir "./历史文件" --verbose
```

**效果**：
```
文档1.docx    →  DOC_合同_文档1_2610070915.docx
工作簿1.xlsx  →  XLS_报价单_工作簿1_2610070915.xlsx
扫描件001.png →  IMG_发票_扫描件001_2610070915.png   ← OCR 识别
随便写写.docx  →  DOC_未分类_随便写写_2610070915.docx  ← 判不准就不硬猜
```

**内置 38 个分类**：合同 · 发票 · 报价单 · 招投标 · 需求文档 · 方案 · 测试报告 · 验收文档 · 技术文档 · 设计文档 · 说明书 · 图纸 · 知识产权 · 规章制度 · 通知公告 · 会议纪要 · 简历 · 人事档案 · 培训材料 · 财务报表 · 预算 · 报销单 · 内容脚本 · 运营数据 · 法律文书 · 资质证书 · 分析报告 ……

### 附加依赖

```bash
pip install python-docx openpyxl python-pptx pypdf
# PDF 提取 + 图片 OCR
apt install poppler-utils tesseract-ocr tesseract-ocr-chi-sim      # Debian/Ubuntu
dnf install poppler-utils tesseract tesseract-langpack-chi_sim     # RHEL/CentOS
```

支持格式：**PDF · Word · Excel · PPT · txt/md · 图片（中文 OCR）**

---

## 共同的安全机制

| 机制 | 说明 |
|---|---|
| **默认预览** | 不加 `--apply`，一个文件都不动 |
| **日志留痕** | 每次执行写 `_*_log_YYYYmmdd_HHMMSS.json` |
| **一键回滚** | `--rollback <日志文件>` 按日志还原 |
| **不覆盖** | 重名自动加 `_02 _03` |
| **疑似同名报告** | 发现同一文档多份时，列出清单让你决定 |

---

## 环境要求

- **Python 3.8+**
- `rename_kit`：无需第三方依赖
- `classify_kit`：见上方「附加依赖」

---

## 反馈 / 贡献

1. 提 Issue 描述"你想解决的小问题"
2. 提 PR（建议每个工具一个目录，含脚本 + README）

---

## 许可

[MIT](LICENSE) —— 自由使用、修改、分发。
