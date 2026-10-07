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
import io, json, os, re, signal, socket, subprocess, sys, threading, time, urllib.request, webbrowser, datetime, importlib.util
from contextlib import redirect_stdout
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

HERE = Path(__file__).resolve().parent

APP_VERSION = '3.2'
APP_PORT = 8765
APP_PORT_SCAN = 60        # 扫描 8765 ~ 8824 找旧实例
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
    APP_VERSION = getattr(fk, 'VERSION', APP_VERSION)   # 版本号以 filekit.py 为准
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


_ILLEGAL = set('/\\:*?"<>|')


def _check_name(name):
    """检查单个新文件名是否合法，返回错误信息或 None"""
    if not name or not name.strip():
        return '文件名不能为空'
    if any(c in _ILLEGAL for c in name):
        bad = ''.join(c for c in name if c in _ILLEGAL)
        return f'文件名含非法字符 {bad}：{name}'
    if name in ('.', '..'):
        return f'文件名无效：{name}'
    if len(name.encode('utf-8')) > 250:
        return f'文件名过长（{len(name)} 字符）：{name}'
    return None


def api_apply(dirs, mode, opts, groups=None):
    """执行重命名。
    groups（可选）：前端确认过的清单 [{dir, items:[{old,new,cat}]}]
                    带 items 时以它为准（支持用户手工编辑过的新名字）
    """
    total, logs = 0, []

    tasks = []
    if groups:
        for g in groups:
            if g.get('dir') and g.get('items'):
                tasks.append((g['dir'], g['items']))
    if not tasks:
        for d in dirs:
            plan = _plan_quiet(d, mode, opts)
            if plan:
                tasks.append((d, plan))

    for d, items in tasks:
        # ---- 校验（任何问题整批中止，不做半截）----
        news, olds = {}, set()
        for it in items:
            old, nw = it.get('old', ''), (it.get('new') or '').strip()
            err = _check_name(nw)
            if err:
                return {'ok': False, 'error': f'{d} → {err}'}
            if nw.lower() in news:
                return {'ok': False, 'error': f'{d} → 有两个文件会重名为同一个名字：{nw}'}
            news[nw.lower()] = old
            olds.add(old)
        for nw, old in news.items():
            tgt, src = Path(d) / nw, Path(d) / old
            if tgt.exists() and src.exists() and tgt.resolve() != src.resolve() and nw not in olds:
                return {'ok': False, 'error': f'{d} → 目标文件已存在：{nw}（请换一个名字）'}

        # ---- 执行 ----
        try:
            plan = [{'old': i['old'], 'new': (i['new'] or '').strip(), 'cat': i.get('cat')} for i in items]
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
    return {'app': 'filekit',
            'version': APP_VERSION,
            'pid': os.getpid(),
            'missing': [{'key': k, 'name': fk.DEP_HINTS.get(k, (k, ''))[0],
                         'how': fk.DEP_HINTS.get(k, (k, ''))[1]} for k in missing],
            'ok': not missing}


# ============================================================================
# 旧实例检测与清理
#
# 症状：装了新版本、浏览器里还是老功能 —— 因为**旧的 server 进程还在跑**，
#       新实例只能用别的端口起，而浏览器打开的是旧进程。
# 处理：启动前扫描端口 → 认出 filekit 实例 → 尝试停掉 → 再起新的。
# ============================================================================
def _port_open(port, timeout=0.05):
    try:
        with socket.socket() as sk:
            sk.settimeout(timeout)
            return sk.connect_ex(('127.0.0.1', port)) == 0
    except Exception:
        return False


def _pid_by_port(port):
    """通过系统命令反查监听某端口的进程 PID
    用于清理「老版本 filekit」—— 它们的 /api/env 不返回 PID，没法直接停。"""
    try:
        if os.name == 'nt':                      # Windows
            r = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, timeout=8)
            for line in r.stdout.splitlines():
                u = line.upper()
                if f':{port} ' in line and 'LISTENING' in u:
                    parts = line.split()
                    if parts and parts[-1].isdigit():
                        return int(parts[-1])
        else:                                     # macOS / Linux
            r = subprocess.run(['lsof', '-ti', f'tcp:{port}', '-sTCP:LISTEN'],
                               capture_output=True, text=True, timeout=8)
            if r.stdout.strip():
                return int(r.stdout.split()[0])
            r = subprocess.run(['ss', '-lptn', f'sport = :{port}'],
                               capture_output=True, text=True, timeout=8)
            m = re.search(r'pid=(\d+)', r.stdout)
            if m:
                return int(m.group(1))
    except Exception:
        pass
    return None


