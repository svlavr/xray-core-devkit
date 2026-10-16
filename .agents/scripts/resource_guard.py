"""Own subprocess trees and disposable temp; never purge shared Go caches."""
import argparse
import ctypes
import copy
import json
import os
from pathlib import Path
import queue
import re
import shutil
import signal
import stat
import subprocess
import sys
import threading
import time
import uuid

ROOT = Path(__file__).absolute().parents[2]
TRANSIENT = ROOT / '.local/host/transient'
IDLE_SECONDS = 120


class CancelledError(RuntimeError):
    """The caller cancelled this owned operation."""


def check_cancelled(cancelled):
    if cancelled is not None and cancelled.is_set():
        raise CancelledError('MCP operation cancelled')


def backend_work(method):
    """Protocol housekeeping is not a reason to retain a heavy backend."""
    return bool(method and not method.startswith('notifications/') and method not in {
        'initialize', 'ping', 'tools/list', 'resources/list',
        'resources/templates/list', 'prompts/list'})


def cached_control(message, catalogue=None):
    if 'id' not in message:
        return None
    if message.get('method') == 'ping':
        return {'jsonrpc': '2.0', 'id': message['id'], 'result': {}}
    if message.get('method') == 'tools/list' and catalogue is not None and not message.get('params'):
        return {'jsonrpc': '2.0', 'id': message['id'], 'result': copy.deepcopy(catalogue)}
    return None


def complete_catalogue(request, response):
    return request.get('method') == 'tools/list' and not request.get('params') and 'result' in response and not response['result'].get('nextCursor')


def plain_path(path):
    """Reject links/reparse ancestors before creating or recursively removing."""
    path = Path(os.path.abspath(path))
    for item in [*reversed(path.parents), path]:
        if item.exists() or item.is_symlink():
            metadata = item.lstat()
            if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, 'st_file_attributes', 0) & 0x400:
                raise ValueError('Transient paths must not contain links/reparse points: ' + str(item))
    return path


def lock_file(handle):
    handle.seek(0)
    if os.name == 'nt':
        import msvcrt
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def clean_stale(base=TRANSIENT):
    """Only recover marked owned temp with an acquirable OS lifetime lease."""
    base = plain_path(base)
    removed = []
    if not base.exists():
        return removed
    for folder in base.glob('run-*'):
        if not re.fullmatch(r'run-[0-9a-f]{32}', folder.name):
            continue
        lease = base / (folder.name + '.lock')
        try:
            plain_path(folder)
            plain_path(lease)
            if not lease.is_file() or lease.stat().st_nlink != 1:
                continue
            with lease.open('r+b') as handle:
                lock_file(handle)
                marker = folder / 'owner.json'
                plain_path(marker)
                if json.loads(marker.read_text()) != {'schema': 1, 'run': folder.name}:
                    continue
                # shutil.rmtree does not traverse symlinks, but also reject
                # junctions and aliases before deletion for an honest skip.
                for directory, children, files in os.walk(folder, followlinks=False):
                    for name in children + files:
                        plain_path(Path(directory) / name)
                shutil.rmtree(folder)
                removed.append(folder.name)
            # Run UUIDs are never reused. A waiter on the old inode will find
            # no directory; removing its completed lease cannot split ownership.
            lease.unlink(missing_ok=True)
        except (OSError, ValueError):
            continue
    return removed


def _kernel():
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE, *([ctypes.c_void_p] * 4)]
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    return kernel


def _birth(kernel, handle):
    times = [ctypes.c_uint64() for _ in range(4)]
    if not kernel.GetProcessTimes(handle, *(ctypes.byref(value) for value in times)):
        raise ctypes.WinError(ctypes.get_last_error())
    return str(times[0].value)


def process_token(pid):
    if os.name == 'nt':
        kernel = _kernel()
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            return _birth(kernel, handle)
        finally:
            kernel.CloseHandle(handle)
    # WSL/Linux workers use the kernel start tick to reject recycled PIDs.
    fields = Path('/proc/' + str(pid) + '/stat').read_text().rsplit(')', 1)[1].split()
    if fields[0] in {'Z', 'X'}:
        raise ProcessLookupError('Owner has exited')
    return fields[19]


