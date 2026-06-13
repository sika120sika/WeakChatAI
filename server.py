#!/usr/bin/env python3
"""CodeChat Agent Server — ローカルツール実行ブリッジ
使い方: python server.py
"""

import fnmatch
import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 3000
WORKING_DIR = None


# ── セキュリティ: 作業ディレクトリ外へのアクセスを禁止 ──────────────────
def _safe_path(rel):
    if not WORKING_DIR:
        raise ValueError("作業ディレクトリが未設定です。ブラウザで設定してください。")
    full = os.path.realpath(os.path.join(WORKING_DIR, rel))
    base = os.path.realpath(WORKING_DIR)
    if full != base and not full.startswith(base + os.sep):
        raise ValueError(f"作業ディレクトリ外へのアクセスは禁止されています: {rel}")
    return full


# ── ツール実装 ───────────────────────────────────────────────────────────

def tool_read_file(args):
    path = _safe_path(args["path"])
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            content = f.read()
        return {"content": content, "chars": len(content), "path": args["path"]}
    except FileNotFoundError:
        return {"error": f"ファイルが見つかりません: {args['path']}"}
    except IsADirectoryError:
        return {"error": f"ディレクトリです（ファイルを指定してください）: {args['path']}"}


def tool_write_file(args):
    path = _safe_path(args["path"])
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(args["content"])
    return {"ok": True, "path": args["path"], "bytes": len(args["content"].encode())}


def tool_list_dir(args):
    rel = args.get("path", ".")
    path = _safe_path(rel)
    try:
        entries = []
        for name in sorted(os.listdir(path)):
            full = os.path.join(path, name)
            entry = {"name": name, "type": "dir" if os.path.isdir(full) else "file"}
            if entry["type"] == "file":
                entry["size"] = os.path.getsize(full)
            entries.append(entry)
        return {"entries": entries, "path": rel}
    except FileNotFoundError:
        return {"error": f"ディレクトリが見つかりません: {rel}"}


def tool_run_command(args):
    # 承認はブラウザ側で取得済み。サーバーは実行するだけ。
    if not WORKING_DIR:
        return {"error": "作業ディレクトリが未設定です"}
    try:
        result = subprocess.run(
            args["command"],
            cwd=WORKING_DIR,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="replace",
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": "タイムアウト (30秒)", "returncode": -1}
    except Exception as e:
        return {"error": str(e), "returncode": -1}


def tool_search_content(args):
    query = args["query"].lower()
    base = _safe_path(args.get("path", "."))
    CODE_EXTS = {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".cs",
        ".cpp", ".c", ".h", ".html", ".css", ".json", ".md", ".yaml", ".yml",
        ".sh", ".toml", ".rb", ".php", ".kt", ".swift", ".dart", ".lua",
    }
    results = []
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS]
        for fname in files:
            if os.path.splitext(fname)[1].lower() not in CODE_EXTS:
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if query in line.lower():
                            results.append({
                                "file": os.path.relpath(fpath, WORKING_DIR),
                                "line": i,
                                "content": line.rstrip(),
                            })
                            if len(results) >= 50:
                                return {"results": results, "truncated": True}
            except OSError:
                pass
    return {"results": results}


SKIP_DIRS = {
    "node_modules", "__pycache__", ".git", ".venv", "venv",
    "dist", "build", ".next", ".idea", ".vs", "out",
    # C# / .NET
    "bin", "obj", ".mono",
    # Godot
    "export", ".godot",
    # その他ビルド成果物
    "cache", ".cache", "tmp", ".tmp",
}

# get_tree でスキップするバイナリ・自動生成ファイルの拡張子
TREE_SKIP_EXTS = {
    ".import", ".uid",                                          # Godot 自動生成
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tga",  # 画像
    ".wav", ".mp3", ".ogg", ".flac",                           # 音声
    ".ttf", ".otf", ".woff", ".woff2",                         # フォント
    ".zip", ".tar", ".gz", ".7z", ".rar",                      # アーカイブ
    ".exe", ".dll", ".so", ".a", ".lib", ".pdb",               # バイナリ
    ".blend", ".fbx", ".obj", ".gltf", ".glb",                 # 3D アセット
}


def tool_get_tree(args):
    rel  = args.get("path", ".")
    base = _safe_path(rel)
    max_depth = min(int(args.get("max_depth", 4)), 6)
    MAX_LINES = 800

    lines = []

    def walk(path, prefix="", depth=0):
        if depth > max_depth or len(lines) >= MAX_LINES:
            return
        try:
            entries = sorted(os.listdir(path))
        except PermissionError:
            return
        dirs  = [e for e in entries if os.path.isdir(os.path.join(path, e))
                 and e not in SKIP_DIRS and not e.startswith(".")]
        files = [e for e in entries
                 if not os.path.isdir(os.path.join(path, e))
                 and os.path.splitext(e)[1].lower() not in TREE_SKIP_EXTS]
        items = dirs + files
        for i, name in enumerate(items):
            if len(lines) >= MAX_LINES:
                lines.append(prefix + "└── ... (省略)")
                return
            connector = "└── " if i == len(items) - 1 else "├── "
            lines.append(prefix + connector + name)
            if name in dirs:
                ext = "    " if i == len(items) - 1 else "│   "
                walk(os.path.join(path, name), prefix + ext, depth + 1)

    walk(base)
    return {"tree": "\n".join(lines), "root": os.path.basename(base) or base}


def tool_find_files(args):
    pattern  = args.get("pattern", "*")
    rel_path = args.get("path", ".")
    base     = _safe_path(rel_path)

    results = []
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for fname in files:
            if fnmatch.fnmatch(fname.lower(), pattern.lower()):
                fpath = os.path.join(root, fname)
                results.append(os.path.relpath(fpath, WORKING_DIR).replace("\\", "/"))
        if len(results) >= 200:
            break

    results.sort()
    return {"files": results[:200], "count": len(results), "truncated": len(results) >= 200}


TOOL_HANDLERS = {
    "read_file":      tool_read_file,
    "write_file":     tool_write_file,
    "list_dir":       tool_list_dir,
    "run_command":    tool_run_command,
    "search_content": tool_search_content,
    "get_tree":       tool_get_tree,
    "find_files":     tool_find_files,
}


# ── HTTP サーバー ────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"  [{args[1]}] {args[0]}")

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def _read_body(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n)) if n else {}

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/ping":
            self._send_json({"ok": True, "workdir": WORKING_DIR})
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        global WORKING_DIR
        body = self._read_body()

        if self.path == "/set_workdir":
            path = body.get("path", "").strip()
            if os.path.isdir(path):
                WORKING_DIR = path
                print(f"  作業ディレクトリ設定 → {WORKING_DIR}")
                self._send_json({"ok": True, "path": WORKING_DIR})
            else:
                self._send_json({"error": f"ディレクトリが存在しません: {path}"}, 400)
            return

        for name, handler in TOOL_HANDLERS.items():
            if self.path == f"/tool/{name}":
                try:
                    result = handler(body)
                except ValueError as e:
                    result = {"error": str(e)}
                except Exception as e:
                    result = {"error": f"サーバーエラー: {e}"}
                self._send_json(result)
                return

        self._send_json({"error": "unknown endpoint"}, 404)


if __name__ == "__main__":
    print("=" * 52)
    print("  CodeChat Agent Server")
    print(f"  listening → http://localhost:{PORT}")
    print("  Ctrl+C で終了")
    print("=" * 52)
    HTTPServer(("localhost", PORT), Handler).serve_forever()
