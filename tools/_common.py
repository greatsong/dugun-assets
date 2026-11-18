"""dugun-assets 도구 공용: 목록 읽기 · 쓰기, 미리보기 시트 그리기.
파이썬 표준 라이브러리 + Pillow(시트를 그릴 때만)."""
import hashlib, json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(REPO, "catalog.json")
FOLDER = {"배경": "backgrounds", "소품": "props", "재질": "textures", "효과": "effects", "캐릭터": "characters", "아이콘": "icons"}
PREFIX = {"배경": "bg", "소품": "prop", "재질": "tex", "효과": "fx", "캐릭터": "char", "아이콘": "icon"}
FONTS = [  # 우리말 글꼴 후보(있는 것 하나)
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "C:/Windows/Fonts/malgun.ttf",
]


def load():
    return json.load(open(CATALOG, encoding="utf-8"))


def save(cat):
    tmp = CATALOG + ".tmp"
    json.dump(cat, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, CATALOG)


def sha1(p):
    return hashlib.sha1(open(p, "rb").read()).hexdigest()


def path_of(e):
    return os.path.join(REPO, e["file"])


def _font(size):
    from PIL import ImageFont
    for f in [os.environ.get("DUGUN_FONT", "")] + FONTS:
        if f and os.path.exists(f):
            try: return ImageFont.truetype(f, size)
            except OSError: pass
    return ImageFont.load_default()


def sheet(entries, out, cols=8, cell=220, title="", max_bytes=2_000_000):
    """그림을 격자로 모은 jpg. 그림 아래에 id와 우리말 이름. 투명한 그림은 크림 바탕 위에."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("(Pillow가 없어 시트를 건너뜀 — pip install pillow)"); return None
    if not entries: return None
    cols = max(1, min(cols, len(entries)))
    lab = 46; head = 56 if title else 0
    rows = (len(entries) + cols - 1) // cols
    W, H = cols * cell, head + rows * (cell + lab)
    S = Image.new("RGB", (W, H), (246, 243, 236)); d = ImageDraw.Draw(S)
    f1, f2, ft = _font(15), _font(14), _font(26)
    if title: d.text((14, 12), title, fill=(40, 40, 60), font=ft)
    for i, e in enumerate(entries):
        x, y = (i % cols) * cell, head + (i // cols) * (cell + lab)
        try:
            im = Image.open(path_of(e)).convert("RGBA")
        except Exception:
            d.text((x + 8, y + 8), "열 수 없음", fill=(200, 0, 0), font=f1); continue
        im.thumbnail((cell - 12, cell - 12))
        bg = Image.new("RGBA", im.size, (255, 248, 230, 255)); bg.alpha_composite(im)
        S.paste(bg.convert("RGB"), (x + (cell - im.width) // 2, y + (cell - im.height) // 2))
        d.text((x + 6, y + cell + 2), e["id"][:30], fill=(30, 30, 30), font=f2)
        d.text((x + 6, y + cell + 22), e.get("title", "")[:16], fill=(70, 70, 110), font=f1)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    q, scale = 85, 1.0
    while True:
        T = S if scale == 1.0 else S.resize((int(W * scale), int(H * scale)))
        T.save(out, "JPEG", quality=q, optimize=True)
        if os.path.getsize(out) <= max_bytes or q <= 50: break
        q -= 10
        if q <= 55: scale *= 0.85
    return out


def kit_dir(arg=None):
    """두근두근러닝 제작 폴더(kit). --kit 또는 DUGUN_KIT, 없으면 저장소 옆의 기본 자리."""
    for p in (arg, os.environ.get("DUGUN_KIT"),
              os.path.join(os.path.dirname(REPO), "10_수업자료", "dugeun-theater", "kit")):
        if p and os.path.isdir(p): return os.path.abspath(p)
    sys.exit("kit 폴더를 찾지 못함 — --kit <경로> 또는 DUGUN_KIT")
