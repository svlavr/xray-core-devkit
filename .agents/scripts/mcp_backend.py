"""A sequential, session-owned JSON-lines MCP client with bounded shutdown."""
import json
import queue
import subprocess
import threading
import time
from resource_guard import ManagedProcess, stop, bounded_send, check_cancelled


class Backend:
    def __init__(self, command, cwd, env, stderr, timeout=60, initialize=None, notify=None, deadline=None, cancelled=None):
        self.timeout = timeout
        self.notify = notify
        self.closed = False
        self.inbox = queue.Queue()
        self.proc = ManagedProcess(
            command, cwd=cwd, env=env, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=stderr, text=True, encoding='utf-8',
            bufsize=1, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()
        try:
            initialization = initialize or {'jsonrpc': '2.0', 'id': 'xray-initialize',
                'method': 'initialize', 'params': {'protocolVersion': '2024-11-05',
                'capabilities': {}, 'clientInfo': {'name': 'xray-checkout-guard', 'version': '2'}}}
            # This sequential gateway owns roots through cwd. Do not advertise
            # reverse calls that would require reading a second client request.
            initialization = {**initialization, 'params': {**initialization.get('params', {}), 'capabilities': {}}}
            result = self.call(initialization, deadline=deadline, cancelled=cancelled)
            if 'error' in result:
                raise RuntimeError('MCP initialization failed: ' + str(result['error']))
            self.initialization = result
            remaining = deadline-time.monotonic() if deadline is not None else self.timeout
            if remaining <= 0:raise TimeoutError('MCP initialization budget expired')
            self.send({'jsonrpc': '2.0', 'method': 'notifications/initialized', 'params': {}}, timeout=remaining, cancelled=cancelled)
        except BaseException:
            self.close(force=cancelled is not None and cancelled.is_set())
            raise

    def _read(self):
        try:
            for line in self.proc.stdout:
                try:
                    value = json.loads(line)
                    if 'method' in value:
                        if 'id' in value:
                            self.send({'jsonrpc': '2.0', 'id': value['id'], 'error': {
                                'code': -32601, 'message': 'Reverse client calls are not negotiated by this gateway'}})
                        elif self.notify:
                            self.notify(value)
                    else:
                        self.inbox.put(value)
                except ValueError:
                    continue
        finally:
            self.inbox.put(None)

    def send(self, message, timeout=None, cancelled=None):
        bounded_send(self.proc, message, self.timeout if timeout is None else timeout, cancelled=cancelled)

    def call(self, message, deadline=None, cancelled=None):
        check_cancelled(cancelled)
        deadline = min(deadline, time.monotonic()+self.timeout) if deadline is not None else time.monotonic()+self.timeout
        if deadline <= time.monotonic():raise TimeoutError('MCP request budget already expired')
        self.send(message, timeout=deadline-time.monotonic(), cancelled=cancelled)
        while True:
            check_cancelled(cancelled)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('MCP request timed out')
            try:
                value = self.inbox.get(timeout=min(.1, remaining) if cancelled is not None else remaining)
            except queue.Empty as error:
                if cancelled is not None and time.monotonic() < deadline:
                    continue
                raise TimeoutError('MCP response deadline exceeded for ' + message['method']) from error
            if value is None:
                raise RuntimeError('MCP backend exited')
            check_cancelled(cancelled)
            if time.monotonic() >= deadline:
                raise TimeoutError('MCP response arrived after the operation deadline')
            if value.get('id') == message['id']:
                return value

    def close(self, force=False):
        if self.closed:
            return
        self.closed = True
        if force:
            stop(self.proc)
        try:
            self.proc.stdin.close()
        except OSError:
            pass
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            stop(self.proc)
        self.reader.join(timeout=1)
        self.proc.stdout.close()


class PersistentBackend:
    """Replace a failed backend or a backend bound to another index generation."""
    def __init__(self, factory, deadline_factory=False):
        self.factory = factory
        self.deadline_factory = deadline_factory
        self.backend = None
        self.key = None

    def call(self, key, message, deadline=None, cancelled=None):
        check_cancelled(cancelled)
        if self.backend is None or self.key != key:
            self.close()
            options = {'deadline': deadline} if self.deadline_factory else {}
            if cancelled is not None:options['cancelled'] = cancelled
            self.backend = self.factory(key, **options)
            self.key = key
        try:
            options = {'deadline': deadline} if deadline is not None else {}
            if cancelled is not None:options['cancelled'] = cancelled
            return self.backend.call(message, **options)
        except BaseException:
            self.close(force=cancelled is not None and cancelled.is_set())
            raise

    def close(self, force=False):
        if self.backend is not None:
            if force:self.backend.close(force=True)
            else:self.backend.close()
            self.backend = None
            self.key = None
