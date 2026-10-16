"""Bundled helper, build-profile and evidence regressions; no live Go/index runs."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import go_mcp
import inspect_go
import package_map
from resource_guard import run


class AnalysisHelperTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        (self.root / "go.mod").write_text("module example.test/project\n")
        (self.root / "sample.go").write_text("package sample\ntype Value struct{}\n")

    def test_profiles_ignore_inherited_workspace_and_cgo(self):
        with patch.dict(os.environ, {"GOWORK": str(self.root / "parent.work"), "CGO_ENABLED": "1", "GOFLAGS": "-tags=inherited"}):
            for platform in ("windows/amd64", "android/arm64", "linux/amd64"):
                env = package_map.build_environment(platform, "selected")
                self.assertEqual(env["GOWORK"], "off")
                self.assertEqual(env["CGO_ENABLED"], "0")
                self.assertEqual(env["GOFLAGS"], "-mod=readonly -tags=selected")
                self.assertEqual(env["GOOS"] + "/" + env["GOARCH"], platform)
        with self.assertRaises(ValueError):
            package_map.build_environment("darwin/arm64")

    def test_fingerprint_covers_go_workspace_and_ignores_documents(self):
        before = package_map.source_fingerprint(self.root)
        (self.root / "README.md").write_text("documentation")
        self.assertEqual(before, package_map.source_fingerprint(self.root))
        (self.root / "go.work").write_text("use .")
        self.assertNotEqual(before, package_map.source_fingerprint(self.root))
        before = package_map.source_fingerprint(self.root)
        (self.root / "sample.go").write_text("package sample\ntype Other struct{}\n")
        self.assertNotEqual(before, package_map.source_fingerprint(self.root))

    def test_parse_packages_keeps_test_edges_without_synthetic_packages(self):
        data = {"ImportPath": "example/p", "Name": "p", "Imports": ["example/api"],
                "TestImports": ["example/test"], "XTestImports": ["example/xtest"]}
        packages = package_map.parse_packages(json.dumps(data) + "\n" + json.dumps({**data, "ForTest": "example/p"}))
        self.assertEqual(len(packages), 1)
        reports = list(package_map.impact_reports({"builds": [{"platform": "linux/amd64", "packages": packages}]}, "example/test"))
        self.assertEqual(reports[0]["direct_test"], ["example/p"])
        self.assertEqual(reports[0]["direct_production"], [])
        self.assertFalse(reports[0]["package_present"])

    def test_package_map_rejects_reuse_for_another_profile_or_tags(self):
        output = self.root / "map.json"
        data = {"source_sha": "head", "source_fingerprint": package_map.source_fingerprint(self.root),
                "source_cwd": str(self.root), "tags": "", "gowork": "off",
                "builds": [{"platform": "linux/amd64", "packages": []}]}
        output.write_text(json.dumps(data))
        with patch.object(package_map, "git", return_value="head"), patch.object(package_map, "run") as runner:
            with self.assertRaisesRegex(RuntimeError, "STALE"):
                package_map.main(["--repo", str(self.root), "--out", str(output), "--impact", "p"])
            with self.assertRaisesRegex(RuntimeError, "STALE"):
                package_map.main(["--repo", str(self.root), "--out", str(output), "--impact", "p", "--platforms", "linux/amd64", "--tags", "other"])
            runner.assert_not_called()

    def test_package_extraction_uses_guard_and_refuses_changed_source(self):
        output = self.root / "map.json"
        def execute(*args, **kwargs):
            self.assertEqual(kwargs["env"]["GOWORK"], "off")
            self.assertEqual(kwargs["transient"], self.root / ".local/host/transient")
            (self.root / "sample.go").write_text("package changed")
            return subprocess.CompletedProcess(args[0], 0, json.dumps({"ImportPath": "example/p", "Name": "p"}), "")
        with patch.object(package_map, "git", return_value="head"), patch.object(package_map, "run", side_effect=execute), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "Source changed"):
                package_map.main(["--repo", str(self.root), "--out", str(output)])
        self.assertFalse(output.exists())

    def test_reference_normalization_is_method_and_version_specific(self):
        text = "The object has 1 references\nLocated in the file: sample.go\nThe reference is located on line 0, which has content type Value struct{}"
        message = {"result": {"content": [{"type": "text", "text": text}]}}
        self.assertEqual(go_mcp.normalize(message, "go_file_context")["result"]["content"][0]["text"], text)
        normalized = go_mcp.normalize(message, "go_symbol_references")
        self.assertEqual(inspect_go.parse_references(normalized), [{"file": "sample.go", "line": 1}])
        binary = self.root / "gopls"
        binary.touch()
        with patch.object(go_mcp, "run", return_value=subprocess.CompletedProcess([], 0, "golang.org/x/tools/gopls v0.24.0\n")), patch.object(go_mcp, "Relay") as relay:
            with self.assertRaisesRegex(RuntimeError, "v0.23.0"):
                go_mcp.main(["--binary", str(binary), "--repo", str(self.root)])
            relay.assert_not_called()

    def test_direct_adapter_disables_foreign_workspace_and_preserves_build_environment(self):
        binary = self.root / 'gopls'
        binary.touch()
        selected = {'GOWORK': str(self.root / 'foreign.work'), 'GOOS': 'android',
                    'GOARCH': 'arm64', 'CGO_ENABLED': '0', 'GOFLAGS': '-tags=selected'}
        with patch.dict(os.environ, selected), \
             patch.object(go_mcp, 'run', return_value=subprocess.CompletedProcess([], 0, 'golang.org/x/tools/gopls v0.23.0\n')) as runner, \
             patch.object(go_mcp, 'Relay') as relay, \
             patch.object(go_mcp.sys, 'stdin'), patch.object(go_mcp.sys, 'stdout'):
            self.assertEqual(go_mcp.main(['--binary', str(binary), '--repo', str(self.root)]), 0)
            version_env = runner.call_args.kwargs['env']
            relay_env = relay.call_args.kwargs['env']
            self.assertEqual(version_env['GOWORK'], 'off')
            self.assertEqual(version_env, relay_env)
            for key in ('GOOS', 'GOARCH', 'CGO_ENABLED', 'GOFLAGS'):
                self.assertEqual(relay_env[key], selected[key])
            relay.return_value.serve.assert_called_once_with()

    def test_workspace_and_partial_reference_results_remain_unknown(self):
        def workspace(path):
            return {"result": {"content": [{"type": "text", "text": "Workspace: " + path}]}}
        self.assertTrue(inspect_go.workspace_matches(workspace(str(self.root)), self.root))
        self.assertFalse(inspect_go.workspace_matches(workspace(str(self.root) + "-other"), self.root))
        self.assertFalse(inspect_go.workspace_matches(workspace("unreported"), self.root))
        with self.assertRaisesRegex(RuntimeError, "not fully parsed"):
            inspect_go.parse_references({"result": {"content": [{"type": "text", "text": "The object has 2 references"}]}})

    def test_symbol_chain_is_bundled_and_environment_matches_receipt(self):
        tools = self.root / "tools"
        (tools / "bin").mkdir(parents=True)
        for name in ("gopls", "ast-grep"):
            (tools / "bin" / (name + (".exe" if os.name == "nt" else ""))).touch()
        out = self.root / "inspection"
        commands = []
        def execute(command, **kwargs):
            commands.append(command)
            self.assertEqual(kwargs["env"]["CGO_ENABLED"], "0")
            self.assertEqual(kwargs["env"]["GOWORK"], "off")
            if command[0] == sys.executable:
                self.assertEqual(Path(command[1]).parent, Path(inspect_go.__file__).parent)
                tail = command[command.index("--args") + 1:]
                self.assertEqual(Path(tail[0]).parent, Path(inspect_go.__file__).parent)
                raw = out / "raw"
                raw.mkdir()
                texts = ["Workspace: " + str(self.root), "The object has 1 references\nLocated in the file: sample.go\nThe reference is located on line 2, which has content type Value struct{}", "context"]
                for index, (name, text) in enumerate(zip(("go_workspace", "go_symbol_references", "go_file_context"), texts)):
                    (raw / (str(index) + "-" + name + ".json")).write_text(json.dumps({"result": {"content": [{"type": "text", "text": text}]}}))
            return subprocess.CompletedProcess(command, 0, "[]", "")
        with patch.object(inspect_go, "git", return_value="head"), patch.object(inspect_go, "run", side_effect=execute), contextlib.redirect_stdout(io.StringIO()):
            result = inspect_go.main(["--repo", str(self.root), "--tools", str(tools), "--file", "sample.go", "--symbol", "Value", "--platform", "linux/amd64", "--tags", "custom", "--out", str(out)])
        self.assertEqual(result, 0)
        report = json.loads((out / "inspection.json").read_text())
        self.assertEqual(report["build_environment"]["GOFLAGS"], "-mod=readonly -tags=custom")
        self.assertEqual(report["semantic_references"]["locations"][0]["line"], 2)
        self.assertTrue(report["workspace_verified"])
        self.assertEqual(len(commands), 2)

    def test_probe_captures_real_stdio_and_backend_error(self):
        server = self.root / "server.py"
        server.write_text('''import json,sys
for line in sys.stdin:
 message=json.loads(line)
 if 'id' not in message:continue
 if message['method']=='tools/call':result={'isError':True,'content':[{'type':'text','text':'bounded failure'}]}
 elif message['method']=='tools/list':result={'tools':[]}
 else:result={'serverInfo':{'name':'fixture'}}
 print(json.dumps({'jsonrpc':'2.0','id':message['id'],'result':result}),flush=True)
''')
        calls = self.root / "calls.json"
        calls.write_text(json.dumps([{"name": "fixture", "arguments": {}}]))
        output = self.root / "probe"
        command = [sys.executable, str(Path(__file__).parent / "mcp_probe.py"), "--exe", sys.executable,
            "--cwd", str(self.root), "--out", str(output), "--calls", str(calls), "--timeout", "3", "--args", str(server), "--backend-option"]
        result = run(command, transient=self.root / "transient", capture_output=True, text=True, encoding="utf-8", timeout=15)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads((output / "initialize.json").read_text())["result"]["serverInfo"]["name"], "fixture")
        self.assertTrue(json.loads((output / "0-fixture.json").read_text())["result"]["isError"])


if __name__ == "__main__":
    unittest.main()
