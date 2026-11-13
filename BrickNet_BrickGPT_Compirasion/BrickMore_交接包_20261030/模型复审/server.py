# -*- coding: utf-8 -*-
"""现有模型复审站。运行 python 模型复审/server.py，打开 http://127.0.0.1:8130/。"""
import json
import re
import sys
import threading
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ASSETS = ROOT / "最终展示" / "static"
MODELS = ROOT / "最终展示" / "models"
SAVE = ROOT / "picks_review.json"
LOCK = threading.Lock()
GROUPS = [("camera", 2, "相机", "结构关系"), ("car", 3, "汽车", "几何表面"),
          ("car", 4, "汽车", "比例"), ("car", 5, "汽车", "综合"),
          ("guitar", 1, "吉他", "物体识别"), ("piano", 5, "钢琴", "综合"),
          ("vessel", 1, "船", "物体识别")]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def catalog():
    display = ROOT / "最终展示_完成" / "static" / "curated.json"
    if not display.exists():
        display = ASSETS / "curated.json"
    current = read_json(display)
    original = {e["choice_id"]: e for e in read_json(ROOT / "资料" / "best_all.json")}
    verified = {e["id"]: e for e in read_json(ROOT / "资料" / "collab_verified.json")}
    cars = [e for e in current if e["category"] == "car" and e.get("level") is None]

    def normalize(e, is_current=False):
        e = dict(e)
        old = original.get(e["id"], {})
        e["prompt"] = e.get("prompt") or old.get("prompt") or ""
        e["prompt_zh"] = e.get("prompt_zh") or old.get("zh") or ""
        e["glb"] = e.get("glb") or e.get("raw_glb")
        e["current"] = is_current
        e["hint_level"] = e.get("level")
        hint = re.search(r"_L([1-5])_", e["id"])
        if hint:
            e["hint_level"] = int(hint.group(1))
        e["source_zh"] = e.get("source_zh") or "已有备选"
        return e

    groups = []
    for category, level, zh, level_name in GROUPS:
        key = f"{category}_L{level}"
        entries = [normalize(e, True) for e in current
                   if e["category"] == category and e.get("level") == level]
        if not entries:
            raise ValueError(f"当前展示缺少 {key}")
        if category == "camera":
            cid = "camera-L2V2"
            entries.append(normalize(dict(id=cid, category=category, level=level,
                source="judged", source_zh="原人工优选", glb=f"models/judged_{cid}_raw.glb",
                stitched_glb=f"models/judged_{cid}_st.glb")))
        elif category == "car":
            entries.extend(normalize(e) for e in cars)
        elif category == "piano":
            for cid in ("piano-L5V3", "piano-L5V4"):
                e = verified[cid]
                if e.get("status") not in ("retiled", "raw_ok"):
                    continue
                entries.append(normalize(dict(e, source_zh="同事 · 已验证备选",
                    glb=f"models/collab_{cid}_raw.glb", stitched_glb=f"models/collab_{cid}_st.glb")))
        for entry in entries:
            for field in ("glb", "stitched_glb"):
                rel = entry.get(field)
                if rel and not (ROOT / "最终展示" / rel).is_file():
                    raise ValueError(f"模型文件缺失: {rel}")
            # 原验证文件中的机器路径不进入浏览器或导出结果。
            for field in ("raw_glb", "stitched_ldr", "src_dir"):
                entry.pop(field, None)
        entries.sort(key=lambda e: (not e["current"], e["hint_level"] != level,
                                   e["hint_level"] is not None, e["id"]))
        groups.append(dict(key=key, category=category, level=level, name=zh,
            level_name=level_name, current_id=entries[0]["id"],
            criterion=entries[0]["prompt_zh"] or entries[0]["prompt"], candidates=entries))
    return dict(title="BrickMore · 模型复审", schema_version=1, groups=groups)


CATALOG = catalog()
BY_GROUP = {g["key"]: g for g in CATALOG["groups"]}


def empty_state():
    return dict(schema_version=1, revision=0, updated_at=None, decisions={})


def read_state():
    return read_json(SAVE) if SAVE.exists() else empty_state()


def validate_decisions(decisions):
    if not isinstance(decisions, dict) or set(decisions) - set(BY_GROUP):
        raise ValueError("包含未知的复审组")
    result = {}
    for key, decision in decisions.items():
        if not isinstance(decision, dict):
            raise ValueError("选择格式不正确")
        status = decision.get("status")
        cid = decision.get("candidate_id")
        if status not in ("selected", "regenerate", "pending"):
            raise ValueError("未知的选择状态")
        if status == "selected" and cid not in {e["id"] for e in BY_GROUP[key]["candidates"]}:
            raise ValueError(f"候选不属于 {key}")
        note = decision.get("note", "")
        if not isinstance(note, str) or len(note) > 4000:
            raise ValueError("备注最多 4000 字")
        result[key] = dict(status=status, candidate_id=cid if status == "selected" else None, note=note)
    return result


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(HERE / "static"), **kwargs)

    def log_message(self, fmt, *args):
        if len(args) > 1 and str(args[1]) not in ("200", "304"):
            super().log_message(fmt, *args)

    def send_json(self, value, status=200):
        data = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def serve_asset(self, base, relative):
        file = (base / relative).resolve()
        if not file.is_relative_to(base.resolve()) or not file.is_file():
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "model/gltf-binary" if file.suffix == ".glb" else self.guess_type(str(file)))
        self.send_header("Content-Length", str(file.stat().st_size))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        with file.open("rb") as stream:
            self.copyfile(stream, self.wfile)

    def do_GET(self):
        path = unquote(urlsplit(self.path).path)
        if path == "/api/catalog":
            return self.send_json(CATALOG)
        if path == "/api/review":
            with LOCK:
                return self.send_json(read_state())
        if path.startswith("/models/"):
            return self.serve_asset(MODELS, path[len("/models/"):])
        if path.startswith("/assets/"):
            return self.serve_asset(ASSETS, path[len("/assets/"):])
        return super().do_GET()

    def do_POST(self):
        if urlsplit(self.path).path != "/api/review":
            return self.send_error(404)
        # 本地网页只能从本站写入选择结果。
        origin = self.headers.get("Origin")
        if origin and origin != f"http://{self.headers.get('Host')}":
            return self.send_json(dict(error="请求来源不匹配"), 403)
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self.send_json(dict(error="需要 JSON 请求"), 415)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 100000:
                raise ValueError("请求大小不正确")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            decisions = validate_decisions(payload.get("decisions"))
            with LOCK:
                old = read_state()
                if payload.get("revision") != old["revision"]:
                    return self.send_json(dict(error="选择文件已在其他页面更新，请刷新后再试", state=old), 409)
                state = dict(schema_version=1, revision=old["revision"] + 1,
                    updated_at=datetime.now(timezone.utc).isoformat(), decisions=decisions)
                temp = SAVE.with_suffix(".json.tmp")
                temp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                temp.replace(SAVE)
            return self.send_json(state)
        except (ValueError, TypeError, AttributeError, KeyError) as error:
            return self.send_json(dict(error=str(error)), 400)
        except OSError:
            return self.send_json(dict(error="保存失败，请检查目录是否可写；可先导出 JSON 备份"), 500)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8130
    print(f"BrickMore 模型复审 → http://127.0.0.1:{port}/", flush=True)
    print(f"复审结果自动保存到: {SAVE}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
