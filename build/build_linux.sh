#!/usr/bin/env bash
# ============================================================
#  filekit 打包脚本 —— Linux
#  产物：dist/filekit（单文件可执行程序，含全部 Python 依赖）
#  用法：bash build/build_linux.sh
# ============================================================
set -e
cd "$(dirname "$0")/.."

echo "=== filekit 打包（Linux）==="

# 1. 装 PyInstaller
command -v pyinstaller >/dev/null 2>&1 || {
  echo "[1/3] 安装 PyInstaller…"
  python3 -m pip install pyinstaller
}

# 2. 打包
echo "[2/3] 打包…"
PROJ="$(pwd)"
rm -rf build_tmp dist
python3 -m PyInstaller \
  --onefile \
  --name filekit \
  --collect-all docx \
  --collect-all openpyxl \
  --collect-all pptx \
  --collect-all pypdf \
  --collect-all rapidocr_onnxruntime \
  --add-data "$PROJ/web:web" \
  --add-data "$PROJ/tools/filekit/filekit.py:." \
  --add-data "$PROJ/requirements.txt:." \
  --paths "$PROJ/tools/filekit" \
  --workpath build_tmp \
  --specpath build_tmp \
  --clean --noconfirm \
  server.py

# 3. 结果
echo
echo "[3/3] 完成 ✔"
echo "  产物：$(pwd)/dist/filekit"
ls -lh dist/filekit
echo
echo "分发方式：把 dist/filekit 单独发给别人，双击/命令行运行即可"
echo "运行：./dist/filekit"
