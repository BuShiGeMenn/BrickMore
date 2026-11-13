# -*- coding: utf-8 -*-
"""合并第三轮、七组复审和五组重生成，生成独立交付目录。

python 工具/build_delivery_package.py
python 工具/build_delivery_package.py --pack-only
"""
import argparse
import csv
import hashlib
import json
import shutil
import struct
import zipfile
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
SOURCE_ZIP = ROOT / "重生成_5组_新提示词_20261107.zip"
OUT = ROOT / "BrickMore_汇总交付_20261107"
BASE = ROOT / "最终展示_完成"
ORIGINAL = ROOT / "最终展示"
ALLOWED = {(2, 4), (4, 2), (2, 6), (6, 2), (1, 2), (2, 1), (1, 4), (4, 1),
           (1, 6), (6, 1), (1, 8), (8, 1), (1, 1), (2, 2), (1, 3), (3, 1),
           (2, 3), (3, 2), (2, 8), (8, 2)}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def key(entry):
    return f"{entry['category']}_L{entry['level']}" if entry.get("level") is not None else None


def check_glb(data):
    assert len(data) >= 20
    magic, version, size = struct.unpack_from("<4sII", data)
    assert magic == b"glTF" and version == 2 and size == len(data), "GLB 头或长度错误"
    length, kind = struct.unpack_from("<II", data, 12)
    assert kind == 0x4E4F534A and 20 + length <= len(data)
    document = json.loads(data[20:20 + length])
    assert document.get("meshes"), "GLB 没有网格"
    return dict(meshes=len(document["meshes"]), bytes=len(data))


def cells(bricks, strict=True):
    result = {}
    for i, b in enumerate(bricks):
        assert all(isinstance(b[p], int) for p in ("h", "w", "x", "y", "z"))
        assert (b["h"], b["w"]) in ALLOWED
        assert 0 <= b["x"] < b["x"] + b["h"] <= 48
        assert 0 <= b["y"] < b["y"] + b["w"] <= 48 and 0 <= b["z"] < 48
        for x in range(b["x"], b["x"] + b["h"]):
            for y in range(b["y"], b["y"] + b["w"]):
                c = x, y, b["z"]
                if strict:
                    assert c not in result, f"重叠: {c}"
                result[c] = i
    return result


def geometry_check(model, raw, reported):
    bricks = model["bricks"]
    occupied = cells(bricks)
    assert set(occupied) == set(cells(raw["bricks"], strict=False)), "保形体素不一致"
    adjacency = [set() for _ in bricks]
    for (x, y, z), i in occupied.items():
        j = occupied.get((x, y, z + 1))
        if j is not None and i != j:
            adjacency[i].add(j)
            adjacency[j].add(i)
    visited = set()
    components = 0
    for i in range(len(bricks)):
        if i in visited:
            continue
        components += 1
        queue = [i]
        visited.add(i)
        while queue:
            for j in adjacency[queue.pop()]:
                if j not in visited:
                    visited.add(j)
                    queue.append(j)
    assert components == 1, f"凸点连通分量为 {components}"
    assert reported["brick_count"] == len(bricks) and reported["occupied_voxels"] == len(occupied)
    return dict(brick_count=len(bricks), occupied_voxels=len(occupied), overlap_voxels=0,
                out_of_bounds_bricks=0, stud_components=components, shape_preserved=True,
                physical_stability_tested=False)


