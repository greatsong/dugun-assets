#!/usr/bin/env python3
"""배경 음악(대사 밑에 가볍게 까는 음악)을 직접 합성해 섞는다 — 외부 음원·샘플·유료 API 없음.

  python3 pipeline/bgm.py <topic> <video> [--style keys] [--below 18] [--duck 6] [--force]
- 편 파일에 `bgm: { style: 'keys', below: 18, duck: 6 }`를 두면 produce.sh final 이 끝 화면 음악 다음에 부른다.
  bgm 이 없는 편은 아무것도 하지 않는다(종료 코드 0). (2026-11-15 리송 PD님: 교육계획서 영상 "가벼운 음악 적절히 배경으로 깔기")
- 곡 'keys' = 끝 화면 D '로파이 건반'과 같은 결(내림 마 장조, 80 BPM): 일렉트릭 피아노 화음 + 부드러운 베이스 + 아주 작은 셰이커,
  16마디(48초) 토막 넷(가벼운 A1·A2, 조금 찬 B1·B2)을 번갈아 이어 붙인다. 선율은 거의 없다(말을 가리지 않게).
- 음량: 대사 전체 음량(LUFS)보다 below LU 낮게, 대사가 나오는 동안은 duck dB 더 낮게(timeline.json 의 대사 구간으로 계산 — 펌핑 없음).
  말소리가 몰린 2~4 kHz는 음악에서 덜어 낸다.
- 끝 화면(outro)이 있으면 그 3초 앞에서 음악을 천천히 내려 끝 화면 음악에 자리를 넘긴다. 처음 2초는 서서히 올린다.
- 바탕 소리: audio_mix.wav(끝 화면 음악까지 섞인 것)가 audio.wav 보다 새것이면 그것, 아니면 audio.wav.
  이미 배경 음악을 섞은 audio_mix.wav 를 다시 받으면 두 번 섞지 않도록 audio_premix.wav(섞기 전 사본)를 바탕으로 쓴다(bgm.json 에 기록).
"""
import json, os, sys, wave
import numpy as np

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KIT, "pipeline"))
import outro_synth2 as O2
from outro_synth import SR, hz

a = sys.argv[1:]
if len(a) < 2: sys.exit(__doc__)
topic, video = a[0], a[1]
opt = lambda n, d=None: a[a.index(n) + 1] if n in a else d
B = os.path.join(KIT, "build", topic, video)
S = json.load(open(os.path.join(B, "script.json"), encoding="utf-8"))
cfg = dict(S.get("bgm") or {})
if opt("--style"): cfg["style"] = opt("--style")
if not cfg.get("style"):
    print("배경 음악 없음(편 파일에 bgm 이 없음)"); sys.exit(0)
STYLE = cfg["style"]; BELOW = float(opt("--below", cfg.get("below", 18))); DUCK = float(opt("--duck", cfg.get("duck", 6)))
if STYLE != "keys": sys.exit(f"없는 배경 음악 '{STYLE}' (지금은 keys 하나)")

BT = 60 / 80; BAR = 4 * BT; SEC_BARS = 16; SEC = SEC_BARS * BAR; TAIL = 4.0
PROGS = {
    1: [('Eb3', ['Bb3', 'D4', 'F4', 'G4']), ('C3', ['Bb3', 'D4', 'Eb4', 'G4']), ('Ab2', ['Bb3', 'C4', 'Eb4', 'G4']), ('Bb2', ['Ab3', 'C4', 'Eb4', 'F4'])],
    2: [('Ab2', ['G3', 'C4', 'Eb4', 'G4']), ('Bb2', ['Ab3', 'D4', 'F4', 'Bb4']), ('G2', ['F3', 'Bb3', 'D4', 'G4']), ('C3', ['Bb3', 'D4', 'Eb4', 'G4'])],
}


