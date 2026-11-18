#!/usr/bin/env python3
"""저장소 그림을 편 폴더로 복사하고, 그 편 요청서(assets.json)에 넣을 줄을 출력한다. 요청서 자체는 고치지 않는다.
  python3 tools/use.py bg_classroom_a prop_dice --to <주제>            # → kit/topics/<주제>/assets/<id>.<확장자>
  python3 tools/use.py bg_stage_gb --to <주제> --as bg_stage           # 편 코드가 쓰는 옛 이름으로 복사(id 하나일 때)
  python3 tools/use.py prop_dice --to /tmp/시험폴더                      # 주제 대신 폴더 경로도 된다
  옵션: --kit <kit 경로>(기본: DUGUN_KIT 또는 저장소 옆 기본 자리), --force(있는 파일 덮어쓰기)
"""
import argparse, json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import kit_dir, load, path_of, sha1

ap = argparse.ArgumentParser()
ap.add_argument("ids", nargs="+")
ap.add_argument("--to", required=True)
ap.add_argument("--as", dest="as_name")
ap.add_argument("--kit")
ap.add_argument("--force", action="store_true")
a = ap.parse_args()
if a.as_name and len(a.ids) != 1: sys.exit("--as 는 id 하나일 때만")

by = {e["id"]: e for e in load()}
bad = [i for i in a.ids if i not in by]
if bad: sys.exit("목록에 없는 id: " + " ".join(bad) + "  (찾기: python3 tools/find.py <낱말>)")

if os.path.isabs(a.to) or os.sep in a.to or a.to.startswith("."):
    dst_dir, topic = os.path.abspath(a.to), None
else:
    dst_dir, topic = os.path.join(kit_dir(a.kit), "topics", a.to, "assets"), a.to
os.makedirs(dst_dir, exist_ok=True)

lines = []
for i in a.ids:
    e = by[i]; src = path_of(e)
    if sha1(src) != e["sha1"]: sys.exit(f"{i}: 저장소 파일이 목록의 sha1과 다름 — 먼저 확인")
    name = (a.as_name or i) + os.path.splitext(src)[1]
    dst = os.path.join(dst_dir, name)
    if os.path.exists(dst) and not a.force and sha1(dst) != e["sha1"]:
        sys.exit(f"{dst} 에 다른 그림이 이미 있음 — --force 로 덮어쓰기")
    shutil.copy2(src, dst)
    print(f"복사 {i} → {dst}")
    kind = {"배경": "background"}.get(e["kind"], "prop")
    row = {"lib": i, "id": a.as_name or i, "kind": kind, "scene": "<장면>"}
    lines.append("  " + json.dumps(row, ensure_ascii=False))
print("\n요청서(assets.json)의 images에 넣을 줄 — 손으로 붙이고 scene을 채운다(이 도구는 요청서를 고치지 않음):")
print(",\n".join(lines))
print("\n※ 지금 공용 도구 assets.py는 'lib' 꼴을 아직 모른다(2차에서 맞춤). 그때까지 lint가 prompt 없음을 지적하면 메모로 남긴다.")