def export_csv(path, rows):
    fields = ["category", "level", "id", "source", "source_zh", "visual_review",
              "glb", "stitched_glb", "prompt", "prompt_zh"]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def prepare_page(path, total):
    html = path.read_text(encoding="utf-8")
    html = html.replace("BrickMore-48 · 合格模型合集(判决最佳 + 第二轮 + 同事新尝试)", "BrickMore-48 · 汇总展示（复审与重生成）")
    html = html.replace("BrickMore-48 · 合格模型合集", "BrickMore-48 · 汇总展示")
    html = html.replace('每个"类×等级"下并列展示:', f"105 个正式组 · {total} 个模型 · 新增 5 组 6 个候选")
    html = html.replace('<span class="chip c-collab">同事新尝试(已验证)</span>',
        '<span class="chip c-collab">同事补充</span><span class="chip c-regen">本轮重生成 · 外形待复审</span>')
    html = html.replace("</style>", ".src.regen,.c-regen { color:#e9a0aa; border-color:#855461; } .pending-note { color:#e9a0aa; font-size:11px; margin:6px 0; } .downloads a { color:#a8cfe2; margin-right:12px; font-size:11px; } .view { position:relative; } .load-state { position:absolute; inset:0; display:grid; place-items:center; color:#a5adb8; font-size:11px; } body.big-open header,body.big-open main { visibility:hidden; }\n</style>")
    html = html.replace("function makeViewer(holder, item, big = false)", "function makeViewer(holder, item, big = false, initialKind = null)")
    html = html.replace("antialias: true });", "antialias: true, alpha: true });")
    html = html.replace("  renderer.setSize(W, H, false);", "  renderer.setSize(W, H, false);\n  renderer.setScissorTest(false); renderer.setClearColor(0x000000, 0); renderer.clear(); renderer.setScissorTest(true);")
    html = html.replace("    v.kind = kind;\n    const path = kind === 'raw' ? item.glb : item.stitched_glb;\n    if (!path) return;",
        "    const path = kind === 'raw' ? item.glb : item.stitched_glb;\n    if (!path) return;\n    v.kind = kind;\n    holder.dataset.state = 'loading';")
    html = html.replace("loader.load('/' + path, gltf => attach(big ? gltf.scene.clone() : gltf.scene),\n                undefined, e => console.error('GLB fail', path, e));",
        "loader.load('/' + path, gltf => { attach(big ? gltf.scene.clone() : gltf.scene); holder.dataset.state = 'ready'; holder.dataset.kind = kind; },\n                undefined, e => { holder.dataset.state = 'failed'; console.error('GLB fail', path, e); });")
    html = html.replace("v.load(item.glb ? 'raw' : 'stitched');", "v.load(initialKind || (item.glb ? 'raw' : 'stitched'));")
    html = html.replace("`${items[0].category} · ${lvlName(items[0].level)} — ${items.length} 个合格模型`", "`${items[0].category} · ${lvlName(items[0].level)} — ${items.length} 个模型`")
    html = html.replace("${items.length} 个合格模型", "${items.length} 个模型")
    html = html.replace("const [cls, txt] = item.source === 'judged' ? SRC_STYLE.judged", "const [cls, txt] = item.source === 'regenerated' ? ['regen', '本轮重生成'] : item.source === 'judged' ? SRC_STYLE.judged")
    html = html.replace("${item.status === 'retiled' ? '重铺验证' : item.status === 'raw_ok' ? '原生可拼' : ''}",
        "${item.visual_review === 'pending' ? '几何通过 · 外形待复审' : item.visual_review === 'user_selected' ? '用户复审选定' : item.status === 'retiled' ? '重铺验证' : item.status === 'raw_ok' ? '原生可拼' : ''}")
    html = html.replace("${item.stitched_glb ? '<button class=\"swap\">看重铺版</button>' : ''}",
        "${item.glb && item.stitched_glb ? '<button class=\"swap\">看重铺版</button>' : item.stitched_glb ? '<span class=\"badge\">仅重铺 GLB</span>' : ''}")
    html = html.replace("<div class=\"zh\">${item.prompt_zh || ''}</div>",
        "<div class=\"zh\">${item.prompt_zh || ''}</div>${item.visual_review === 'pending' ? '<div class=\"pending-note\">本轮新候选，造型待人工确认。</div>' : ''}${item.records ? `<div class=\"downloads\"><a href=\"/${item.records}/model.ldr\" download>LDR</a><a href=\"/${item.records}/model.txt\" download>排砖 TXT</a><a href=\"/${item.records}/validation.json\" download>检查记录</a></div>` : ''}")
    html = html.replace("onclick = () => openBig(item);", "onclick = () => openBig(item, v.kind);")
    html = html.replace("function openBig(item) {", "function openBig(item, kind) {")
    html = html.replace("bigV = makeViewer(bigDrag, item, true);", "document.body.classList.add('big-open');\n  bigV = makeViewer(bigDrag, item, true, kind);")
    html = html.replace("function closeBig() {", "function closeBig() {\n  document.body.classList.remove('big-open');")
    html = html.replace("bigV.controls.dispose(); bigV = null;", "bigV.controls.dispose(); bigV.scene.traverse(o => { if (o.isMesh) o.geometry.dispose(); }); bigV = null;")
    assert "holder.dataset.state = 'ready'" in html
    assert "item.glb && item.stitched_glb" in html
    path.write_text(html, encoding="utf-8")


