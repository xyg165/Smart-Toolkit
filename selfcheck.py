#!/usr/bin/env python3
"""
selfcheck.py —— 提交前自检：找出「调用了但没定义」的函数

来历：有一次插入新代码时误删了 api_browse 函数，
      而我的测试只覆盖了部分接口，没测到页面「添加文件夹」按钮，
      结果用户那边点一下才报 NameError。
      所以加这个检查：静态扫一遍，把「调用但未定义」的名字找出来。

用法：
    python selfcheck.py            # 在仓库根目录运行
"""
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
problems = []


def check_python_defs(path: Path):
    """检查 Python 文件里被调用但未定义的模块级函数"""
    try:
        src = path.read_text(encoding='utf-8')
        tree = ast.parse(src)
    except Exception as e:
        problems.append(f'{path.name}: 语法错误 —— {e}')
        return

    defined = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    # 模块级 import 进来的名字
    imported = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                imported.add((a.asname or a.name).split('.')[0])
        elif isinstance(n, ast.ImportFrom):
            for a in n.names:
                imported.add(a.asname or a.name)
    # 赋值过的名字（含全局变量）
    assigned = {t.id for n in ast.walk(tree) if isinstance(n, ast.Assign)
                for t in ast.walk(n) if isinstance(t, ast.Name)}

    called = set(re.findall(r'(?<![\w.])(api_\w+|_\w+)\(', src))
    missing = called - defined - imported - assigned
    # 过滤掉明显是内置/外部库的
    missing = {m for m in missing if not m.startswith(('__', 'int', 'str', 'dict', 'list'))}
    if missing:
        problems.append(f'{path.name}: 调用但未定义 → {sorted(missing)}')


def check_frontend_api(path: Path):
    """检查前端 fetch 的 API 路径，后端是否都提供"""
    try:
        html = path.read_text(encoding='utf-8')
    except Exception:
        return
    called = set(re.findall(r"fetch\('(/api/[\w/]+)", html))
    srv = (ROOT / 'server.py').read_text(encoding='utf-8')
    routes = set(re.findall(r"u\.path == '(/api/[\w/]+)'", srv))
    missing = called - routes
    if missing:
        problems.append(f'{path.name}: 前端调用了后端没有的接口 → {sorted(missing)}')


print('=== filekit 自检 ===')
print()
for f in sorted(ROOT.glob('*.py')):
    check_python_defs(f)
    print(f'  检查 {f.name}')

for f in [ROOT / 'web' / 'index.html']:
    if f.exists():
        check_frontend_api(f)
        print(f'  检查 web/index.html')

print()
if problems:
    print('❌ 发现问题：')
    for p in problems:
        print('  -', p)
    sys.exit(1)
print('✅ 自检通过：没有未定义的调用，前后端接口对得上')
