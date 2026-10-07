# Smart-Toolkit

> 一堆解决具体小问题的实用工具。
> 每个工具都遵循三条原则：**零依赖、默认安全、出问题能回滚。**

---

## 工具列表

| 工具 | 作用 | 语言 | 文档 |
|---|---|---|---|
| **rename_kit** | 文件批量重命名（预览 → 执行 → 可回滚）| Python 3.7+ | [查看](tools/rename_kit/README.md) |

> 持续更新中。每个工具都是独立的单文件脚本，复制走就能用。

---

## 设计原则

做每个工具时，都遵守这四条：

1. **零依赖** —— 优先用标准库，不用装任何包
2. **默认安全** —— 破坏性操作默认是"预览"，加参数才真执行
3. **可回滚** —— 每一次改动都留日志，能一键还原
4. **中文友好** —— 完整支持 UTF-8，不做英文中心主义

---

## 快速使用

```bash
# 克隆
git clone git@github.com:xyg165/Smart-Toolkit.git
cd Smart-Toolkit

# 用某个工具（以 rename_kit 为例）
python tools/rename_kit/rename_kit.py --dir "/你的文件夹"          # 预览
python tools/rename_kit/rename_kit.py --dir "/你的文件夹" --apply  # 执行
```

每个工具的具体用法见各自目录下的 README。

---

## 工具：rename_kit

**解决什么问题**：文件名乱——带空格、中英混杂、"最终版最终版2"、`头像1/头像10` 排序错乱。

```bash
# 预览（不改任何文件）
python rename_kit.py --dir "./素材"

# 执行
python rename_kit.py --dir "./素材" --pad --apply

# 回滚
python rename_kit.py --rollback "./素材/_rename_log_xxx.json"
```

**效果**：
```
Logo image 头像 用于自媒体的头像图片.png  →  IMG_Logo_image_头像_用于自媒体的头像图片.png
双鱼封面 final 版.png                   →  IMG_双鱼封面.png
内容排期表（2026Q4）.xlsx                →  XLS_内容排期表2026Q4.xlsx
头像1.png / 头像10.png / 头像2.png       →  IMG_头像01.png / IMG_头像10.png / IMG_头像02.png
```

详见 → [tools/rename_kit/README.md](tools/rename_kit/README.md)

---

## 环境要求

- Python 3.7+（各工具若有额外要求，会在自己的 README 里说明）

---

## 贡献 / 反馈

有想加的工具有两种方式：
1. 提 Issue 描述"你想解决的小问题"
2. 直接提 PR（建议每个工具一个目录，含脚本 + README）

---

## 许可

[MIT](LICENSE) —— 自由使用、修改、分发。
