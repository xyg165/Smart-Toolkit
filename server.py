#!/usr/bin/env python3
"""
filekit web —— 本地网页版文件整理工具
================================================================
启动后在本地浏览器操作：选文件夹 → 预览 → 确认执行 → 可回退

  · 全程本地运行，文件不出本机（监听 127.0.0.1）
  · 零 Web 框架依赖（只用 Python 标准库 http.server）
  · 支持单个文件夹 / 批量多个文件夹
  · 支持按文件夹回退（读取历史日志）

用法：
  python server.py                # 启动并自动打开浏览器
  python server.py --port 8899    # 指定端口
  python server.py --no-browser   # 不自动打开浏览器
"""
import io, json, os, sys, threading, webbrowser, socket, datetime, importlib.util
from contextlib import redirect_stdout
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def resource_path(rel):
    """兼容 PyInstaller 打包后的资源路径"""
    base = getattr(sys, '_MEIPASS', HERE)
    return Path(base) / rel


def load_filekit():
    for rel in ('filekit.py', 'tools/filekit/filekit.py'):
        cand = resource_path(rel)
        if cand.exists():
            spec = importlib.util.spec_from_file_location('filekit', cand)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            return m
    raise FileNotFoundError('找不到 filekit.py')


try:
    fk = load_filekit()
except Exception as e:
    print(f'[错误] 无法加载 filekit.py: {e}')
    sys.exit(1)


# ============================================================================
# 业务 API
# ============================================================================
def api_browse(path):
    """列出目录内容（用于网页里的文件夹选择）"""
    if not path:
        path = str(Path.home())
    p = Path(path).expanduser()
    try:
        p = p.resolve()
    except Exception:
        pass
    if not p.is_dir():
        return {'error': f'不是有效目录：{path}'}
    dirs, files = [], []
    try:
        # 文件夹排在前面，同组内按名称排序
        items = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        for item in items:
            if item.name.startswith('.'):
                continue
            try:
                if item.is_dir():
                    dirs.append({'name': item.name, 'path': str(item)})
                else:
                    st = item.stat()
                    files.append({'name': item.name, 'size': st.st_size,
                                  'mtime': int(st.st_mtime)})
            except (PermissionError, OSError):
                continue
    except PermissionError:
        return {'error': f'无权限访问：{p}'}
    parent = str(p.parent) if p.parent != p else None
    return {'path': str(p), 'parent': parent, 'dirs': dirs, 'files': files,
            'file_count': len(files), 'sep': os.sep}


def _plan_quiet(directory, mode, opts):
    buf = io.StringIO()
    with redirect_stdout(buf):
        plan = fk.build_plan(directory, mode=mode,
                             sep=opts.get('sep', '_'),
                             add_date=opts.get('add_date', True),
                             lower=opts.get('lower', False),
                             pad=opts.get('pad', False))
    return plan


def api_preview(dirs, mode, opts):
    out = []
    for d in dirs:
        try:
            plan = _plan_quiet(d, mode, opts)
            items = [{'old': i['old'], 'new': i['new'], 'cat': i.get('cat', ''),
                      'score': i.get('score', 0), 'chars': i.get('chars', 0)} for i in plan]
            out.append({'dir': d, 'ok': True, 'count': len(items), 'items': items})
        except SystemExit:
            out.append({'dir': d, 'ok': False, 'error': '目录不存在', 'count': 0, 'items': []})
        except Exception as e:
            out.append({'dir': d, 'ok': False, 'error': str(e), 'count': 0, 'items': []})
    return out


def api_apply(dirs, mode, opts):
    total, logs = 0, []
    for d in dirs:
        try:
            plan = _plan_quiet(d, mode, opts)
            if not plan:
                continue
            buf = io.StringIO()
            with redirect_stdout(buf):
                fk.do_apply(d, plan)
            total += len(plan)
            found = sorted(Path(d).glob('_filekit_log_*.json'))
            if found:
                logs.append({'dir': d, 'log': str(found[-1])})
        except Exception as e:
            return {'ok': False, 'error': f'{d}: {e}'}
    return {'ok': True, 'renamed': total, 'logs': logs}