def _probe(port, timeout=0.5):
    """探测端口是否为 filekit 服务；是则返回 {port,pid,version}"""
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/env', timeout=timeout) as r:
            d = json.loads(r.read().decode('utf-8', 'ignore'))
        # 新版本有 app 字段；老版本没有，但有 missing/ok 特征
        if d.get('app') == 'filekit' or ('missing' in d and 'ok' in d):
            return {'port': port, 'pid': d.get('pid'), 'version': d.get('version', '旧版（无版本号）')}
    except Exception:
        pass
    return None


def find_running(except_pid=None):
    """扫描端口范围，找出正在运行的 filekit 实例"""
    found = []
    for port in range(APP_PORT, APP_PORT + APP_PORT_SCAN):
        if not _port_open(port):
            continue
        info = _probe(port)
        if not info:
            continue
        if info.get('pid') is None:
            # 老版本不返回 PID → 从系统反查，这样也能停掉
            info['pid'] = _pid_by_port(port)
            info['version'] = info.get('version') or '旧版（无版本号）'
        if info.get('pid') == except_pid:
            continue
        found.append(info)
    return found


def stop_instance(inst):
    """停掉一个 filekit 实例：先 SIGTERM，Windows/失败时用 taskkill"""
    pid = inst.get('pid')
    if not pid:
        return False
    try:
        os.kill(int(pid), signal.SIGTERM)
        return True
    except Exception:
        try:
            subprocess.run(['taskkill', '/F', '/PID', str(pid)],
                           capture_output=True, timeout=5)
            return True
        except Exception:
            return False


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
        elif u.path == '/api/quit':
            self._send(200, {'ok': True, 'msg': '正在退出'})
            threading.Timer(0.3, lambda: os._exit(0)).start()
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
                                      payload.get('opts', {}), payload.get('groups')))
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
    ap.add_argument('--keep-old', action='store_true',
                    help='不停掉已在运行的旧实例（默认会停掉，确保用新版本）')
    args = ap.parse_args()

    # ---- 先看看有没有旧实例在跑（装了新版却还是老功能，多半是它）----
    old_running = find_running(except_pid=os.getpid())
    if old_running and not args.keep_old:
        print('=' * 56)
        print('  检测到已有 filekit 实例在运行：')
        for r in old_running:
            print(f"     端口 {r['port']} · 版本 {r['version']} · PID {r.get('pid') or '未知'}")
        stoppable = [r for r in old_running if r.get('pid')]
        if stoppable:
            print('  正在停止旧实例（保证你用的是新版本）…')
            n_ok = sum(1 for r in stoppable if stop_instance(r))
            print(f'  已停止 {n_ok}/{len(stoppable)} 个')
            time.sleep(0.8)
        else:
            print('  ⚠️  无法自动停止旧实例（可能权限不足）')
            print('     请找到那个命令行窗口按 Ctrl+C 关闭，然后重新运行本脚本。')
            print('     或手动执行：')
            print('       Linux/macOS :  lsof -ti:8765 | xargs kill')
            print('       Windows     :  netstat -ano | findstr :8765  →  taskkill /F /PID <PID>')
            print('     （本次仍会用别的端口启动新版本）')
        print('=' * 56)

    port = free_port(args.port)
    url = f'http://127.0.0.1:{port}/'

    # 启动前环境自检（缺依赖不影响重命名，只是读不到对应格式）
    missing = []
    try:
        missing = fk.check_env(need_content=True)
    except Exception:
        pass

    print('=' * 56)
    print(f'  filekit web —— 本地文件整理工具   v{APP_VERSION}')
    print('=' * 56)
    print(f'  地址：{url}')
    print(f'  版本：v{APP_VERSION}（浏览器右上角也会显示，用于确认新旧）')
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
