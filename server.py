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
import io, json, os, queue, re, signal, socket, subprocess, sys, threading, time, urllib.request, webbrowser, datetime, importlib.util
from contextlib import redirect_stdout
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler
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
# 热更新：源码变化 → SSE 推给浏览器 → 自动刷新 / 一键重启
#
# 原理：浏览器收不到"服务端主动推送"（除了 SSE/WebSocket）。
#       所以服务端盯住自己的源码文件，一有变化就通过 SSE 长连接广播，
#       页面收到后自己刷新（前端改动）或提示重启（Python 改动）。
# ============================================================================
_SSE_CLIENTS = []
_SSE_LOCK = threading.Lock()
_UPSTREAM = {'version': None}      # 上游最新版本（后台查，供页面提示）
_SERVER = None                 # 保存 HTTPServer 实例，重启前要关掉以释放端口
UPSTREAM_REPO = 'xyg165/Smart-Toolkit'    # 上游仓库（查新版本用）


def _broadcast(msg):
    """给所有 SSE 客户端发一条消息"""
    with _SSE_LOCK:
        dead = []
        for q in _SSE_CLIENTS:
            try:
                q.put_nowait(msg)
            except Exception:
                dead.append(q)
        for q in dead:
            _SSE_CLIENTS.remove(q)


def _watched_files():
    """要被监控的文件：前端 + 两个 Python 源"""
    out = []
    for rel in ('web/index.html', 'server.py', 'filekit.py', 'tools/filekit/filekit.py'):
        f = resource_path(rel)
        # PyInstaller 打包后这些是解包到临时目录的副本，改了也没意义 → 跳过
        if f.exists() and not getattr(sys, 'frozen', False):
            out.append(f)
    return out


def watch_sources(interval=2.0):
    """后台线程：监控源码 mtime，变化就广播"""
    files = _watched_files()
    if not files:
        return
    mtimes = {}
    for f in files:
        try:
            mtimes[str(f)] = f.stat().st_mtime
        except Exception:
            pass
    while True:
        time.sleep(interval)
        changed = []
        for k, old in list(mtimes.items()):
            try:
                new = Path(k).stat().st_mtime
                if abs(new - old) > 0.5:
                    mtimes[k] = new
                    changed.append(Path(k).name)
            except Exception:
                pass
        if changed:
            py_changed = any(n.endswith('.py') for n in changed)
            _broadcast({'event': 'changed',
                        'files': changed,
                        'need_restart': py_changed,
                        'version': APP_VERSION})
            time.sleep(4)      # 防抖：一次保存往往触发多次


def check_upstream(timeout=4):
    """查上游最新 tag；失败静默返回 None（不打扰用户）"""
    try:
        req = urllib.request.Request(
            f'https://api.github.com/repos/{UPSTREAM_REPO}/tags',
            headers={'User-Agent': 'filekit'})
        data = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
        if isinstance(data, list) and data:
            return str(data[0].get('name', '')).lstrip('v')
    except Exception:
        pass
    return None


def _restart_self(port):
    """原地重启当前进程（端口不变）

    用 os.execv 替换进程映像 —— 它**保留 PID**，所以"PID 没变"不代表没重启。
    验证方法：改一下 filekit.py 的 VERSION，重启后看 /api/env 返回的版本号。
    """
    script = os.path.abspath(sys.argv[0])
    cleaned, skip = [], False
    for a in sys.argv[1:]:
        if skip:
            skip = False
            continue
        if a == '--port':
            skip = True
            continue
        if a in ('--no-browser', '--keep-old'):
            continue
        cleaned.append(a)
    cleaned += ['--port', str(port), '--keep-old']

    if getattr(sys, 'frozen', False):
        cmd = [sys.executable] + cleaned            # 打包版：可执行文件本身即程序
    else:
        cmd = [sys.executable, '-u', script] + cleaned   # 源码版：-u 保证输出不缓冲
    try:
        if _SERVER is not None:
            _SERVER.server_close()      # 先释放端口，新进程才能立刻绑上同一个端口
    except Exception:
        pass
    try:
        os.execv(sys.executable, cmd)
    except Exception:
        os._exit(0)

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
    """整批回退，并把日志里的条目标记为已回退（供执行记录页显示状态）"""
    try:
        buf = io.StringIO()
        with redirect_stdout(buf):
            fk.do_rollback(logfile)
        # 回退成功后更新日志标记（否则「执行记录」页会误显示成「文件已变动」）
        try:
            log = Path(logfile)
            data = json.loads(log.read_text(encoding='utf-8'))
            folder = Path(data.get('directory', ''))
            for r in data.get('renames', []):
                if r.get('rolled_back'):
                    continue
                # 原名已恢复、新名已不存在 → 视为已回退
                if (folder / r.get('old', '')).exists() and not (folder / r.get('new', '')).exists():
                    r['rolled_back'] = True
            log.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception:
            pass
        return {'ok': True, 'msg': buf.getvalue().strip()}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def api_history(limit=100):
    """执行记录列表（含每个文件的明细与当前状态）"""
    out = []
    for item in reversed(fk.load_history()[-limit:]):
        log = Path(item.get('log', ''))
        rec = {'time': item.get('time', ''), 'dir': item.get('dir', ''),
               'log': str(log), 'count': item.get('count', 0),
               'exists': log.exists(), 'items': []}
        if log.exists():
            try:
                data = json.loads(log.read_text(encoding='utf-8'))
                folder = Path(data.get('directory', item.get('dir', '')))
                for r in data.get('renames', []):
                    new_name, old_name = r.get('new', ''), r.get('old', '')
                    done = bool(r.get('rolled_back'))
                    rec['items'].append({
                        'old': old_name, 'new': new_name,
                        'cat': r.get('category'),
                        'rolled_back': done,
                        'can_rollback': (not done
                                         and (folder / new_name).exists()
                                         and not (folder / old_name).exists()),
                    })
            except Exception as e:
                rec['error'] = str(e)
        out.append(rec)
    return {'records': out}


