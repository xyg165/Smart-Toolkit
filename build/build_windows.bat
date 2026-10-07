@echo off
chcp 65001 >nul
REM ============================================================
REM  filekit 打包脚本 —— Windows
REM  产物：dist\filekit.exe（单文件可执行程序，含全部 Python 依赖）
REM  用法：双击本文件，或在 cmd 中运行 build\build_windows.bat
REM ============================================================
cd /d "%~dp0.."

echo === filekit 打包（Windows）===

REM 1. 装 PyInstaller
where pyinstaller >nul 2>nul
if errorlevel 1 (
  echo [1/3] 安装 PyInstaller...
  python -m pip install pyinstaller
  if errorlevel 1 (
    echo [X] PyInstaller 安装失败
    pause
    exit /b 1
  )
)

REM 2. 打包
echo [2/3] 打包...
if exist build_tmp rmdir /s /q build_tmp
if exist dist rmdir /s /q dist
python -m PyInstaller ^
  --onefile ^
  --name filekit ^
  --collect-all docx ^
  --collect-all openpyxl ^
  --collect-all pptx ^
  --collect-all pypdf ^
  --add-data "%cd%\web;web" ^
  --add-data "%cd%\tools\filekit\filekit.py;." ^
  --add-data "%cd%\requirements.txt;." ^
  --paths "%cd%\tools\filekit" ^
  --workpath build_tmp ^
  --specpath build_tmp ^
  --clean --noconfirm ^
  server.py
if errorlevel 1 (
  echo [X] 打包失败
  pause
  exit /b 1
)

REM 3. 结果
echo.
echo [3/3] 完成
echo   产物：%cd%\dist\filekit.exe
dir dist

echo.
echo 分发方式：把 dist\filekit.exe 单独发给别人，双击即可运行
echo   （会在本地起服务并自动打开浏览器）
pause
