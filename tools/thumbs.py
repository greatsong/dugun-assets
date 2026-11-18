#!/usr/bin/env python3
"""갤러리(index.html)용 가벼운 미리보기를 만든다: thumbs/<id>.webp (긴 변 480px)
투명 배경 그림은 투명한 채로 둔다(갤러리가 바탕색을 깐다). 이미 있고 원본보다 새것이면 건너뛴다.
  python3 tools/thumbs.py          # 빠진 것 · 바뀐 것만
  python3 tools/thumbs.py --force  # 전부 다시
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import REPO, load, path_of

LONG = 480


def main():
    from PIL import Image
    force = "--force" in sys.argv
    out_dir = os.path.join(REPO, "thumbs")
    os.makedirs(out_dir, exist_ok=True)
    cat = load()
    keep, made = set(), 0
    for e in cat:
        if "w" not in (e.get("size") or {}): continue      # 소리(음악 · 효과음)는 미리보기 그림이 없다
        src = path_of(e)
        dst = os.path.join(out_dir, e["id"] + ".webp")
        keep.add(os.path.basename(dst))
        if not force and os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
            continue
        im = Image.open(src)
        im.load()
        alpha = im.mode in ("RGBA", "LA", "P")
        im = im.convert("RGBa" if alpha else "RGB")            # 투명 그림은 미리 곱한 알파로 줄여 가장자리 검은 테를 막는다
        s = LONG / max(im.size)
        if s < 1:
            im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
        if alpha:
            im = im.convert("RGBA")
        im.save(dst, "WEBP", quality=80, method=6)
        made += 1
    gone = [f for f in os.listdir(out_dir) if f.endswith(".webp") and f not in keep]
    for f in gone:
        os.remove(os.path.join(out_dir, f))
    total = sum(os.path.getsize(os.path.join(out_dir, f)) for f in os.listdir(out_dir))
    print(f"미리보기 {len(keep)}장 (새로 {made} · 지움 {len(gone)}) — thumbs/ {total // 1024} KB")


if __name__ == "__main__":
    main()