def build():
    assert not OUT.exists(), f"目录已存在，请保留它或另行指定输出: {OUT}"
    stage = OUT.with_name(OUT.name + ".building")
    assert stage.resolve().parent == ROOT and OUT.resolve().parent == ROOT
    assert not stage.exists(), f"临时目录已存在: {stage}"
    selections = read_json(ROOT / "picks_round3.json")
    review = read_json(ROOT / "picks_review.json")
    initial = read_json(BASE / "static" / "curated.json")
    expected_round3 = {e["id"] for e in initial if e["source"] == "round3"}
    assert expected_round3 == {v for v in selections.values() if v}, "第三轮选择与现有展示不一致"
    assert all(d["status"] in ("selected", "regenerate") for d in review["decisions"].values())
    originals = {e["choice_id"]: e for e in read_json(ROOT / "资料" / "best_all.json")}
    verified = {e["id"]: e for e in read_json(ROOT / "资料" / "collab_verified.json")}
    input_hash = digest(SOURCE_ZIP.read_bytes())
    new_checks = []
    with zipfile.ZipFile(SOURCE_ZIP) as archive:
        assert archive.testzip() is None, "来源 ZIP CRC 检查失败"
        members = [i.filename for i in archive.infolist() if not i.is_dir()]
        prefix = members[0].split("/", 1)[0] + "/"
        assert all(n.startswith(prefix) and ".." not in PurePosixPath(n).parts for n in members)
        def source_bytes(rel):
            return archive.read(prefix + rel)
        def source_json(rel):
            return json.loads(source_bytes(rel))
        checksums = {}
        for line in source_bytes("checksums.sha256").decode("utf-8-sig").splitlines():
            if not line.strip():
                continue
            sha, rel = line.split(None, 1)
            rel = rel.lstrip(" *")
            assert digest(source_bytes(rel)) == sha, f"来源 SHA256 不一致: {rel}"
            checksums[rel] = sha
        assert {n[len(prefix):] for n in members} - {"checksums.sha256"} == set(checksums)
        manifest = source_json("manifest.json")
        attempts = source_json("all_attempts_manifest.json")
        provenance = source_json("provenance.json")
        prompts = {e["candidate_id"]: e for e in source_json("recommended_prompts.json")}
        regenerate = {g for g, d in review["decisions"].items() if d["status"] == "regenerate"}
        assert {e["group"] for e in manifest} == regenerate
        for g, cid in provenance["retained_groups"].items():
            assert review["decisions"][g]["candidate_id"] == cid
        for e in manifest:
            assert e["status"] == "geometry_passed_pending_visual_review"
            folder = e["folder"]
            assert e["prompt"] == source_json(folder + "/generation.json")["prompt"]
            assert e["prompt"] == prompts[e["source_candidate_id"]]["prompt"]
            result = geometry_check(source_json(folder + "/model.json"), source_json(folder + "/raw_geometry.json"), source_json(folder + "/validation.json"))
            check_glb(source_bytes(folder + "/model.glb"))
            new_checks.append(dict(id=e["id"], group=e["group"], **result))

        replaced = set(review["decisions"])
        selected_ids = {d["candidate_id"] for d in review["decisions"].values() if d["status"] == "selected"}
        final = [dict(e) for e in initial if key(e) not in replaced and not (e.get("level") is None and e["id"] in selected_ids)]
        changes = []
        for g, d in review["decisions"].items():
            before = [e["id"] for e in initial if key(e) == g]
            if d["status"] == "selected":
                cid = d["candidate_id"]
                source = next((dict(e) for e in initial if e["id"] == cid), None)
                if source is None:
                    source = dict(verified[cid], glb=f"models/collab_{cid}_raw.glb", stitched_glb=f"models/collab_{cid}_st.glb", source_zh="同事备选")
                for field in ("raw_glb", "stitched_ldr", "src_dir", "has_raw_glb"):
                    source.pop(field, None)
                source["original_level"] = source.get("level")
                source["category"], level = g.rsplit("_L", 1)
                source["level"] = int(level)
                source["original_source_zh"] = source.get("source_zh")
                source["source_zh"] = "本轮复审选定"
                source["visual_review"] = "user_selected"
                final.append(source)
                after = [cid]
            else:
                after = []
                for e in manifest:
                    if e["group"] != g:
                        continue
                    folder = "models/regen/" + e["id"]
                    final.append(dict(id=e["id"], category=e["category"], level=e["level"],
                        source="regenerated", source_zh="本轮重生成 · " + ("采样备选" if e["generation"]["options"]["do_sample"] else "主候选"),
                        status="retiled", visual_review="pending", prompt=e["prompt"],
                        prompt_zh=prompts[e["source_candidate_id"]].get("prompt_zh", ""), glb=None,
                        stitched_glb=folder + "/model.glb", records=folder, validation=e["validation"],
                        seed=e["seed"], generation_revision=provenance["revision"],
                        source_prompt_id=e["source_candidate_id"]))
                    after.append(e["id"])
            changes.append(dict(group=g, before=before, after=after,
                action="用户复审替换" if d["status"] == "selected" else "重生成候选替换", visual_review="user_selected" if d["status"] == "selected" else "pending"))
        for e in final:
            old = originals.get(e["id"], {})
            e["prompt"] = e.get("prompt") or old.get("prompt") or ""
            e["prompt_zh"] = e.get("prompt_zh") or old.get("zh") or ""
        category_order = {c: n for n, c in enumerate(dict.fromkeys(e["category"] for e in initial))}
        final.sort(key=lambda e: (category_order[e["category"]], e["level"] if e.get("level") is not None else 99, e["source"] == "regenerated" and "S104" in e["id"], e["id"]))
        assert len({e["id"] for e in final}) == len(final), "重复模型 ID"
        formal = {(e["category"], e["level"]) for e in final if e.get("level") is not None}
        assert formal == {(c, l) for c in category_order for l in range(1, 6)}
        assert len(formal) == 105
        stage.mkdir()
        display = stage / "展示"
        display.mkdir()
        shutil.copytree(BASE / "static", display / "static")
        shutil.copy2(BASE / "server.py", display / "server.py")
        server = (display / "server.py").read_text(encoding="utf-8")
        server = server.replace("self.send_header('Content-Type', 'model/gltf-binary')", "self.send_header('Content-Type', 'model/gltf-binary' if f.suffix == '.glb' else self.guess_type(str(f)))")
        server = server.replace("else 8126", "else 8140").replace("127.0.0.1:8126", "127.0.0.1:8140")
        (display / "server.py").write_text(server, encoding="utf-8")
        for e in final:
            if e["source"] == "regenerated":
                incoming = next(m for m in manifest if m["id"] == e["id"])
                source_prefix = incoming["folder"] + "/"
                target = display / e["records"]
                target.mkdir(parents=True)
                for name in members:
                    rel = name[len(prefix):]
                    if rel.startswith(source_prefix):
                        dest = target / rel[len(source_prefix):]
                        assert dest.resolve().is_relative_to(target.resolve())
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(archive.read(name))
            else:
                for field in ("glb", "stitched_glb"):
                    rel = e.get(field)
                    if rel:
                        source = BASE / rel
                        if not source.exists():
                            source = ORIGINAL / rel
                        assert source.is_file(), source
                        target = display / rel
                        target.parent.mkdir(parents=True, exist_ok=True)
                        if not target.exists():
                            shutil.copy2(source, target)
        dump(display / "static" / "curated.json", final)
        prepare_page(display / "static" / "index.html", len(final))
        records = stage / "资料与记录"
        records.mkdir()
        for rel in ("picks_round3.json", "picks_review.json", "资料/best_all.json", "资料/best_all.md", "资料/collab_verified.json"):
            shutil.copy2(ROOT / rel, records / Path(rel).name)
        shutil.copy2(SOURCE_ZIP, records / SOURCE_ZIP.name)
        for name in ("manifest.json", "all_attempts_manifest.json", "provenance.json", "artifact_audit.json", "recommended_prompts.json", "recommended_prompts.txt"):
            (records / name).write_bytes(source_bytes(name))
        shutil.copy2(ROOT / "工具" / "build_delivery_package.py", records / "build_delivery_package.py")
        dump(stage / "选择与替换记录.json", dict(round3=selections, review=review, changes=changes, regenerated_candidates=[e["id"] for e in manifest]))
        export_csv(stage / "模型总清单.csv", final)
        export_csv(stage / "本轮新增与替换清单.csv", [e for e in final if key(e) in replaced])
        refs = {e[f] for e in final for f in ("glb", "stitched_glb") if e.get(f)}
        for rel in refs:
            check_glb((display / rel).read_bytes())
        counts = Counter(e["source"] for e in final)
        result = dict(created_at=datetime.now(timezone(timedelta(hours=8))).isoformat(),
            source_zip=SOURCE_ZIP.name, source_zip_sha256=input_hash, source_zip_crc_passed=True,
            source_checksum_files_verified=len(checksums), formal_groups=len(formal), categories=len(category_order),
            model_count=len(final), ungraded_models=sum(e.get("level") is None for e in final),
            referenced_glbs=len(refs), source_counts=dict(counts), regenerated_groups=5, regenerated_candidates=len(manifest),
            archived_rejected_attempts=[dict(id=e["id"], status=e["status"], review=e.get("visual_review")) for e in attempts if e["id"] not in {m["id"] for m in manifest}],
            duplicate_raw_output=source_json("artifact_audit.json")["identical_raw_output_groups"],
            independent_geometry_checks=new_checks, browser_verification=dict(status="pending"))
        dump(stage / "验收报告.json", result)
        date = "2026-11-07"
        rows = ["# BrickMore-48 汇总交付", "", f"整理日期：{date}。来源：`{SOURCE_ZIP.name}`。", "",
            f"本包包含 **21 类 × 5 等级 = 105 个正式组，{len(final)} 个展示模型**，另有 {result['ungraded_models']} 个未归档等级的汽车试作（已计入模型总数）。",
            "新增五组为 6 个候选；几何与凸点连通通过，外形状态沿用生成包的“待人工复审”。本包未把它们标为人工验收通过。", "",
            "## 本轮更新", "", "| 组别 | 本次采用或保留的候选 | 状态 |", "|---|---|---|"]
        for change in changes:
            rows.append(f"| {change['group']} | {' / '.join(change['after'])} | {'用户已选定' if change['visual_review'] == 'user_selected' else '几何通过，外形待复审'} |")
        rows.extend(["", "原第三轮篮子、长凳、马克杯、桌子七组的 picks 保持一致。已被复审替换的旧模型不进入主展示；选中的汽车 L3 从未归档汽车试作移入 L3，不重复列出。", "",
            "## 文件与打开方法", "", "- `展示/`：独立的离线展示站与页面实际引用的模型。", "- `模型总清单.csv`：全部展示条目，包含英文及中文提示词、模型路径、来源与复审状态。", "- `本轮新增与替换清单.csv`、`选择与替换记录.json`：本轮七组的更新记录。", "- `资料与记录/`：原选择文件、生成清单、提示词、模型版本及完整原始生成 ZIP。", "- 新候选的 GLB、LDR、TXT、原始输出、几何 JSON、报告和图片位于 `展示/models/regen/<模型 ID>/`。", "- 原包中已淘汰的 2 次尝试保存在原始生成 ZIP 中，不列入主展示。", "", "在本目录运行：", "", "```powershell", "python .\\展示\\server.py 8140", "```", "", "浏览器打开 http://127.0.0.1:8140/ 。服务和页面仅使用 Python 标准库与包内静态资源。", "",
            "## 核验与已知情况", "", f"- 原始 ZIP 的 CRC 与 {len(checksums)} 个文件的 SHA-256 校验通过。", f"- {len(refs)} 个页面引用的 GLB 头、长度及网格信息核验通过。", "- 6 个新候选独立复核：合法砖型、48³ 网格边界、零重叠、单一凸点连通、重铺前后体素并集相同。", "- 汽车 L4 主候选 `car_L4_P1_G` 与汽车 L5 主候选 `car_L5_P1_G` 的原始输出相同；L5 另保留 `car_L5_P1_S104` 采样备选。", "- 新模型 GLB 为重铺后的几何；页面不将其误标为原版。原始排砖、TXT 与 LDR 仍随包保留。", "- 黄色为统一显示色，生成模型不包含提示词描述的部件配色。", "- 新包采用原 630 模型管线的 YX 尺寸约定；来源声明尚未对照训练转换器核验。物理稳定性未测试。", "- 浏览器运行检查结果见 `验收报告.json`。", ""])
        (stage / "交付总结.md").write_text("\n".join(rows), encoding="utf-8")
        (stage / "启动展示.cmd").write_text('@echo off\r\nchcp 65001 >nul\r\ncd /d "%~dp0"\r\npython 展示\\server.py 8140\r\npause\r\n', encoding="utf-8")
    assert digest(SOURCE_ZIP.read_bytes()) == input_hash, "来源 ZIP 在整理期间发生变化"
    stage.rename(OUT)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def package():
    assert OUT.is_dir() and OUT.resolve().parent == ROOT
    archive_path = OUT.with_suffix(".zip")
    assert not archive_path.exists(), f"压缩包已存在: {archive_path}"
    sums = OUT / "checksums.sha256"
    files = sorted(p for p in OUT.rglob("*") if p.is_file() and p != sums)
    sums.write_text("\n".join(f"{digest(p.read_bytes())}  {p.relative_to(OUT).as_posix()}" for p in files) + "\n", encoding="utf-8")
    files.append(sums)
    with zipfile.ZipFile(archive_path, "x", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in files:
            archive.write(path, path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        for path in files:
            assert digest(archive.read(path.relative_to(ROOT).as_posix())) == digest(path.read_bytes())
    sha = digest(archive_path.read_bytes())
    archive_path.with_suffix(".zip.sha256").write_text(f"{sha}  {archive_path.name}\n", encoding="utf-8")
    print(json.dumps(dict(archive=str(archive_path), archive_bytes=archive_path.stat().st_size,
        files=len(files), sha256=sha, integrity="passed"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack-only", action="store_true")
    args = parser.parse_args()
    package() if args.pack_only else build()
