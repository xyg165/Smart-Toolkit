#!/usr/bin/env python3
"""
文件批量重命名工具 rename_kit
================================
规则：[类型前缀]_[清理后的名字]_[版本/日期].[后缀]

三条安全设计：
  1. 默认只预览（dry-run），加 --apply 才真改
  2. 改之前检查冲突，重名自动加序号
  3. 每次执行都写日志，一条命令即可全部回滚

用法：
  python3 rename_kit.py --dir /path/to/folder              # 预览
  python3 rename_kit.py --dir /path/to/folder --apply      # 执行
  python3 rename_kit.py --rollback /path/to/folder/_rename_log_xxx.json   # 回滚
"""
import argparse, os, re, json, sys, datetime
from pathlib import Path

# 类型前缀映射
TYPE_PREFIX = {
    '.jpg': 'IMG', '.jpeg': 'IMG', '.png': 'IMG', '.gif': 'IMG', '.webp': 'IMG',
    '.bmp': 'IMG', '.svg': 'IMG', '.ico': 'IMG', '.heic': 'IMG', '.tif': 'IMG',
    '.doc': 'DOC', '.docx': 'DOC', '.md': 'DOC', '.txt': 'DOC', '.rtf': 'DOC', '.odt': 'DOC',
    '.xls': 'XLS', '.xlsx': 'XLS', '.csv': 'XLS', '.ods': 'XLS',
    '.ppt': 'PPT', '.pptx': 'PPT', '.key': 'PPT', '.odp': 'PPT',
    '.pdf': 'PDF',
    '.mp3': 'AUD', '.wav': 'AUD', '.m4a': 'AUD', '.flac': 'AUD', '.aac': 'AUD',
    '.mp4': 'VID', '.mov': 'VID', '.avi': 'VID', '.mkv': 'VID', '.webm': 'VID',
    '.zip': 'ZIP', '.rar': 'ZIP', '.7z': 'ZIP', '.tar': 'ZIP', '.gz': 'ZIP',
    '.psd': 'IMG', '.ai': 'IMG', '.sketch': 'IMG',
}
PREFIX_RE = re.compile(r'^(IMG|DOC|XLS|PPT|PDF|AUD|VID|ZIP|FILE)[_\-]', re.I)
# 版本号统一：v1 / V1 / 1 / 第一版 → v01 / v02...
VERSION_RE = re.compile(r'(?:^|[_\-])(?:v|ver|版本)?\s*(\d+)\s*(?:版)?(?=[_\-]|$)', re.I)
# 要干掉的"废话"后缀
JUNK_RE = re.compile(r'(最终版|最新版|修改版|的副本|副本|copy|final|new|new\s*\d*)\s*', re.I)


def clean_stem(stem: str, sep: str = '_') -> str:
    """清理文件名主体：空格转分隔符、去特殊字符、去废话词"""
    s = stem.strip()
    s = JUNK_RE.sub('', s)                       # 去掉"最终版/副本/final"等
    s = re.sub(r'[\s\u3000]+', sep, s)           # 空格（含全角）→ 分隔符
    s = re.sub(r'[\\/:*?"<>|\u0000-\u001f]', '', s)  # 非法字符
    s = re.sub(r'[()（）\[\]【】]', '', s)      # 去括号（易造成混乱）
    s = re.sub(re.escape(sep) + r'{2,}', sep, s)  # 连续分隔符合并
    s = re.sub(r'(?:^|(?<=[_\-]))版(?=[_\-]|$)', '', s)  # 去掉孤立的"版"字
    s = re.sub(re.escape(sep) + r'{2,}', sep, s)
    s = re.sub(r'-{2,}', '-', s)
    s = s.strip(sep + '-. ')
    return s


