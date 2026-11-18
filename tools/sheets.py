#!/usr/bin/env python3
"""종류별 미리보기 시트를 다시 그린다: sheets/<폴더>.jpg + 같은 것을 여러 번 그린 묶음만 모은 sheets/_variants.jpg
  python3 tools/sheets.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import FOLDER, REPO, load, sheet

cat = load()
for kind, folder in FOLDER.items():
    es = [e for e in cat if e["kind"] == kind]
    if not es: continue
    cols = 6 if kind == "배경" else 10
    out = sheet(es, os.path.join(REPO, "sheets", folder + ".jpg"), cols=cols, cell=260 if kind == "배경" else 200,
                title=f"{kind} {len(es)}장 — dugun-assets")
    print(out, os.path.getsize(out) // 1024, "KB")
groups = {}
for e in cat:
    if e.get("variant_of"): groups.setdefault(e["variant_of"], []).append(e)
es = [e for g in sorted(groups) for e in groups[g]]
out = sheet(es, os.path.join(REPO, "sheets", "_variants.jpg"), cols=6, cell=240,
            title=f"같은 것을 여러 번 그린 묶음 {len(groups)}개 · {len(es)}장 (variant_of 순서)")
print(out, os.path.getsize(out) // 1024, "KB")