def api_rollback_one(logfile, old):
    """把某条记录里的单个文件改回原名（其余文件不动）"""
    log = Path(logfile)
    if not log.exists():
        return {'ok': False, 'error': '日志文件不存在（文件夹可能被移动或删除）'}
    try:
        data = json.loads(log.read_text(encoding='utf-8'))
    except Exception as e:
        return {'ok': False, 'error': f'日志读取失败：{e}'}
    folder = Path(data.get('directory', ''))
    for r in data.get('renames', []):
        if r.get('old') != old:
            continue
        if r.get('rolled_back'):
            return {'ok': False, 'error': '这个文件已经回退过了'}
        src, tgt = folder / r.get('new', ''), folder / r.get('old', '')
        if not src.exists():
            return {'ok': False, 'error': f'找不到文件（可能已被移动或改名）：{r.get("new")}'}
        if tgt.exists():
            return {'ok': False, 'error': f'原文件名已被占用：{r.get("old")}'}
        try:
            src.rename(tgt)
        except Exception as e:
            return {'ok': False, 'error': f'改名失败：{e}'}
        r['rolled_back'] = True
        try:
            log.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception:
            pass
        return {'ok': True, 'msg': f'已回退为：{r.get("old")}'}
    return {'ok': False, 'error': '这条记录里没有找到该文件'}


def api_env():
    missing = fk.check_env(need_content=True)
    return {'app': 'filekit',
            'version': APP_VERSION,
            'upstream': _UPSTREAM.get('version'),
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

    def _sse(self):
        """SSE 长连接：服务端有变化就主动推给浏览器"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.end_headers()
        q = queue.Queue()
        with _SSE_LOCK:
            _SSE_CLIENTS.append(q)
        try:
            self.wfile.write(b'retry: 3000\n\n')
            self.wfile.flush()
            while True:
                try:
                    msg = q.get(timeout=15)
                    data = 'data: ' + json.dumps(msg, ensure_ascii=False) + '\n\n'
                except queue.Empty:
                    data = ': ping\n\n'          # 心跳，防代理断开
                self.wfile.write(data.encode('utf-8'))
                self.wfile.flush()
        except Exception:
            pass
        finally:
            with _SSE_LOCK:
                if q in _SSE_CLIENTS:
                    _SSE_CLIENTS.remove(q)

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
        elif u.path == '/api/history':
            self._send(200, api_history())
        elif u.path == '/api/env':
            self._send(200, api_env())
        elif u.path == '/api/events':
            self._sse()
        elif u.path == '/api/restart':
            self._send(200, {'ok': True, 'msg': '正在重启…'})
            port_now = self.server.server_port
            threading.Timer(0.6, lambda: _restart_self(port_now)).start()
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
        elif u.path == '/api/rollback_one':
            self._send(200, api_rollback_one(payload.get('logfile', ''),
                                             payload.get('old', '')))
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

    # 后台起「源码监控」：代码一改就通知浏览器（前后端都算）
    threading.Thread(target=watch_sources, daemon=True).start()

    # 后台查上游最新版本（失败静默，不打扰）
    def _bg_upstream():
        v = check_upstream()
        if v:
            _UPSTREAM['version'] = v
            if v != APP_VERSION:
                print(f'  提示：上游已有新版本 v{v}（当前 v{APP_VERSION}）')
                _broadcast({'event': 'upstream', 'version': v})
    threading.Thread(target=_bg_upstream, daemon=True).start()

    global _SERVER
    try:
        _SERVER = ThreadingHTTPServer(('127.0.0.1', port), Handler)
        _SERVER.serve_forever()
    except KeyboardInterrupt:
        print('\n已停止')


if __name__ == '__main__':
    main()
