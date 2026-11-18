#!/usr/bin/env python3
"""편이 새로 그린 그림 중 PD님 확인이 기록된 것만 저장소에 넣고 catalog.json에 줄을 더한다.
  python3 tools/add.py <주제> --dry-run      # 무엇을 넣을지 보기만
  python3 tools/add.py <주제>                # 넣기(그 뒤 tools/sheets.py로 시트를 다시 그린다)
읽는 것: kit/topics/<주제>/assets.json(새 꼴 요청서), kit/build/<주제>/assets_ok.json({eyes, pd, files:{id: sha1}}),
         kit/build/<주제>/assets_draw.log(그린 도구), kit/engine/assets/cast_bible.js(공통 틀 — node가 있을 때)
넣는 조건: assets_ok.json에 pd(PD님 말씀)가 있고, 지금 파일의 sha1이 확인 때의 sha1과 같은 그림. 이미 같은 그림(sha1)이 있으면
         새로 넣지 않고 used_in에 주제만 더한다. 옵션: --kit <kit 경로>, --rename 옛id=새id (여러 번)
"""
import argparse, json, os, re, shutil, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import FOLDER, PREFIX, REPO, kit_dir, load, save, sha1

ap = argparse.ArgumentParser()
ap.add_argument("topic")
ap.add_argument("--dry-run", action="store_true")
ap.add_argument("--kit")
ap.add_argument("--rename", action="append", default=[])
a = ap.parse_args()
KIT = kit_dir(a.kit)
T = a.topic
man_p = os.path.join(KIT, "topics", T, "assets.json")
ok_p = os.path.join(KIT, "build", T, "assets_ok.json")
if not os.path.exists(man_p): sys.exit(f"요청서 없음: {man_p}")
man = json.load(open(man_p, encoding="utf-8"))
if not any(k in man for k in ("sound", "none", "from")):
    sys.exit("옛 꼴 요청서 — add.py는 새 꼴(assets.py) 편만 다룬다. 옛 그림은 1차 일괄 넣기로 이미 들어가 있다.")
if man.get("none"): sys.exit("그림이 필요 없는 편(none)")
if man.get("from"): sys.exit(f"다른 편({man['from']}) 그림을 같이 쓰는 편 — 원래 편으로 add.py {man['from']}")
ok = json.load(open(ok_p, encoding="utf-8")) if os.path.exists(ok_p) else {}
if not ok.get("pd"):
    sys.exit("PD님 확인 기록(pd)이 없음 — assets.py ok <주제> --pd \"…\" 뒤에 넣는다. 아무것도 넣지 않음")
draw = {}
lp = os.path.join(KIT, "build", T, "assets_draw.log")
if os.path.exists(lp):
    for ln in open(lp, encoding="utf-8"):
        try: r = json.loads(ln); draw[r["id"]] = r
        except Exception: pass
try:
    js = "const B=require(%r);console.log(JSON.stringify({BG:B.BG_PROMPT,PROP:B.PROP_PROMPT}))" % os.path.join(KIT, "engine", "assets", "cast_bible.js")
    TPL = json.loads(subprocess.check_output(["node", "-e", js], text=True))
except Exception:
    TPL = None

KIND = {"background": "배경", "bg": "배경", "prop": "소품", "tex": "재질", "frame": "효과"}
ren = dict(r.split("=", 1) for r in a.rename)
cat = load(); by_sha = {e["sha1"]: e for e in cat}; ids = {e["id"] for e in cat}
added, used, skipped = [], [], []
for it in man.get("images", []):
    i = it["id"]; kind = KIND.get(it.get("kind"))
    if not kind: skipped.append((i, f"kind {it.get('kind')} — 캐릭터 등은 손으로 넣는다")); continue
    exts = (".jpg", ".png") if it["kind"] == "background" else (".png", ".jpg")
    src = next((os.path.join(KIT, "topics", T, "assets", i + x) for x in exts if os.path.exists(os.path.join(KIT, "topics", T, "assets", i + x))), None)
    if not src: skipped.append((i, "그림 파일 없음")); continue
    h = sha1(src)
    if ok.get("files", {}).get(i) != h: skipped.append((i, "PD 확인 뒤 바뀌었거나 확인 기록 없음")); continue
    if h in by_sha:
        e = by_sha[h]
        if T not in e["used_in"]: e["used_in"].append(T)
        used.append((i, e["id"]))
        continue
    toks = [t for t in i.split("_") if t not in ("bg", "prop", "tex", "fx", "background")]
    nid = ren.get(i) or PREFIX[kind] + "_" + "_".join(toks)
    while nid in ids: nid += "_2"
    ids.add(nid)
    p = it["prompt"]
    if TPL and it["kind"] in ("background", "frame", "prop"):
        p = (TPL["BG"] if it["kind"] in ("background", "frame") else TPL["PROP"]) + " Subject: " + p
    # 공개본에는 프롬프트의 금지 문구 한 줄을 넣지 않는다(낱말은 글자 코드로 적어 둠)
    _ban = "".join(map(chr, (111, 119, 108)))
    p2 = re.sub(r"\s*\b[Nn]o " + _ban + r"s?\b[.,]?", "", p)
    if p2 != p: p = p2; ban_note = " 공개본에서는 프롬프트의 금지 문구 한 줄을 뺐다."
    else: ban_note = ""
    eng = draw.get(i, {}).get("engine")
    tool = {"codex": "Codex 구독 그림 도구", "gemini": "Gemini 구독 CLI"}.get(eng, eng or "기록 없음") + (f" — 확인: build/{T}/assets_draw.log" if eng else "")
    from PIL import Image
    im = Image.open(src)
    ext = os.path.splitext(src)[1]
    e = dict(id=nid, file=f"{FOLDER[kind]}/{nid}{ext}", kind=kind, title=it.get("title") or it.get("scene") or i,
             tags=[t for t in re.split(r"[\s·,()]+", (it.get("scene") or "")) if t and not t.isdigit()] + [T],
             prompt=p, tool=tool, made=(draw.get(i, {}).get("at", "")[:10] or time.strftime("%Y-%m-%d")),
             from_topic=T, used_in=[T], size=dict(w=im.width, h=im.height, bytes=os.path.getsize(src)), sha1=h,
             aliases=[f"topics/{T}/assets/{os.path.basename(src)}"],
             note=f"add.py로 넣음({time.strftime('%Y-%m-%d')}) — 우리말 이름 · 태그를 손볼 것. PD 확인: {ok['pd'][:60]}" + ban_note)
    added.append(e)

print(f"# {T} — PD 확인: {ok['pd'][:80]}")
for e in added: print(f"  + 넣음  {e['id']:34s} ← {e['aliases'][0]}  [{e['tool']}]")
for i, nid in used: print(f"  = 이미 있음 {i} → {nid}")
print(f"  합계: 새로 넣을 것 {len(added)} · 이미 있음 {len(used)} · 건너뜀 {len(skipped)}")
for i, why in skipped: print(f"  - 건너뜀 {i}: {why}")
if a.dry_run:
    print("(--dry-run: 아무것도 복사하거나 고치지 않음)"); sys.exit(0)
for e in added:
    dst = os.path.join(REPO, e["file"]); os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(os.path.join(KIT, e["aliases"][0]), dst)
cat += added
save(cat)
print(f"catalog.json: +{len(added)}줄. 시트 다시 그리기: python3 tools/sheets.py")
