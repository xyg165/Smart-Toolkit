@echo off
chcp 65001 >nul
REM ============================================================
REM   filekit 一键启动（Windows）
REM   用法：双击本文件，或在 cmd 中运行 install.bat
REM ============================================================
cd /d "%~dp0"

echo ==============================================
echo   filekit 启动脚本（Windows）
echo ==============================================

REM ---------- 1. 检测 Python ----------
set PY=
where python >nul 2>nul && set PY=python
if "%PY%"=="" ( where py >nul 2>nul && set PY=py )
if "%PY%"=="" (
  echo [X] 未找到 Python，请先安装 Python 3.8+
  echo     下载地址：https://www.python.org/downloads/
  echo     安装时请勾选 "Add Python to PATH"
  pause
  exit /b 1
)
echo [OK] Python 已找到
%PY% --version

REM ---------- 2. 安装 Python 依赖 ----------
echo.
echo [1/2] 安装 Python 依赖...
if exist vendor (
  %PY% -m pip install --no-index --find-links=vendor -r requirements.txt
  if errorlevel 1 %PY% -m pip install -r requirements.txt
) else (
  %PY% -m pip install -r requirements.txt
)
if errorlevel 1 (
  echo.
  echo [!] 依赖安装失败，试试国内镜像：
  echo     %PY% -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
  pause
)

echo [OK] Python 依赖完成

REM ---------- 3. 系统依赖提示 ----------
echo.
echo [2/2] 说明：无需安装任何系统程序。
echo     图片 OCR 用 rapidocr、PDF 用 pypdf，都已随上面的 pip 依赖装好。
echo     （若系统里有 tesseract/poppler，会自动作为回退使用。）

REM ---------- 4. 启动 ----------
echo.
echo 启动服务（浏览器会自动打开）...
echo 关闭本窗口即停止服务
echo.
%PY% server.py
pause