def api_logs(directory):
    p = Path(directory)
    if not p.is_dir():
        return {'error': '目录不存在', 'logs': []}
    logs = []
    for f in sorted(p.glob('_filekit_log_*.json'), reverse=True):
        try:
            data = json.load(open(f, encoding='utf-8'))
            done = [r for r in data.get('renames', [])
                    if (p / r['new']).exists() and not (p / r['old']).exists()]
            logs.append({'file': str(f), 'name': f.name,
                         'time': data.get('time', ''), 'count': len(data.get('renames', [])),
                         'rollbackable': len(done)})
        except Exception:
            continue
    return {'dir': str(p), 'logs': logs}


def api_rollback(logfile):
    try:
        buf = io.StringIO()
        with redirect_stdout(buf):
            fk.do_rollback(logfile)
        return {'ok': True, 'msg': buf.getvalue().strip()}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def api_env():
    missing = fk.check_env(need_content=True)
    return {'missing': [{'key': k, 'name': fk.DEP_HINTS.get(k, (k, ''))[0],
                         'how': fk.DEP_HINTS.get(k, (k, ''))[1]} for k in missing],
            'ok': not missing}


# ============================================================================
# HTTP 服务
# ============================================================================
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass   # 静音，避免刷屏

    def _send(self, code, body, ctype='application/json; charset=utf-8'):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path in ('/', '/index.html'):
            f = resource_path('web/index.html')
            if f.exists():
                self._send(200, f.read_bytes(), 'text/html; charset=utf-8')
            else:
                self._send(404, {'error': 'web/index.html 缺失'})
        elif u.path == '/api/browse':
            self._send(200, api_browse(q.get('path', '')))
        elif u.path == '/api/logs':
            self._send(200, api_logs(q.get('dir', '')))
        elif u.path == '/api/env':
            self._send(200, api_env())
        else:
            self._send(404, {'error': 'not found'})

    def do_POST(self):
        try:
            n = int(self.headers.get('Content-Length', 0))
            payload = json.loads(self.rfile.read(n) or b'{}')
        except Exception:
            payload = {}
        u = urlparse(self.path)
        if u.path == '/api/preview':
            self._send(200, api_preview(payload.get('dirs', []), payload.get('mode', 'auto'),
                                        payload.get('opts', {})))
        elif u.path == '/api/apply':
            self._send(200, api_apply(payload.get('dirs', []), payload.get('mode', 'auto'),
                                      payload.get('opts', {})))
        elif u.path == '/api/rollback':
            self._send(200, api_rollback(payload.get('logfile', '')))
        else:
            self._send(404, {'error': 'not found'})


def free_port(preferred=8765):
    for port in range(preferred, preferred + 40):
        with socket.socket() as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
    return 0


def main():
    import argparse
    ap = argparse.ArgumentParser(description='filekit web —— 本地网页版文件整理')
    ap.add_argument('--port', type=int, default=8765)
    ap.add_argument('--no-browser', action='store_true')
    args = ap.parse_args()

    port = free_port(args.port)
    url = f'http://127.0.0.1:{port}/'

    # 启动前环境自检（缺依赖不影响重命名，只是读不到对应格式）
    missing = []
    try:
        missing = fk.check_env(need_content=True)
    except Exception:
        pass

    print('=' * 56)
    print('  filekit web —— 本地文件整理工具')
    print('=' * 56)
    print(f'  地址：{url}')
    if missing:
        print(f'  环境：缺 {len(missing)} 项依赖（不影响重命名功能）')
        for k in missing:
            nm = fk.DEP_HINTS.get(k, (k, ''))[0]
            print(f'        - {nm}')
        print('  修复：pip install -r requirements.txt')
    else:
        print('  环境：依赖齐全')
    print('  提示：全程本地运行，文件不出本机')
    print('  关闭此窗口即停止服务')
    print('=' * 56)

    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    try:
        HTTPServer(('127.0.0.1', port), Handler).serve_forever()
    except KeyboardInterrupt:
        print('\n已停止')


if __name__ == '__main__':
    main()