def contain_self():
    """Establish containment before any backend can spawn descendants."""
    if os.name != 'nt':
        return None  # spawn creates a dedicated process group/session.
    from ctypes import wintypes
    kernel = _kernel()
    class Basic(ctypes.Structure):
        _fields_ = [('ProcessTime', ctypes.c_int64), ('JobTime', ctypes.c_int64),
                    ('Flags', wintypes.DWORD), ('MinWorkingSet', ctypes.c_size_t),
                    ('MaxWorkingSet', ctypes.c_size_t), ('ActiveProcesses', wintypes.DWORD),
                    ('Affinity', ctypes.c_size_t), ('Priority', wintypes.DWORD), ('Scheduling', wintypes.DWORD)]
    class IO(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint64) for name in ['ReadOps', 'WriteOps', 'OtherOps', 'ReadBytes', 'WriteBytes', 'OtherBytes']]
    class Extended(ctypes.Structure):
        _fields_ = [('Basic', Basic), ('IO', IO), ('ProcessMemory', ctypes.c_size_t),
                    ('JobMemory', ctypes.c_size_t), ('PeakProcessMemory', ctypes.c_size_t), ('PeakJobMemory', ctypes.c_size_t)]
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    job = kernel.CreateJobObjectW(None, None)
    limits = Extended()
    limits.Basic.Flags = 0x2000  # KILL_ON_JOB_CLOSE; handle is not inherited.
    if not job or not kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
        raise ctypes.WinError(ctypes.get_last_error())
    if not kernel.AssignProcessToJobObject(job, kernel.GetCurrentProcess()):
        raise ctypes.WinError(ctypes.get_last_error())
    return job  # Keep handle until OS process exit, including abrupt death.


def watch_owner(pid, token):
    if os.name == 'nt':
        kernel = _kernel()
        handle = kernel.OpenProcess(0x100000 | 0x1000, False, pid)
        if not handle or _birth(kernel, handle) != token:
            os._exit(125)
        def watch():
            kernel.WaitForSingleObject(handle, 0xFFFFFFFF)
            os._exit(125)  # Fail closed also on wait failure.
        threading.Thread(target=watch, daemon=True).start()
    else:
        def watch():
            while True:
                try:
                    if process_token(pid) != token:
                        break
                except OSError:
                    break
                time.sleep(.25)
            os.killpg(os.getpgrp(), signal.SIGKILL)
        threading.Thread(target=watch, daemon=True).start()


def stop(process):
    if process.poll() is None:
        if os.name == 'nt':
            process.kill()  # Only our supervisor; its job owns descendants.
        else:
            os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=10)


def bounded_send(process, message, timeout, cancelled=None):
    """A pipe write has its own deadline, including a nonreading backend."""
    completed = threading.Event()
    errors = []
    def write():
        try:
            process.stdin.write(json.dumps(message) + '\n')
            process.stdin.flush()
        except BaseException as error:
            errors.append(error)
        finally:
            completed.set()
    check_cancelled(cancelled)
    writer = threading.Thread(target=write, daemon=True)
    writer.start()
    deadline = time.monotonic() + timeout
    try:
        while not completed.wait(min(.1, max(0, deadline-time.monotonic()))):
            check_cancelled(cancelled)
            if time.monotonic() >= deadline:
                raise TimeoutError('MCP send deadline exceeded')
        check_cancelled(cancelled)
    except BaseException:
        stop(process)
        writer.join(timeout=2)
        raise
    writer.join(timeout=2)
    if errors:
        raise errors[0]


class MCPOutput:
    """Bounded frontend output; a stalled client cannot keep owned trees alive."""
    def __init__(self, timeout=180):
        self.timeout = timeout
        self.stream = sys.stdout
        self.queue = queue.Queue(maxsize=64)
        self.lock = threading.Lock()
        self.pending = 0
        self.started = None
        self.drained = threading.Event(); self.drained.set()
        self.stopped = threading.Event()
        def writer():
            while not self.stopped.is_set():
                try:
                    message = self.queue.get(timeout=.1)
                except queue.Empty:
                    continue
                self.started = time.monotonic()
                try:
                    print(json.dumps(message, ensure_ascii=False), file=self.stream, flush=True)
                except (OSError, ValueError):
                    os._exit(124)
                finally:
                    self.started = None
                with self.lock:
                    self.pending -= 1
                    if not self.pending:self.drained.set()
        def watchdog():
            while not self.stopped.wait(.1):
                started = self.started
                if started is not None and time.monotonic() - started >= self.timeout:
                    # A writer can hold sys.stdout's lock indefinitely. Exit
                    # without interpreter flushing; supervisor owner-watchers
                    # reap only this frontend's descendants and retain scratch
                    # for the next lease-checked recovery.
                    os._exit(124)
        self.writer = threading.Thread(target=writer, daemon=True)
        self.writer.start()
        threading.Thread(target=watchdog, daemon=True).start()

    def emit(self, message):
        with self.lock:
            self.pending += 1
            self.drained.clear()
        try:
            self.queue.put(message, timeout=min(.25, self.timeout))
        except queue.Full:
            os._exit(124)

    def close(self):
        if not self.drained.wait(timeout=min(2, self.timeout)):
            os._exit(124)
        self.stopped.set()
        self.writer.join(timeout=1)


