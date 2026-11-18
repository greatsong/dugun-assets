#!/usr/bin/env python3
"""catalog.json → catalog.csv (엑셀에서 바로 열리게 UTF-8 BOM)
  python3 tools/to_csv.py
"""
import csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import REPO, load

COLS = [("id", "id"), ("file", "파일"), ("kind", "종류"), ("title", "이름"), ("tags", "찾는 낱말"),
        ("w", "가로"), ("h", "세로"), ("bytes", "용량(바이트)"), ("tool", "그린 도구"), ("made", "만든 날"),
        ("from_topic", "처음 그린 영상"), ("used_in", "쓰인 영상"), ("variant_of", "같은 그림 묶음"),
        ("sha1", "sha1"), ("prompt", "프롬프트"), ("note", "참고")]


def main():
    out = os.path.join(REPO, "catalog.csv")
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow([k for _, k in COLS])
        for e in load():
            row = dict(e, w=e["size"]["w"], h=e["size"]["h"], bytes=e["size"]["bytes"])
            w.writerow(["; ".join(row.get(c) or []) if isinstance(row.get(c), list) else row.get(c, "") for c, _ in COLS])
    print(out)


if __name__ == "__main__":
    main()
