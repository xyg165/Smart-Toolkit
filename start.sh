#!/usr/bin/env bash
# ============================================================
#  filekit 一键启动（Linux / macOS）
#  用法：
#     bash install.sh            # 安装依赖并启动
#     bash install.sh --deps     # 只装依赖，不启动
# ============================================================
set -e
cd "$(dirname "$0")"

echo "=============================================="
echo "  filekit 启动脚本（Linux / macOS）"
echo "=============================================="

# ---------- 1. 检测 Python ----------
PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1; then
    v=$("$c" -c 'import sys;print(sys.version_info[0]*100+sys.version_info[1])' 2>/dev/null || echo 0)
    if [ "$v" -ge 308 ]; then PY="$c"; break; fi
  fi
done
if [ -z "$PY" ]; then
  echo "❌ 未找到 Python 3.8+，请先安装："
  echo "   Ubuntu/Debian:  sudo apt install python3 python3-pip"
  echo "   CentOS/RHEL:    sudo dnf install python3 python3-pip"
  echo "   macOS:          brew install python3"
  exit 1
fi
echo "✅ Python: $($PY --version)"

# ---------- 2. 安装 Python 依赖 ----------
echo
echo "[1/3] 安装 Python 依赖…"
if [ -d vendor ] && ls vendor/*.whl >/dev/null 2>&1; then
  echo "  发现离线安装包 vendor/，使用离线安装"
  "$PY" -m pip install --no-index --find-links=vendor -r requirements.txt 2>/dev/null \
    || "$PY" -m pip install -r requirements.txt
else
  "$PY" -m pip install -r requirements.txt \
    || "$PY" -m pip install --user -r requirements.txt
fi
echo "✅ Python 依赖完成"

# ---------- 3. 系统级依赖（可选，用于 PDF / 图片 OCR）----------
echo
echo "[2/3] 检查系统级依赖（可选，用于 PDF/图片识别）…"
MISSING=""
command -v pdftotext >/dev/null 2>&1 || MISSING="$MISSING pdftotext"
command -v tesseract >/dev/null 2>&1 || MISSING="$MISSING tesseract"

if [ -n "$MISSING" ]; then
  echo "⚠️  缺少：$MISSING"
  if command -v apt >/dev/null 2>&1; then
    echo "   安装命令：sudo apt install poppler-utils tesseract-ocr tesseract-ocr-chi-sim"
  elif command -v dnf >/dev/null 2>&1; then
    echo "   安装命令：sudo dnf install poppler-utils tesseract tesseract-langpack-chi_sim"
  elif command -v brew >/dev/null 2>&1; then
    echo "   安装命令：brew install poppler tesseract tesseract-lang"
  fi
  echo "   （不装也能用：只是 PDF/图片会标「未分类」，其余格式正常）"
else
  echo "✅ 系统依赖齐全"
fi

# ---------- 4. 启动 ----------
echo
if [ "$1" = "--deps" ]; then
  echo "[3/3] 已跳过启动（--deps）"
  echo "以后启动：python3 server.py"
  exit 0
fi

echo "[3/3] 启动服务（浏览器会自动打开）…"
echo "      按 Ctrl+C 停止"
echo
exec "$PY" server.py