class ManagedProcess(subprocess.Popen):
    def __init__(self, command, *, cwd=None, env=None, transient=TRANSIENT, **kwargs):
        self.transient = plain_path(transient)
        self.transient.mkdir(parents=True, exist_ok=True)
        clean_stale(self.transient)
        launch = [sys.executable, str(Path(__file__).absolute()), '--supervise',
                  json.dumps([str(value) for value in command]), '--transient', str(self.transient),
                  '--owner', str(os.getpid()), '--token', process_token(os.getpid())]
        for descriptor in kwargs.get('pass_fds', ()):
            launch += ['--keep-fd', str(descriptor)]
        kwargs.pop('start_new_session', None)
        # Explicit fd handles also work in hidden Windows launchers, where
        # native GetStdHandle inheritance can silently discard command output.
        for name, stream in [('stdin', sys.stdin), ('stdout', sys.stdout), ('stderr', sys.stderr)]:
            if kwargs.get(name) is None:
                kwargs[name] = stream
        super().__init__(launch, cwd=cwd, env=env, start_new_session=os.name != 'nt', **kwargs)

    def wait(self, timeout=None):
        result = super().wait(timeout=timeout)
        clean_stale(self.transient)
        return result


class Relay:
    """Transparent async stdio relay with idle eviction and handshake replay."""
    def __init__(self, command, cwd, env=None, transform=None, idle=IDLE_SECONDS, timeout=180, transient=TRANSIENT):
        self.command, self.cwd, self.env = command, cwd, env
        self.transient = transient
        self.transform = transform or (lambda message, method: message)
        self.idle, self.timeout = idle, timeout
        self.events = queue.Queue(maxsize=64)
        self.process = None
        self.reader = None
        self.generation = 0
        self.initialize = None
        self.pending = {}
        self.admitted = {}
        self.reverse = {}
        self.catalogue = None
        self.catalogue_revision = 0
        self.replay = None
        self.deferred = []
        self.write_started = None
        self.output = None

    def emit(self, message):
        self.output.emit(message)

    def send(self, message):
        if not self.process:
            return False
        if 'id' in message and 'method' in message:
            kind = message.get('params', {}).get('name') if message['method'] == 'tools/call' else message['method']
            self.pending[message['id']] = (kind, self.admitted.get(message['id'], time.monotonic()), backend_work(message['method']), message['method']=='tools/list' and not message.get('params'), self.catalogue_revision)
        try:
            self.writes.put_nowait(message)
            return True
        except queue.Full:
            self.close('MCP writer queue limit exceeded')
            return False

    def start(self):
        self.generation += 1
        generation = self.generation
        self.process = ManagedProcess(self.command, cwd=self.cwd, env=self.env, transient=self.transient,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=sys.stderr,
            text=True, encoding='utf-8', bufsize=1,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        stream = self.process.stdout
        self.reader_stop = threading.Event()
        stopped = self.reader_stop
        self.writes = queue.Queue(maxsize=64)
        self.write_started = None
        def enqueue(value):
            while not stopped.is_set():
                try:
                    self.events.put(('backend', generation, value), timeout=.2)
                    return
                except queue.Full:
                    pass
        def read():
            try:
                for line in stream:
                    try:
                        enqueue(json.loads(line))
                    except ValueError:
                        sys.stderr.write(line)
            finally:
                enqueue(None)
        self.reader = threading.Thread(target=read, daemon=True)
        self.reader.start()
        def write():
            while not stopped.is_set():
                try:
                    message = self.writes.get(timeout=.2)
                except queue.Empty:
                    continue
                self.write_started = time.monotonic()
                try:
                    self.process.stdin.write(json.dumps(message) + '\n')
                    self.process.stdin.flush()
                except (OSError, ValueError):
                    enqueue(None)
                    return
                finally:
                    self.write_started = None
        self.writer = threading.Thread(target=write, daemon=True)
        self.writer.start()
        if self.initialize:
            self.replay = 'resource-replay-' + uuid.uuid4().hex
            self.send({**self.initialize, 'id': self.replay})

    def close(self, error=None):
        if self.process:
            self.reader_stop.set()
            stop(self.process)
            self.reader.join(timeout=2)
            self.writer.join(timeout=2)
            if self.reader.is_alive():
                raise RuntimeError('Owned MCP reader did not terminate')
            if self.writer.is_alive():
                raise RuntimeError('Owned MCP writer did not terminate')
            try:
                self.process.stdin.close()
            except OSError:
                pass  # A killed nonreader may leave buffered bytes unflushable.
            self.process.stdout.close()
            self.process = None
        if error:
            for request_id in dict.fromkeys([*self.admitted, *self.pending, *(item['id'] for item in self.deferred if 'id' in item)]):
                if request_id != self.replay:
                    self.emit({'jsonrpc': '2.0', 'id': request_id,
                               'error': {'code': -32000, 'message': error}})
        self.pending.clear(); self.admitted.clear(); self.reverse.clear(); self.deferred.clear(); self.replay = None
        self.generation += 1  # Discard stale reader events from the old backend.

    def serve(self):
        self.output = MCPOutput(self.timeout)
        def inputs():
            try:
                for line in sys.stdin:
                    try:
                        self.events.put(('client', time.monotonic(), json.loads(line)))
                    except ValueError:
                        continue
            finally:
                self.events.put(('client', 0, None))
        threading.Thread(target=inputs, daemon=True).start()
        last_activity = time.monotonic()
        try:
            while True:
                now = time.monotonic()
                write_started = self.write_started
                if (write_started is not None and now - write_started >= self.timeout) or any(now - value[1] >= self.timeout for value in self.pending.values()) or any(now - started >= self.timeout for started in (*self.reverse.values(), *self.admitted.values())):
                    self.close('MCP request exceeded total deadline')
                elif self.process and not self.pending and not self.reverse and now - last_activity >= self.idle:
                    self.close()
                try:
                    side, generation, message = self.events.get(timeout=min(self.idle, .25))
                except queue.Empty:
                    now = time.monotonic()
                    if self.process and not self.pending and not self.reverse and now - last_activity >= self.idle:
                        self.close()
                    continue
                if side == 'backend' and generation != self.generation:
                    continue
                if side == 'client':
                    if message is None:
                        return
                    method = message.get('method')
                    control = cached_control(message, self.catalogue)
                    if control is not None:
                        self.emit(self.transform(control, method))
                        continue
                    if 'id' in message and method:
                        self.admitted[message['id']] = generation
                        if time.monotonic() - generation >= self.timeout:
                            self.close('MCP request exceeded total deadline')
                            continue
                    if 'id' in message and backend_work(method):
                        last_activity = time.monotonic()
                    if not self.process:
                        # Notifications alone do not retain a heavy backend.
                        if 'id' not in message:
                            continue
                        self.start()
                    if method == 'initialize':
                        self.initialize = message
                    if 'id' in message and 'method' not in message and message['id'] in self.reverse:
                        self.reverse.pop(message['id'], None)
                        self.send(message)
                        continue  # Reverse calls can be needed during replay.
                    if self.replay:
                        if len(self.deferred) >= 64:
                            self.close('MCP replay queue limit exceeded')
                        else:
                            self.deferred.append(message)
                        continue
                    if 'id' in message and 'method' not in message:
                        self.reverse.pop(message['id'], None)
                    self.send(message)
                elif message is None:
                    self.close('MCP backend exited')
                elif message.get('id') == self.replay and self.replay:
                    self.pending.pop(self.replay, None)
                    self.replay = None
                    if 'error' in message:
                        self.close('MCP backend reinitialization failed')
                        continue
                    self.send({'jsonrpc': '2.0', 'method': 'notifications/initialized', 'params': {}})
                    while self.deferred and self.process:
                        self.send(self.deferred.pop(0))
                else:
                    request_id = message.get('id')
                    method = None
                    if 'method' in message and 'id' in message:
                        self.reverse[request_id] = time.monotonic()
                    elif 'result' in message or 'error' in message:
                        self.admitted.pop(request_id, None)
                        method, _, work, can_cache, revision = self.pending.pop(request_id, (None, None, False, False, None))
                        if work:
                            last_activity = time.monotonic()
                        if can_cache and revision==self.catalogue_revision and 'result' in message and not message['result'].get('nextCursor'):
                            self.catalogue = copy.deepcopy(message['result'])
                    if message.get('method') == 'notifications/tools/list_changed':
                        self.catalogue = None
                        self.catalogue_revision += 1
                    self.emit(self.transform(message, method))
        finally:
            self.close()
            self.output.close()


def run(command, *, timeout=600, check=False, capture_output=False, input=None, cancelled=None, **kwargs):
    check_cancelled(cancelled)
    if capture_output:
        kwargs.update(stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if input is not None:
        kwargs['stdin'] = subprocess.PIPE
    with ManagedProcess(command, **kwargs) as process:
        try:
            if cancelled is None:
                stdout, stderr = process.communicate(input=input, timeout=timeout)
            else:
                deadline = time.monotonic()+timeout
                first = True
                while True:
                    check_cancelled(cancelled)
                    left = deadline-time.monotonic()
                    if left <= 0:
                        raise subprocess.TimeoutExpired(command, timeout)
                    try:
                        stdout, stderr = process.communicate(input=input if first else None, timeout=min(.1,left))
                        check_cancelled(cancelled)
                        break
                    except subprocess.TimeoutExpired:
                        first = False
        except BaseException:
            stop(process)
            raise
        result = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
        if check:
            result.check_returncode()
        return result


def idle_lines(stream, idle_seconds=IDLE_SECONDS):
    """Yield None only when no request is running; EOF ends the gateway."""
    if stream is not sys.stdin:
        yield from stream  # Preserve deterministic caller/generator semantics.
        return
    inbox = queue.Queue(maxsize=32)
    def reader():
        try:
            for line in stream:
                inbox.put(line)
        finally:
            inbox.put('')
    threading.Thread(target=reader, daemon=True).start()
    deadline = time.monotonic() + idle_seconds
    while True:
        if time.monotonic() >= deadline:
            yield None
            deadline = time.monotonic() + idle_seconds
            continue
        try:
            line = inbox.get(timeout=max(.001, deadline - time.monotonic()))
        except queue.Empty:
            yield None
            deadline = time.monotonic() + idle_seconds
            continue
        if not line:
            return
        yield line
        try:
            message = json.loads(line)
            if 'id' in message and backend_work(message.get('method')):
                deadline = time.monotonic() + idle_seconds
        except (ValueError, TypeError):
            pass


def supervise(args):
    job = contain_self()
    watch_owner(args.owner, args.token)
    base = plain_path(args.transient)
    name = 'run-' + uuid.uuid4().hex
    folder = base / name
    lease = base / (name + '.lock')
    with lease.open('x+b') as handle:
        handle.write(b'0'); handle.flush(); lock_file(handle)
        folder.mkdir()
        (folder / 'owner.json').write_text(json.dumps({'schema': 1, 'run': name}))
        env = dict(os.environ, TMP=str(folder), TEMP=str(folder), TMPDIR=str(folder), GOTMPDIR=str(folder))
        extra={'pass_fds':tuple(args.keep_fd)} if os.name!='nt' else {}
        result = subprocess.call(json.loads(args.supervise), env=env,
                                 stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr,
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), **extra)
        if os.name != 'nt':
            # The command has exited. Reap remaining members before releasing
            # its lease; stop() handles the whole group on timeout/cancellation.
            for entry in Path('/proc').iterdir():
                if entry.name.isdigit() and int(entry.name) != os.getpid():
                    try:
                        if os.getpgid(int(entry.name)) == os.getpgrp():
                            os.kill(int(entry.name), signal.SIGKILL)
                    except ProcessLookupError:
                        pass
        # Windows must close the job before parent-side temp cleanup.
        os._exit(result if result >= 0 else 128 - result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--supervise', help=argparse.SUPPRESS)
    parser.add_argument('--transient', type=Path, default=TRANSIENT, help=argparse.SUPPRESS)
    parser.add_argument('--cwd', type=Path, default=ROOT, help='Explicit command/worker checkout')
    parser.add_argument('--owner', type=int, help=argparse.SUPPRESS)
    parser.add_argument('--token', help=argparse.SUPPRESS)
    parser.add_argument('--keep-fd', type=int, action='append', default=[], help=argparse.SUPPRESS)
    parser.add_argument('--timeout', type=float, default=600)
    parser.add_argument('--clean', action='store_true', help='Recover only inactive managed temporary runs')
    parser.add_argument('--relay', action='store_true', help='Serve an asynchronous MCP with idle backend release')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.supervise:
        supervise(args)
    if args.clean:
        print(json.dumps({'removed': clean_stale()}))
        return 0
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('Expected -- <command>, or --clean')
    if args.relay:
        sys.stdin.reconfigure(encoding='utf-8')
        sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
        Relay(command, args.cwd, transient=args.transient).serve()
        return 0
    return run(command, cwd=args.cwd, transient=args.transient, timeout=args.timeout,
               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).returncode


if __name__ == '__main__':
    raise SystemExit(main())
