#!/usr/bin/env python3
"""낱말로 그림 찾기 — 우리말 이름 · 태그 · id · 프롬프트에서 찾아 후보 표와 임시 미리보기 시트를 낸다.
  python3 tools/find.py 얼음 밤하늘
  python3 tools/find.py 교실 --kind 배경 --top 12
  python3 tools/find.py stage --sheet /tmp/stage.jpg
낱말이 여럿이면 많이 맞는 그림이 위로 온다(태그 · 이름 3점, id 2점, 프롬프트 1점).
"""
import argparse, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import load, sheet

ap = argparse.ArgumentParser()
ap.add_argument("words", nargs="+")
ap.add_argument("--kind", help="배경 · 소품 · 재질 · 효과 · 캐릭터 · 아이콘")
ap.add_argument("--top", type=int, default=20)
ap.add_argument("--sheet", help="시트 저장 자리(기본: 임시 폴더)")
ap.add_argument("--no-sheet", action="store_true")
a = ap.parse_args()

hits = []
for e in load():
    if a.kind and e["kind"] != a.kind: continue
    tags = " ".join(e["tags"]) + " " + e["title"] + " " + e.get("variant_of", "")
    score, matched = 0, 0
    for w in a.words:
        wl = w.lower(); s = 0
        if wl in tags.lower(): s += 3
        if wl in e["id"].lower() or any(wl in x.lower() for x in e.get("aliases", [])): s += 2
        if wl in e["prompt"].lower(): s += 1
        score += s; matched += s > 0
    if score: hits.append((matched, score, e))
hits.sort(key=lambda h: (-h[0], -h[1], h[2]["id"]))
hits = hits[: a.top]
if not hits:
    print("찾은 그림 없음:", " ".join(a.words)); sys.exit(1)
print(f"{'점수':>4}  {'id':34s} {'종류':4s} {'우리말 이름':28s} 파일")
for m, s, e in hits:
    print(f"{s:>4}  {e['id']:34s} {e['kind']:4s} {e['title'][:28]:28s} {e['file']}")
if not a.no_sheet:
    out = a.sheet or os.path.join(tempfile.gettempdir(), "dugun_find_" + "_".join(a.words)[:40] + ".jpg")
    if sheet([h[2] for h in hits], out, cols=5, cell=220, title="찾기: " + " ".join(a.words)):
        print("미리보기 시트:", out)
print("편 폴더로 가져오기: python3 tools/use.py <id …> --to <주제>")