def build_plan(directory: str, sep: str, add_date: bool, lower: bool, pad: bool = False):
    """生成重命名计划 [(旧名, 新名), ...]"""
    d = Path(directory)
    if not d.is_dir():
        print(f'错误：目录不存在 {directory}')
        sys.exit(1)

    items = [p for p in sorted(d.iterdir())
             if p.is_file() and not p.name.startswith(('.', '_rename_log_'))]
    plan, seen = [], {}
    for p in items:
        ext = p.suffix
        prefix = TYPE_PREFIX.get(ext.lower(), 'FILE')
        stem = p.stem
        has_prefix = bool(PREFIX_RE.match(stem))
        clean = clean_stem(stem, sep)
        if not clean:
            clean = 'unnamed'
        new_stem = clean if has_prefix else f'{prefix}{sep}{clean}'
        if pad:
            # 只补零「非字母后」的末尾数字（避免把 2026Q4 变成 2026Q04）
            new_stem = re.sub(r'(?<![A-Za-z])(\d+)$', lambda m: m.group(1).zfill(2), new_stem)
        if lower:
            new_stem = new_stem.lower()
        if add_date:
            mt = datetime.datetime.fromtimestamp(p.stat().st_mtime).strftime('%Y%m%d')
            if mt not in new_stem:
                new_stem = f'{new_stem}{sep}{mt}'
        new_name = f'{new_stem}{ext}'

        # 冲突处理（计划内部 + 与现有文件）
        key = new_name.lower()
        if new_name != p.name and (d / new_name).exists():
            base, e = os.path.splitext(new_name)
            n = 1
            while (d / f'{base}_{n:02d}{e}').exists():
                n += 1
            new_name = f'{base}_{n:02d}{e}'
            key = new_name.lower()
        while key in seen:
            seen[key] += 1
            base, e = os.path.splitext(new_name)
            new_name = f'{base}_{seen[key]:02d}{e}'
            key = new_name.lower()
        seen[key] = 1

        if new_name != p.name:
            plan.append((p.name, new_name))
    return plan


def main():
    ap = argparse.ArgumentParser(description='文件批量重命名（安全版）')
    ap.add_argument('--dir', help='目标目录')
    ap.add_argument('--apply', action='store_true', help='真正执行（默认只预览）')
    ap.add_argument('--sep', default='_', help='分隔符，默认下划线 _')
    ap.add_argument('--date', action='store_true', help='在末尾加修改日期 YYYYMMDD')
    ap.add_argument('--lower', action='store_true', help='文件名转小写')
    ap.add_argument('--pad', action='store_true', help='末尾数字补零（头像1 → 头像01，便于排序）')
    ap.add_argument('--rollback', help='按日志文件回滚')
    args = ap.parse_args()

    # ---------- 回滚 ----------
    if args.rollback:
        with open(args.rollback, encoding='utf-8') as f:
            log = json.load(f)
        d = Path(log['directory'])
        n = 0
        for item in log['renames']:
            cur, old = d / item['new'], d / item['old']
            if cur.exists():
                if old.exists():
                    print(f'  ⚠️ 跳过（目标已存在）: {item["old"]}')
                    continue
                cur.rename(old)
                n += 1
        print(f'✅ 已回滚 {n} 个文件')
        return

    if not args.dir:
        ap.error('需要 --dir（或用 --rollback）')

    plan = build_plan(args.dir, args.sep, args.date, args.lower, args.pad)
    if not plan:
        print('没有需要改名的文件（已符合规则，或目录为空）')
        return

    print(f'\n共 {len(plan)} 个文件待重命名：\n')
    print(f'{"原文件名":<52} →  新文件名')
    print('-' * 110)
    for old, new in plan:
        print(f'{old[:50]:<52} →  {new}')

    if not args.apply:
        print(f'\n👀 这是预览。确认无误后加 --apply 执行：')
        print(f'   python3 {sys.argv[0]} --dir "{args.dir}" --apply')
        return

    d = Path(args.dir)
    done = []
    for old, new in plan:
        (d / old).rename(d / new)
        done.append({'old': old, 'new': new})

    log_path = d / f'_rename_log_{datetime.datetime.now():%Y%m%d_%H%M%S}.json'
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump({'directory': str(d.resolve()), 'time': datetime.datetime.now().isoformat(timespec='seconds'),
                   'renames': done}, f, ensure_ascii=False, indent=2)

    print(f'\n✅ 完成：{len(done)} 个文件已重命名')
    print(f'📄 日志：{log_path}')
    print(f'↩️  如需回滚：python3 {sys.argv[0]} --rollback "{log_path}"')


if __name__ == '__main__':
    main()
