# Smart-Toolkit

> 一堆解决具体小问题的实用工具。
> 每个工具都遵循三条原则：**默认安全、出问题能回滚、说人话的文档。**

---

## 工具列表

| 工具 | 一句话说明 | 依赖 | 文档 |
|---|---|---|---|
| **[filekit](tools/filekit/)** | 文件整理工具箱：**规范文件名 + 读内容自动归类 + 一键回滚** | 部分功能需要（见下）| [README](tools/filekit/README.md) |

> 持续更新中。工具之间彼此独立，复制走就能用。

---

## filekit 功能一览

| 功能 | 说明 | 可用模式 | 需要依赖 |
|---|---|---|---|
| **文件名清理** | 去空格、非法字符、括号；去"最终版/副本/final"等废话词 | 全部 | 否 |
| **类型前缀** | 按扩展名自动加 `IMG`/`DOC`/`XLS`/`PPT`/`PDF`/`AUD`/`VID`/`ZIP` | 全部 | 否 |
| **内容归类** | 读文档正文，判断属于 **38 类**中的哪一类 | classify / auto | 是 |
| **图片 OCR** | 图片中文 OCR 后再判断类别（发票、合同扫描件）| classify / auto | 是 |
| **时间戳入名** | 文件名末尾加 `YYMMDDHHMM`（精确到分钟）| 全部 | 否 |
| **版本号保留** | 原文件名里的 `v1`/`v2` 原样保留 | 全部 | 否 |
| **数字补零** | `头像1` → `头像01`（排序正确）| 全部 | 否 |
| **三级防冲突** | 时间戳 → 序号 → 疑似同名报告 | 全部 | 否 |
| **疑似同名报告** | 发现同一文档多份时，列清单由你决定 | 全部 | 否 |
| **预览模式** | 默认不改任何文件，只看会改成什么 | 全部 | 否 |
| **日志留痕** | 每次执行写 JSON 日志（谁改成了什么）| 全部 | 否 |
| **一键回滚** | 按日志逆序还原到改动前 | rollback | 否 |
| **智能模式** | 能读到内容就归类，读不到就只按文件名 | auto | 视情况 |

**三种模式**：

| 场景 | 用哪个 |
|---|---|
| 文件名本来就有信息（`采购合同 v1.docx`）| `rename` |
| 文件名没信息（`文档1.docx`、`未命名.docx`）| `classify` |
| 文件混着，有的有名有的没名 | **`auto`** |

---

## 设计原则

1. **默认安全** —— 破坏性操作默认是"预览"，加 `--apply` 才真执行
2. **可回滚** —— 每次改动都写日志，一条命令还原
3. **不删文件** —— 只重命名，从不删除、从不覆盖（重名自动加序号）
4. **中文友好** —— 完整支持 UTF-8，中文文件名与内容都能处理
5. **说人话** —— 报错要能看懂，文档要有例子

---

## 快速使用

```bash
git clone https://github.com/xyg165/Smart-Toolkit.git
cd Smart-Toolkit

# 预览（什么都不改）
python tools/filekit/filekit.py auto --dir "/你的文件夹" --verbose

# 执行
python tools/filekit/filekit.py auto --dir "/你的文件夹" --apply

# 回滚
python tools/filekit/filekit.py rollback "/你的文件夹/_filekit_log_xxx.json"
```

### 命名结果

```
DOC_合同_采购合同_v1_2609151030.docx
 ↑    ↑      ↑     ↑      ↑
类型  分类   原名   版本  YYMMDDHHMM（26年09月15日 10:30）
```

---

## 依赖

**零依赖部分**（`rename` 模式 + 所有安全功能）：只用 Python 标准库。

**内容识别部分**（`classify` / `auto`）：

```bash
pip install python-docx openpyxl python-pptx pypdf
apt install poppler-utils tesseract-ocr tesseract-ocr-chi-sim    # Debian/Ubuntu
dnf install poppler-utils tesseract tesseract-langpack-chi_sim   # RHEL/CentOS
```

支持格式：**PDF · Word · Excel · PPT · txt/md · 图片（中文 OCR）**

---

## 内置分类（38 类）

| 大类 | 分类 |
|---|---|
| 商务经营 | 合同 · 保密协议 · 报价单 · 招投标 · 采购订单 · 发票 · 付款凭证 · 客户资料 · 销售合同 |
| 项目产品 | 需求文档 · 方案 · 项目计划 · 测试报告 · 验收文档 · 项目周报 · 产品文档 |
| 技术研发 | 技术文档 · 设计文档 · 说明书 · 图纸 · 知识产权 · 技术标准 |
| 行政人事 | 规章制度 · 通知公告 · 会议纪要 · 简历 · 人事档案 · 培训材料 · 工作总结 |
| 财务 | 财务报表 · 预算 · 报销单 |
| 内容运营 | 内容脚本 · 运营数据 · 素材清单 |
| 法律与其他 | 法律文书 · 资质证书 · 分析报告 |

---

## 环境要求

- **Python 3.8+**
- 详见各工具 README

---

## 反馈 / 贡献

1. 提 Issue 描述"你想解决的小问题"
2. 提 PR（建议每个工具一个目录，含脚本 + README）

---

## 许可

[MIT](LICENSE) —— 自由使用、修改、分发。