def section(kind, prog):
    """16마디 한 토막(+잔향 꼬리 4초). kind = 'A'(건반·베이스·셰이커) | 'B'(+ 여린 킥·림·하이햇·드문 비브라폰)."""
    O2.N = int((SEC + TAIL) * SR)                  # Mix2·duck_env 가 모듈의 N 을 길이로 쓴다
    O2.seed(300 + 10 * prog + (1 if kind == 'B' else 0)); rng = O2.rng
    m = O2.Mix2(); lazy = 0.06
    T = lambda bar, beat: (bar * 4 + beat + (lazy if abs(beat % 1 - 0.5) < 1e-6 else 0)) * BT
    kicks = [T(bar, beat) for bar in range(SEC_BARS) for beat in (0, 2.5)] if kind == 'B' else []
    dk = O2.duck_env(kicks, 0.15, 0.16) if kicks else 1.0
    soft = O2.chain(O2.g_lp(5200, 2), O2.g_bell(300, 1.0, 1.0))
    m.stem('keys', wet=0.24, dly=0.08, fx=lambda y: O2.autopan(O2.fftfilt(y, soft), 0.7, 0.14) * dk)
    m.stem('bass', wet=0.03, fx=lambda y: O2.fftfilt(y, O2.g_lp(800, 2)) * dk)
    m.stem('drums', wet=0.12, fx=lambda y: O2.fftfilt(y, O2.g_lp(9000, 2)))
    m.stem('bell', wet=0.35, dly=0.25)
    P = PROGS[prog]
    for bar in range(SEC_BARS):
        root, ch = P[bar % 4]; vb = 0.48 + 0.05 * ((bar // 4) % 2)
        for beat, ln, v in ((0, 2.4, vb), (2.5, 1.3, vb * 0.7)):
            for j, nm in enumerate(ch):
                at = T(bar, beat) + j * 0.016 + rng.normal(0, 0.003)
                m.add('keys', O2.rhodes(hz(nm), ln * BT, v + rng.normal(0, 0.03), at, 1.0), at, 0.15, pan=-0.3 + 0.2 * j)
        f = hz(root)
        m.add('bass', O2.subbass(f, 1.7 * BT, 0.4), T(bar, 0), 0.42)
        m.add('bass', O2.subbass(f * (1.5 if bar % 4 != 3 else 1.0), 0.9 * BT, 0.35), T(bar, 3), 0.30)
        for k in range(4):
            m.add('drums', O2.shaker2(0.8 + 0.2 * rng.random()), T(bar, k + 0.5), 0.05 if kind == 'A' else 0.07, pan=0.3)
        if kind == 'B':
            for beat, v in ((0, 1.0), (2.5, 0.75)): m.add('drums', O2.kick2(100, 45, 0.035, 0.16, 0.04), T(bar, beat), 0.32 * v)
            for beat in (1, 3): m.add('drums', O2.rim(), T(bar, beat) + 0.012, 0.07, pan=-0.2)
            for k in range(8): m.add('drums', O2.hat(0.02, 6500, 10000), T(bar, k / 2) + rng.normal(0, 0.004), 0.05 if k % 2 == 0 else 0.035, pan=0.35)
            if bar % 2 == 1:                       # 두 마디에 한 번, 화음 음 하나를 높이 살짝
                nm = ch[int(rng.integers(len(ch)))]; at = T(bar, 1.5 + 0.5 * int(rng.integers(2)))
                m.add('bell', O2.vibes(hz(nm) * 2, 2.4), at, 0.05, pan=0.25)
    master = O2.chain(O2.g_bell(2800, -6.0, 0.9), O2.g_lp(7000, 2))   # 말소리 대역을 비워 둔다
    return m.render(rt60=1.2, rev=0.9, bright=5500.0, dtime=0.75 * BT, dfb=0.3, master=master, target=-20.0, limit_db=2.0, fade_out=1.0)


def read_wav(p):
    with wave.open(p) as w:
        ch, n = w.getnchannels(), w.getnframes(); x = np.frombuffer(w.readframes(n), "<i2").astype(np.float32) / 32768
    x = x.reshape(-1, ch)
    return np.repeat(x, 2, 1) if ch == 1 else x


def write_wav(p, y):
    tmp = p + ".tmp.wav"
    with wave.open(tmp, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(y, -1, 1) * 32767).astype("<i2").tobytes())
    os.replace(tmp, p)


def sig(p):
    st = os.stat(p); return [st.st_size, round(st.st_mtime, 3)]


TL = json.load(open(os.path.join(B, "timeline.json"), encoding="utf-8"))
total = float(TL["duration"])
outro = [s for s in TL["scenes"] if s["id"] == "outro"]
end = (outro[0]["start"] - 0.3) if outro else total

# 바탕 소리 고르기(두 번 섞지 않기)
voice = os.path.join(B, "audio.wav"); mix = os.path.join(B, "audio_mix.wav"); pre = os.path.join(B, "audio_premix.wav"); rec = os.path.join(B, "bgm.json")
R = json.load(open(rec)) if os.path.exists(rec) else {}
if os.path.exists(mix) and os.path.getmtime(mix) > os.path.getmtime(voice):
    if R.get("out") == sig(mix) and os.path.exists(pre): base = pre            # 이미 배경 음악을 섞은 판 → 섞기 전 사본
    else: base = mix; write_wav(pre, read_wav(mix))
else:
    base = voice
X = read_wav(base)

# 음악 토막 만들기(캐시)
cdir = os.path.join(KIT, "build", "bgm"); os.makedirs(cdir, exist_ok=True)
secs = {}
for kind in ("A", "B"):
    for prog in (1, 2):
        p = os.path.join(cdir, f"{STYLE}_{kind}{prog}.wav")
        if "--force" in a or not os.path.exists(p): write_wav(p, section(kind, prog))
        secs[kind + str(prog)] = read_wav(p)
ORDER = ["A1", "B1", "A2", "B2"]
L = len(X); bed = np.zeros((L + int((SEC + TAIL) * SR), 2), np.float32); i = 0; k = 0
while i * SEC < end:
    y = secs[ORDER[i % 4]]; st = int(round(i * SEC * SR)); bed[st:st + len(y)] += y; i += 1
bed = bed[:L]

# 음량 곡선: 대사 동안 duck dB 낮게(0.35초 경사), 처음 2초 올리기, 끝 화면 3초 앞에서 내리기
t = np.arange(L) / SR
speak = np.zeros(L, bool)
for sc in TL["scenes"]:
    for b in (sc.get("beats") or {}).values():
        s0 = int((sc["start"] + b["start"] - 0.15) * SR); s1 = int((sc["start"] + b["start"] + b["dur"] + 0.25) * SR)
        speak[max(0, s0):min(L, s1)] = True
g = np.where(speak, 10 ** (-DUCK / 20), 1.0).astype(np.float32)
w = int(0.35 * SR); g = np.convolve(np.pad(g, w, mode="edge"), np.ones(2 * w + 1, np.float32) / (2 * w + 1), mode="same")[w:-w]
g *= np.clip(t / 2.0, 0, 1) * np.clip((end - t) / 3.0, 0, 1)
O2.N = L
vl = O2.lufs_np(read_wav(voice)[: int(min(total, 600) * SR)])                 # 대사만의 음량
bl = O2.lufs_np(bed[: int(min(end, 600) * SR)])
gain = 10 ** (((vl - BELOW) - bl) / 20)
out = X + bed * (gain * g)[:, None]
write_wav(mix, out)
json.dump({"style": STYLE, "below": BELOW, "duck": DUCK, "voice_lufs": round(vl, 2), "bed_lufs": round(bl, 2), "gain_db": round(20 * np.log10(gain), 2),
           "end": round(end, 2), "sections": i, "base": os.path.basename(base), "out": sig(mix)}, open(rec, "w"), ensure_ascii=False, indent=1)
print(f"배경 음악 {STYLE}: {topic} {video} 0~{end:.1f}초, 토막 {i}개, 대사 {vl:.1f} LUFS → 음악 {vl - BELOW:.1f}(말하는 동안 {vl - BELOW - DUCK:.1f}) → audio_mix.wav")
