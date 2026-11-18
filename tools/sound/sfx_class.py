#!/usr/bin/env python3
"""교실 · 예능 효과음 묶음 — 모두 직접 합성(numpy만, 외부 음원 · 샘플 · 유료 API 없음). 두근두근 결: 밝고 부드럽고 귀엽게.

  (저장소 사본) 두근두근러닝 제작 폴더의 pipeline/sfx_class.py를 옮겨 왔다. 고친 것은 불러오는 경로와 저장 폴더뿐이다:
  결과는 tools/sound/out/sfx_class/, 듣기 모음 영상은 tools/sound/out/preview/. 글꼴은 제작 폴더의 것이 없으면 이 컴퓨터의 한글 글꼴을 찾는다.
  python3 tools/sound/sfx_class.py                      # → tools/sound/out/sfx_class/{wav,m4a,mp3}/sfx_*.{wav,m4a,mp3} + sounds.json + sheet.jpg
  python3 tools/sound/sfx_class.py --only quiz_think    # 한 효과음만(변형 모두)
  python3 tools/sound/sfx_class.py --one quiz_think 1 out.wav dur=4.2 bell=0   # 하나를 원하는 값으로(음량 맞춤까지)
  python3 tools/sound/sfx_class.py --preview            # 듣기 모음 영상
  python3 tools/sound/sfx_class.py --list               # 목록만

묶음 둘(sounds.json 의 style): "교실"(퀴즈 · 정답 · 오답 · 전환 · 상상 · 카드 · 마커 · 발견 · 세기 …) / "예능"(띠용 · 뾰로롱 · 두둥 · 빠밤 · 뿅 · 또르르 · 쿵 ·
삐빅 · 휘익 · 꽈광 · 웃음 리듬 · 두근두근 · 박수 · 두구두구 · 땡 · 띠링). 특정 방송 · 프로그램의 효과음을 따라 만들지 않았다 — 그런 쓰임의 소리를 새로 지었다.

편에서 불러 쓰는 법(파이프라인에는 아직 효과음 단계가 없다 — 넣을지는 PD님 결정. 지금은 편 폴더의 sfx 단계(예: topics/music_beat/sfx.py)가 wav 를 읽어 섞는 식)
  1) 만들어 둔 파일 쓰기: build/sfx_class/wav/sfx_<이름>_<번호>.wav (48 kHz 16비트 스테레오). 목록 · 길이 · 어울리는 상황은 sounds.json.
     m4a · mp3 는 미리듣기 · 웹용(인코더 지연으로 앞에 수십 ms 빈 소리가 붙을 수 있다 → 영상 싱크는 wav 로).
  2) 코드에서 바로 만들기(길이 · 횟수를 바꿀 때):
       import sys; sys.path.insert(0, 'tools/sound'); import sfx_class as FX
       y = FX.make('quiz_think', 1, dur=3.0, bell=False)   # (n, 2) float, 음량 맞춤 끝(순간 음량 최댓값 −20 LUFS, 트루 피크 −1.5 dBTP 아래)
       FX.write_wav('build/x/think.wav', y)
     길이를 바꿀 수 있는 것: quiz_think(dur, bell), heartbeat(beats, bpm), drumroll(dur), marker(strokes), count_step(steps, k).
  3) 섞을 때 음량: 대사 위에 얹으면 sounds.json 의 mix_db(추천 덧셈, 대개 −3 ~ −8 dB)만큼 줄여 쓴다. 효과음은 모두 2~4 kHz(말소리 대역)를
     4 dB 덜어 두었다. 같은 장면에 효과음을 겹치지 말고, 표시(낱말 카드 · 점 찍기)마다 붙이지 않는다(화이트보드 결정안 8절과 같은 원칙).
  4) 퀴즈 생각 시간: lesson.js 의 카운트다운은 숫자가 '답 비트 0.3초 앞에서 1초 간격 거꾸로' 바뀌고 0.3초 앞에서 사라진다.
     quiz_think(dur=생각 시간)은 째깍을 그 순간들에, 작은 종을 숫자가 사라지는 순간(dur−0.3초)에 놓는다 → 카운트다운이 시작하는 순간(tk 비트 끝)에 깔면 맞는다.
     정답 '딩동'을 바로 이어 쓰면 bell=False.

음량: 효과음마다 '순간 음량 최댓값'(400 ms 창, BS.1770 K 가중 — 케플러 극장판 sfx.py 와 같은 잣대)을 −20 LUFS 로 맞추고, 트루 피크(4배 오버샘플)가
−1.5 dBTP 를 넘지 않게 멈춘다(m4a · mp3 로 바꿔도 −1 dBFS 아래). 아주 짧은 소리는 그 상한에 걸려 −20 보다 작다(sounds.json 에 표시).
라이선스: 우리 합성(CC BY-NC 4.0, 두근두근러닝). 짧은 신호음 몇 개는 zzfx.py(ZzFX 를 numpy 로 옮긴 것, MIT)로 만든다.
기존 합성 코드(outro_synth.py · outro_synth2.py)는 불러 쓰기만 하고 고치지 않는다. 케플러 극장판 sfx.py 의 도우미(방 울림 · 띠 잡음 · 순간 음량)는 이 파일에 옮겨 고쳐 썼다.
"""
import hashlib, json, math, os, subprocess, sys, wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)              # 저장소 사본: tools/
REPO = os.path.dirname(KIT)              # 저장소 맨 위
sys.path.insert(0, HERE)
import outro_synth as O1           # 읽기 · 불러 쓰기만
import outro_synth2 as O2          # 읽기 · 불러 쓰기만
import zzfx as Z

SR = O1.SR
PI2 = 2 * np.pi
OUT = os.path.join(HERE, 'out', 'sfx_class')        # 저장소 사본: tools/sound/out/sfx_class/
PREVIEW = os.path.join(HERE, 'out', 'preview')


def _font(name, sz):
    """저장소 사본: 제작 폴더의 글꼴(engine/fonts)이 없으면 이 컴퓨터의 한글 글꼴을 쓴다."""
    from PIL import ImageFont
    for p in (os.path.join(KIT, 'engine', 'fonts', name), '/System/Library/Fonts/AppleSDGothicNeo.ttc',
              'C:/Windows/Fonts/malgunbd.ttf', 'C:/Windows/Fonts/malgun.ttf', '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'):
        if os.path.exists(p): return ImageFont.truetype(p, sz)
    return ImageFont.load_default()
TARGET_M = -20.0                    # 순간 음량 최댓값 목표(LUFS)
TP_CAP = -1.5                       # 트루 피크 상한(dBTP)
rng = np.random.default_rng(1)


def reseed(k):
    global rng
    rng = np.random.default_rng(k); O2.seed(k + 1); O1.rng = np.random.default_rng(k + 2)


# ───────── 기본 도우미 ─────────
def tt(d):
    return np.arange(max(1, int(round(d * SR)))) / SR


def N(name):
    """'C6' → Hz"""
    return O2.mhz(O2.midi(name))


PENTA = ('C', 'D', 'E', 'G', 'A')


def penta(lo, hi):
    """lo~hi(이름, 예 'C5','C7') 사이 다장조 5음 음계 음들(Hz, 오름)."""
    a, b = O2.midi(lo), O2.midi(hi); pcs = {0, 2, 4, 7, 9}
    return [O2.mhz(m) for m in range(a, b + 1) if m % 12 in pcs]


def env(t, tau, att=0.001):
    return np.minimum(1, t / att) * np.exp(-t / tau)


def norm(y):
    return y / (np.max(np.abs(y)) + 1e-12)


def to_st(y, pan=0.0):
    y = np.asarray(y, dtype=np.float64)
    if y.ndim == 2: return y
    th = (np.clip(pan, -1, 1) + 1) * np.pi / 4
    return np.stack([y * np.cos(th), y * np.sin(th)], 1) * np.sqrt(2)


def bandnoise(n, lo, hi, order=2):
    return norm(O2.fftfilt(rng.standard_normal(n), O2.chain(O2.g_hp(lo, order), O2.g_lp(hi, order))))


def lp(y, fc, order=2):
    return O2.fftfilt(y, O2.g_lp(fc, order))


def hp(y, fc, order=2):
    return O2.fftfilt(y, O2.g_hp(fc, order))


class Buf:
    """소리 조각을 시각에 놓아 섞는 스테레오 판."""

    def __init__(self, dur):
        self.y = np.zeros((int(round(dur * SR)), 2))

    def add(self, x, at=0.0, gain=1.0, pan=0.0):
        x = np.asarray(x, dtype=np.float64)
        if x.ndim == 1: x = to_st(x, pan)
        elif pan: x = x * np.array([min(1.0, 1 - pan), min(1.0, 1 + pan)])
        i = int(round(at * SR))
        if i < 0: x = x[-i:]; i = 0
        n = min(len(x), len(self.y) - i)
        if n <= 0: return self
        x = x[:n] * gain
        k = min(n // 4, int(0.03 * SR))          # 덜 사그라든 채 잘린 끝을 30 ms 페이드 — '틱' 클릭 방지
        if k > 1: x[-k:] *= (np.cos(np.linspace(0, np.pi / 2, k)) ** 2)[:, None]
        self.y[i:i + n] += x
        return self


def room(y, rt=0.6, wet=0.18, bright=7000.0, lowcut=200.0):
    """작은 방 울림(케플러 sfx.py 의 room 을 고침): 원래 소리 + 울림 꼬리(rt 초)."""
    y = to_st(y)
    irL, irR = O2.make_ir(round(rt, 3), bright, lowcut, 9)
    n = len(y) + int(rt * 1.1 * SR); x = np.zeros((n, 2)); x[:len(y)] = y
    return x + wet * np.stack([O2.conv(x[:, 0], irL), O2.conv(x[:, 1], irR)], 1)


def svf(x, fc, q=1.0, mode='bp'):
    """시간에 따라 움직이는 상태 변수 거르개(TPT). fc: 수 또는 x 와 같은 길이의 배열. bp 는 가운데 이득 1."""
    n = len(x); fcv = np.broadcast_to(np.asarray(fc, dtype=np.float64), (n,))
    g = np.tan(np.pi * np.clip(fcv, 20.0, SR * 0.45) / SR); k = 1.0 / q
    a1 = 1.0 / (1.0 + g * (g + k)); a2 = g * a1; a3 = g * a2
    A1, A2, A3, X = a1.tolist(), a2.tolist(), a3.tolist(), np.asarray(x, dtype=np.float64).tolist()
    out = [0.0] * n; ic1 = ic2 = 0.0
    for i in range(n):
        v3 = X[i] - ic2; v1 = A1[i] * ic1 + A2[i] * v3; v2 = ic2 + A2[i] * ic1 + A3[i] * v3
        ic1 = 2 * v1 - ic1; ic2 = 2 * v2 - ic2
        out[i] = k * v1 if mode == 'bp' else (v2 if mode == 'lp' else X[i] - k * v1 - v2)
    return np.asarray(out)


def glide(f, t):
    """주파수 곡선 f(t)(배열) → 위상."""
    return PI2 * np.cumsum(f) / SR


def sat(y, drive=2.0):
    """부드러운 포화 — 낮은 소리에 배음을 더해 휴대폰 스피커에서도 들리게."""
    return np.tanh(drive * y) / np.tanh(drive)


# ───────── 악기 조각(부드럽게) ─────────
def glock_soft(f, dur=1.4, bright=0.5):
    """글로켄슈필을 부드럽게: 위 부분음을 줄였다(2~4 kHz가 덜 쨍하게)."""
    t = tt(dur); y = np.zeros(len(t))
    for r, a, tau in ((1, 1.0, 0.75), (2.756, 0.30 * bright, 0.35), (5.404, 0.08 * bright, 0.15)):
        if r * f < 15000: y += a * np.sin(PI2 * r * f * t) * np.exp(-t / tau)
    return y * np.minimum(1, t / 0.0015)


def bell(f, dur=1.3, tau=0.55):
    """맑은 차임(케플러 s12 의 부분음)."""
    t = tt(dur)
    y = sum(a * np.sin(PI2 * r * f * t) * np.exp(-t / (tau * k)) for r, a, k in ((1, 1.0, 1.0), (2.0, 0.22, 0.55), (3.01, 0.08, 0.25), (4.17, 0.04, 0.13)))
    return y * np.minimum(1, t / 0.0015)


def handbell(f, dur=1.6):
    """손종 '땡': 조금 어긋난 부분음(1 · 2.0 · 2.74 · 5.1)이 서로 다른 빠르기로 사라진다."""
    t = tt(dur); y = np.zeros(len(t))
    for r, a, tau in ((1, 1.0, 0.7), (1.004, 0.5, 0.65), (2.0, 0.35, 0.4), (2.74, 0.22, 0.25), (5.1, 0.06, 0.1)):
        y += a * np.sin(PI2 * r * f * t + r) * np.exp(-t / tau)
    strike = lp(bandnoise(len(t), 800, 4500) * np.exp(-t / 0.003) * np.minimum(1, t / 0.0008), 4000) * 0.25
    return (y + strike) * np.minimum(1, t / 0.001)


def woodtick(f=1180.0, tau=0.009, noise=0.6):
    """마른 나무 '틱'(케플러 s10 을 음높이 바꾸게)."""
    t = tt(0.12)
    body = (np.sin(PI2 * f * t) + 0.45 * np.sin(PI2 * 2.23 * f * t) * np.exp(-t / 0.004)) * env(t, tau, 0.0004)
    nz = bandnoise(len(t), 1200, 5000) * env(t, 0.0012, 0.0003)
    return norm(lp(body + noise * nz, 6500))


def marimba(f, dur=1.0, vel=1.0):
    """outro_synth 마림바 — 채 소리(흰 잡음 톡)를 걸러 둥글게."""
    return lp(O1.marimba(f, dur), 5500) * vel


def musicbox(f, dur=1.6):
    return lp(O1.musicbox(f, dur), 6500)


def pop(f0=480.0, f1=1150.0, tau=0.028, dur=0.14, up=True):
    """물방울 '톡/퐁': 음높이가 빠르게 올라가며(또는 내려가며) 사라지는 사인."""
    t = tt(dur); k = np.exp(-t / 0.012)
    f = f1 + (f0 - f1) * k if up else f1 + (f0 - f1) * (1 - k)
    y = np.sin(glide(f, t)) * env(t, tau, 0.0006)
    return y + 0.15 * np.sin(2 * glide(f, t)) * env(t, tau * 0.5, 0.0006)


def thump(f0=75.0, f1=46.0, tau=0.10, dur=0.45, drive=2.2, ptau=0.03):
    """낮은 '쿵/둥': 음높이가 툭 떨어지는 사인 + 포화(배음) + 작은 잡음."""
    t = tt(dur); f = f1 + (f0 - f1) * np.exp(-t / ptau)
    y = np.sin(glide(f, t)) * env(t, tau, 0.006)
    y = sat(y, drive) + 0.15 * lp(rng.standard_normal(len(t)), 300) * np.exp(-t / 0.02) * np.minimum(1, t / 0.004)
    return lp(y, 1300)          # 배음은 1 kHz 언저리까지만(휴대폰에서 들리되 '딱' 소리는 안 나게)


def timp(f, dur=1.4, vel=1.0):
    """팀파니 비슷한 북: 살짝 떨어지는 음높이 + 어긋난 부분음 + 말렛 잡음."""
    t = tt(dur); fr = f * (1 + 0.05 * np.exp(-t / 0.03)); ph = glide(fr, t)
    y = sum(a * np.sin(r * ph) * np.exp(-t / tau) for r, a, tau in ((1, 1.0, 0.55), (1.5, 0.5, 0.32), (1.99, 0.35, 0.25), (2.44, 0.2, 0.15), (2.98, 0.1, 0.1)))
    mallet = lp(rng.standard_normal(len(t)), 1500) * np.exp(-t / 0.006)
    return lp(sat((y + 0.4 * norm(mallet)) * np.minimum(1, t / 0.003) * vel, 1.5), 2500)


def flute(fcurve, dur, breath=0.025):
    """부드러운 플루트(음높이 곡선을 받는다)."""
    t = tt(dur); f = np.broadcast_to(fcurve, t.shape) * (1 + 0.004 * np.sin(PI2 * 5.0 * t) * np.clip((t - 0.15) / 0.2, 0, 1))
    ph = glide(f, t); y = np.sin(ph) + 0.16 * np.sin(2 * ph) + 0.05 * np.sin(3 * ph)
    br = bandnoise(len(t), 600, 3000) * breath
    return (y + br) * (1 - np.exp(-t / 0.04)) * np.minimum(1, (dur - t) / 0.06).clip(0, 1)


def blip(f, dur=0.06, duty=0.5, fc=2600.0):
    """부드러운 전자 '삑'(사각파를 거른 것)."""
    t = tt(dur + 0.01); y = np.sign(np.sin(PI2 * f * t) - np.cos(np.pi * duty)) * 0.6
    y = lp(y, fc, 2) * np.minimum(1, t / 0.002) * np.clip((dur + 0.01 - t) / 0.008, 0, 1)
    return y


def clap_shape(fc, seedk):
    r = np.random.default_rng(seedk); t = tt(0.16)
    nz = O2.fftfilt(r.standard_normal(len(t)), O2.chain(O2.g_hp(fc * 0.55, 2), O2.g_lp(fc * 2.2, 2)))
    e = np.zeros(len(t))
    for d in (0.0, 0.006 + 0.004 * r.random(), 0.013 + 0.005 * r.random()): e += 0.6 * np.where(t >= d, np.exp(-(t - d) / 0.004), 0)
    e += 0.8 * np.where(t >= 0.015, np.exp(-(t - 0.015) / 0.03), 0)
    return norm(nz * e)


def noise_sweep(dur, f0, f1, q=1.2, curve=1.0, env_pow=1.5, peak=0.5):
    """'휙': 통과 대역이 f0 → f1 로 움직이는 바람 소리. peak = 가장 큰 순간(0~1)."""
    t = tt(dur); u = t / dur
    fc = f0 * (f1 / f0) ** (u ** curve)
    e = np.where(u < peak, (u / peak), (1 - u) / (1 - peak)).clip(0, 1) ** env_pow
    e = np.sin(e * np.pi / 2) ** 2
    return norm(svf(rng.standard_normal(len(t)), fc, q)) * e


def pan_move(y, p0, p1):
    y = np.asarray(y); u = np.linspace(0, 1, len(y)); p = p0 + (p1 - p0) * u; th = (p + 1) * np.pi / 4
    return np.stack([y * np.cos(th), y * np.sin(th)], 1) * np.sqrt(2)


def shimmer(dur, lo=5000, hi=9000, att=0.4, tau=0.5, gain=0.04):
    """아주 옅은 반짝임 바람(위쪽 띠 잡음)."""
    t = tt(dur); e = np.minimum(1, t / att) * np.exp(-np.maximum(t - att, 0) / tau)
    return to_st(bandnoise(len(t), lo, hi) * e * gain)


def zz(*a, **k):
    """zzfx 값 한 줄(원본 순서) → 모노. seed 고정(늘 같은 소리)."""
    return Z.zzfx(*a, **k)


# ═════════════════════════ 소리 목록 ═════════════════════════
SOUNDS = []


def reg(base, style, title, situation, mood, variants, mix_db=-4, params=None):
    """variants: [(변형 이름, 만든 법), …]"""
    def deco(fn):
        SOUNDS.append(dict(base=base, style=style, title=title, situation=situation, mood=mood, variants=variants,
                           mix_db=mix_db, params=params or {}, fn=fn))
        return fn
    return deco


def get(base):
    for s in SOUNDS:
        if s['base'] == base: return s
    raise KeyError(base)


# ───────────────────────── 교실 ─────────────────────────
def think_times(dur):
    """lesson.js 카운트다운이 숫자를 바꾸는 순간(답 비트 0.3초 앞에서 1초 간격 거꾸로)."""
    ts = []; k = 1
    while dur - 0.3 - k >= -1e-9: ts.append(dur - 0.3 - k); k += 1
    ts = sorted(ts)
    if not ts or ts[0] >= 0.5: ts = [0.0] + ts
    return ts


@reg('quiz_think', '교실', '퀴즈 생각 시간', '퀴즈 보기를 다 읽은 뒤 카운트다운(기본 3.6초)이 도는 동안 — 카운트다운 시작 순간에 깐다',
     '조용히 기다리는 두근두근, 끝에 작은 종',
     [('나무 째깍 + 글로켄 종', '마른 나무 틱(똑 · 딱 두 높이)을 숫자가 바뀔 때마다, 끝에 부드러운 글로켄 E6 · 첼레스타 한 번'),
      ('시계 똑딱 + 첼레스타 두 음', '작은 시계 똑(높게) · 딱(낮게) + 끝에 첼레스타 C6 → G6'),
      ('마림바 통통(점점 올라감) + 차임 화음', '숫자마다 마림바 음이 한 칸씩 올라가 기대감, 끝에 글로켄 도 · 미 · 솔 화음')],
     mix_db=-6, params=dict(dur=3.6, bell=True))
def quiz_think(v, dur=3.6, bell=True):
    ticks = think_times(dur); bt = dur - 0.3; B = Buf(dur + 1.6)
    for i, t0 in enumerate(ticks):
        last = i == len(ticks) - 1
        if v == 1:
            B.add(woodtick(1250 if i % 2 == 0 else 1010, 0.008), t0, 0.55 + (0.1 if last else 0))
        elif v == 2:
            tick = woodtick(1650, 0.006, 0.9) if i % 2 == 0 else woodtick(880, 0.012, 0.5)
            B.add(lp(tick, 6000), t0, 0.5)
        else:
            notes = penta('G4', 'G6'); f = notes[min(i, len(notes) - 1)]
            B.add(marimba(f, 0.6), t0, 0.5 + 0.06 * i)
    if bell:
        if v == 1:
            B.add(glock_soft(N('E6'), 1.3), bt, 0.42); B.add(O2.celesta(N('E5'), 1.2), bt, 0.25)
        elif v == 2:
            B.add(O2.celesta(N('C6'), 1.0), bt - 0.12, 0.35); B.add(O2.celesta(N('G6'), 1.3), bt, 0.42)
        else:
            for j, nm in enumerate(('C6', 'E6', 'G6')): B.add(glock_soft(N(nm), 1.4), bt + 0.025 * j, 0.28, pan=-0.3 + 0.3 * j)
            B.add(O2.vibes(N('C5'), 1.4), bt, 0.18)
    return room(B.y, 0.5, 0.14)


@reg('answer_ding', '교실', '정답 딩동', '정답 공개 순간(정답 보기에 불이 들어올 때)', '맑고 반가운, 놀리지 않는 축하',
     [('딩동(두 음 오름)', '첼레스타 + 부드러운 글로켄 솔5 → 도6'),
      ('딩동댕(세 음)', '마림바 + 글로켄 도 · 미 · 솔, 마지막 음을 길게 + 비브라폰 받침'),
      ('반짝 차임', '신스 벨 도 · 미 · 솔 · 도를 빠르게 훑고 옅은 반짝임')],
     mix_db=-3)
def answer_ding(v):
    B = Buf(2.2)
    if v == 1:
        for t0, nm, g in ((0.0, 'G5', 0.8), (0.13, 'C6', 1.0)):
            B.add(O2.celesta(N(nm), 1.4), t0, 0.6 * g); B.add(glock_soft(N(nm), 1.4, 0.4), t0, 0.35 * g)
    elif v == 2:
        for j, nm in enumerate(('C6', 'E6', 'G6')):
            d = 1.4 if j == 2 else 0.5
            B.add(marimba(N(nm), d), 0.12 * j, 0.55); B.add(glock_soft(N(nm), d, 0.35), 0.12 * j, 0.25 + 0.1 * (j == 2))
        B.add(O2.vibes(N('C5'), 1.6), 0.24, 0.2); B.add(O2.vibes(N('E5'), 1.6), 0.24, 0.15)
    else:
        for j, nm in enumerate(('C6', 'E6', 'G6', 'C7')):
            B.add(O2.bellpluck(N(nm), 1.3), 0.05 * j, 0.35 + 0.08 * j, pan=-0.45 + 0.3 * j)
        B.add(shimmer(1.4, 5000, 9000, 0.15, 0.4, 0.05), 0.12)
    return room(B.y, 0.8, 0.2)


@reg('wrong_soft', '교실', '부드러운 오답', '오답을 고른 친구 · 틀린 생각을 보여 줄 때(놀리지 않게)', '아쉽지만 괜찮아, 둥글고 작게',
     [('뿌우(내려가는 두 음, 플루트)', '부드러운 플루트 미4 → 도4, 둘째 음 끝이 살짝 내려감'),
      ('통통(내려가는 마림바)', '낮은 마림바 미4 → 도4, 높은 소리를 걷어 둥글게'),
      ('뾰잉(아래로 미끄러짐)', 'zzfx 삼각파가 아래로 미끄러짐 — 값 한 줄: zzfx(.9,0,620,.01,.12,.3,1,1,-1.1,0,0,0,0,0,0,0,0,.8,.04)')],
     mix_db=-4)
def wrong_soft(v):
    B = Buf(1.4)
    if v == 1:
        B.add(flute(N('E4'), 0.24), 0.0, 0.5)
        d = 0.52; t = tt(d); fc = N('C4') * (1 - 0.035 * np.clip((t - 0.25) / 0.27, 0, 1) ** 1.5)
        B.add(flute(fc, d), 0.27, 0.55)
        B.y = lp(B.y, 2600)
    elif v == 2:
        B.add(lp(marimba(N('E4'), 0.7), 1800), 0.0, 0.7); B.add(lp(marimba(N('C4'), 0.9), 1600), 0.2, 0.75)
    else:
        y = zz(.9, 0, 620, .01, .12, .3, 1, 1, -1.1, 0, 0, 0, 0, 0, 0, 0, 0, .8, .04)
        B.add(lp(y, 3200), 0.0, 0.6)
    return room(B.y, 0.5, 0.15)


@reg('whoosh_short', '교실', '장면 전환 휙(짧게)', '장면 · 보드가 바뀔 때, 화면이 옆으로 밀려날 때(0.4초)', '가볍고 빠른 바람',
     [('휙(위로, 왼→오)', '잡음의 통과 대역이 500 → 3,500 Hz로 올라가며 왼쪽에서 오른쪽으로'),
      ('훅(아래로, 오→왼)', '통과 대역이 2,500 → 600 Hz로 내려가는 둥근 바람, 오른쪽에서 왼쪽으로')],
     mix_db=-5)
def whoosh_short(v):
    if v == 1: y = pan_move(noise_sweep(0.42, 500, 3500, 1.2, 1.0, 1.2, 0.62), -0.6, 0.6)
    else: y = pan_move(lp(noise_sweep(0.42, 2500, 600, 0.9, 0.8, 1.4, 0.45), 4000), 0.5, -0.5)
    return room(y, 0.4, 0.12)


@reg('whoosh_long', '교실', '장면 전환 휙(길게)', '큰 장면 전환 · 다음 이야기로 넘어갈 때(1초)', '차오르다 지나가는 바람',
     [('쉬이익(차오름)', '통과 대역이 400 → 6,000 Hz로 차오르고 옅은 휘파람이 함께 오름, 끝에서 빠르게 사라짐'),
      ('휘이익 + 톡', '가운데가 가장 큰 바람이 지나간 뒤 첼레스타 한 음')],
     mix_db=-5)
def whoosh_long(v):
    d = 1.0; t = tt(d); u = t / d
    if v == 1:
        y = noise_sweep(d, 400, 6000, 1.1, 1.2, 1.6, 0.85)
        tone = np.sin(glide(380 * (1500 / 380) ** (u ** 1.3), t)) * (np.sin(np.pi * np.clip(u / 0.9, 0, 1)) ** 2) * 0.08
        y = pan_move(y + tone, -0.5, 0.5)
        B = Buf(1.3).add(y)
    else:
        y = noise_sweep(d, 3000, 700, 1.0, 1.0, 1.5, 0.45)
        B = Buf(1.6).add(pan_move(y, 0.6, -0.6)).add(O2.celesta(N('G6'), 0.8), 0.78, 0.22)
    return room(B.y, 0.6, 0.15)


def _gliss(B, notes, t0, span, inst, g0, g1, accel=1.0, pan=0.6, dur=1.2):
    n = len(notes)
    for i, f in enumerate(notes):
        u = i / max(1, n - 1); at = t0 + span * (u ** accel)
        B.add(inst(f, dur), at, g0 + (g1 - g0) * u, pan=(-pan if i % 2 else pan) * (0.4 + 0.6 * u))


@reg('imagine_in', '교실', '상상 들어가기 반짝', '"상상해 볼까?" — 상상 구름이 피어나며 상상 장면으로 들어갈 때', '꿈결 같은 반짝임, 동화의 시작',
     [('별가루 오름', '첼레스타가 도5 → 도7 5음 음계로 빨라지며 오르고, 옅은 반짝임 바람 + 부드러운 패드'),
      ('하프 오름 + 꿈결 패드', '하프 훑어 오르기 + 비브라폰 화음 + 천천히 일렁이는 현 패드')],
     mix_db=-5)
def imagine_in(v):
    B = Buf(2.4)
    if v == 1:
        _gliss(B, penta('C5', 'C7'), 0.0, 0.85, lambda f, d: O2.celesta(f, d), 0.18, 0.4, accel=0.75)
        B.add(shimmer(1.6, 5000, 9000, 0.7, 0.5, 0.035))
        B.add(O2.ens((N('C4'), N('G4'), N('E5')), 1.0, att=0.6, rel=0.8, fc=1800.0, voices=3), 0.0, 0.25)
    else:
        _gliss(B, penta('C4', 'C6'), 0.0, 0.7, lambda f, d: O2.harp(round(f, 2), 1.6), 0.25, 0.45, accel=0.9, pan=0.4)
        for nm in ('C5', 'E5', 'G5'): B.add(O2.vibes(N(nm), 1.6), 0.78, 0.13)
        pad = O2.ens((N('C4'), N('E4'), N('G4')), 1.3, att=0.7, rel=0.9, fc=1600.0, voices=3)
        B.add(pad * (1 + 0.25 * np.sin(PI2 * 2.2 * np.arange(len(pad)) / SR))[:, None], 0.0, 0.25)
    return room(B.y, 1.4, 0.32, 7500.0)


@reg('imagine_out', '교실', '상상 나오기 반짝', '상상 장면을 마치고 교실로 돌아올 때(들어가기의 반대 방향)', '스르르 잦아드는 반짝임',
     [('별가루 내림', '첼레스타가 도7 → 도5로 느려지며 내려옴, 반짝임 바람이 잦아듦'),
      ('하프 내림 + 패드 사라짐', '하프 훑어 내리기 + 패드가 스르르 사라짐')],
     mix_db=-5)
def imagine_out(v):
    B = Buf(2.2)
    if v == 1:
        _gliss(B, penta('C5', 'C7')[::-1], 0.0, 0.9, lambda f, d: O2.celesta(f, d), 0.4, 0.18, accel=1.4)
        B.add(shimmer(1.2, 5000, 9000, 0.05, 0.35, 0.03))
    else:
        _gliss(B, penta('C4', 'C6')[::-1], 0.0, 0.75, lambda f, d: O2.harp(round(f, 2), 1.4), 0.45, 0.25, accel=1.2, pan=0.4)
        pad = O2.ens((N('C4'), N('E4'), N('G4')), 0.5, att=0.05, rel=1.4, fc=1500.0, voices=3)
        B.add(pad, 0.0, 0.22)
    return room(B.y, 1.2, 0.28, 7500.0)


@reg('card_pop', '교실', '카드 톡', '낱말 카드 · 정리 띠 · 쪽지가 화면에 뜰 때(아주 작게, 표시마다 붙이지 않기)', '작고 귀여운 톡',
     [('물방울 톡', '사인이 480 → 1,150 Hz로 순간 오르며 사라지는 물방울 소리'),
      ('나무 톡', '종이 위 펜 끝 같은 작은 나무 톡(낮은 몸통 + 아주 짧은 잡음)'),
      ('종 톡', '신스 벨 솔6을 아주 짧게 + 작은 나무 톡 받침')],
     mix_db=-8)
def card_pop(v):
    B = Buf(0.6)
    if v == 1: B.add(pop(480, 1150, 0.03, 0.15), 0, 0.8)
    elif v == 2:
        t = tt(0.2); tap = np.sin(PI2 * 640 * t) * env(t, 0.012, 0.0006) + 0.35 * np.sin(PI2 * 1500 * t) * env(t, 0.005, 0.0004)
        B.add(norm(lp(tap + 0.4 * bandnoise(len(t), 1500, 6000) * env(t, 0.0015, 0.0004), 6500)), 0, 0.8)
    else:
        t = tt(0.5); b = O2.bellpluck(N('G6'), 0.5) * np.exp(-t / 0.12)
        B.add(b, 0, 0.6); B.add(woodtick(700, 0.01, 0.3), 0, 0.3)
    return room(B.y, 0.3, 0.1)


@reg('marker', '교실', '마커 쓰는 소리', '화이트보드 · 칠판에 첫 획을 쓸 때(말이 없는 틈에 짧게, 말하는 동안은 끈다)', '사각사각, 바쁜 손',
     [('보드 마커 슥슥', '펠트 마커가 보드를 미는 소리 — 띠 잡음이 획 빠르기에 따라 흔들림'),
      ('분필 사각사각', '거친 알갱이 + 획 처음의 작은 톡'),
      ('연필 사각', '가는 알갱이 + 옅은 쉿 소리(가장 작고 가벼움)')],
     mix_db=-6, params=dict(strokes=3))
def marker(v, strokes=3):
    lens = [0.32, 0.2, 0.42, 0.26, 0.36, 0.18]
    tot = sum(lens[i % 6] + 0.09 for i in range(strokes)) + 0.15; t = tt(tot); n = len(t); y = np.zeros(n)
    a = 0.02
    for i in range(strokes):
        L = lens[i % 6]; m = (t >= a) & (t < a + L); u = np.clip((t - a) / L, 0, 1)
        e = (np.sin(np.pi * u) ** 0.6) * m
        if v == 1:
            fc = 2100 + 500 * np.sin(PI2 * (2.5 + i) * t + i) + 300 * np.sin(PI2 * 13 * t)
            seg = svf(rng.standard_normal(n) * e, fc, 1.6) + 0.35 * bandnoise(n, 3500, 8000) * e
            y += seg * (0.75 + 0.25 * np.sin(PI2 * 7 * t + i))
        elif v == 2:
            g = np.zeros(n); k = np.where(m & (rng.random(n) < 300 / SR))[0]; g[k] = rng.uniform(0.3, 1.0, len(k))
            g = O2.fftfilt(g, O2.chain(O2.g_hp(900, 2), O2.g_lp(5000, 2)))
            rough = O2.fftfilt(rng.standard_normal(n), O2.chain(O2.g_hp(1200, 2), O2.g_lp(5500, 2))) * (1 + 0.6 * np.sin(PI2 * 31 * t))
            i0 = int(a * SR); tk = woodtick(1500, 0.006, 0.8); g[i0:i0 + len(tk)] += 2.5 * tk[: n - i0]
            y += (norm(g) + 0.25 * norm(rough)) * np.maximum(e, (np.abs(t - a) < 0.02) * 1.0)
        else:
            g = np.zeros(n); k = np.where(m & (rng.random(n) < 520 / SR))[0]; g[k] = rng.uniform(0.4, 1.0, len(k))
            g = O2.fftfilt(g, O2.chain(O2.g_hp(2500, 2), O2.g_lp(8000, 2)))
            hiss = O2.fftfilt(rng.standard_normal(n), O2.chain(O2.g_hp(3000, 2), O2.g_lp(7500, 2)))
            y += (0.8 * norm(g) + 0.3 * norm(hiss)) * e
        a += L + 0.09
    y = O2.fftfilt(norm(y), O2.g_bell(5500, -3.0, 0.8))
    return room(y, 0.3, 0.08)


@reg('discovery_short', '교실', '발견의 순간(3초)', '"아하!" — 규칙 · 답을 찾아낸 순간(강의판용 짧은 판)', '차오르는 기쁨, 반짝이는 깨달음',
     [('하프 오름 + 화음 종', '하프가 솔3 → 도6을 훑어 오른 뒤 글로켄 도 · 미 · 솔 + 비브라폰 + 현 패드'),
      ('반짝 화음 패드', '현 패드(도 장조 9화음)가 차오르고 첼레스타가 반짝 오른 뒤 맑은 종'),
      ('마림바 달리기 + 종', '마림바가 도5 → 도7로 달려 올라가 비브라폰 화음과 종에 닿음')],
     mix_db=-5)
def discovery_short(v):
    B = Buf(3.0)
    if v == 1:
        _gliss(B, penta('G3', 'C6'), 0.0, 1.0, lambda f, d: O2.harp(round(f, 2), 1.8), 0.2, 0.42, accel=0.85, pan=0.45)
        for j, nm in enumerate(('C6', 'E6', 'G6')): B.add(glock_soft(N(nm), 1.9, 0.4), 1.05 + 0.03 * j, 0.24, pan=-0.3 + 0.3 * j)
        for nm in ('C5', 'E5', 'G5'): B.add(O2.vibes(N(nm), 1.9), 1.05, 0.12)
        B.add(O2.ens((N('C4'), N('G4'), N('E5')), 1.7, att=0.8, rel=0.9, fc=2000.0, voices=3), 0.2, 0.3)
    elif v == 2:
        B.add(O2.ens((N('C4'), N('G4'), N('B4'), N('D5'), N('E5')), 1.6, att=1.1, rel=1.0, fc=2200.0, voices=3), 0.0, 0.4)
        _gliss(B, penta('G5', 'G6'), 0.85, 0.4, lambda f, d: O2.celesta(f, d), 0.15, 0.3, accel=0.8)
        B.add(bell(N('C6'), 1.7), 1.3, 0.35); B.add(bell(N('G5'), 1.7), 1.32, 0.18)
    else:
        _gliss(B, penta('C5', 'C7'), 0.0, 0.8, lambda f, d: marimba(f, 0.7), 0.3, 0.55, accel=0.9, pan=0.4)
        for nm in ('C5', 'E5', 'G5', 'D6'): B.add(O2.vibes(N(nm), 2.0), 0.85, 0.12)
        B.add(bell(N('C7'), 1.8, 0.45), 0.86, 0.18); B.add(glock_soft(N('G6'), 1.6, 0.3), 0.9, 0.18)
        B.add(O2.ens((N('C4'), N('G4')), 1.4, att=0.5, rel=1.0, fc=1600.0, voices=3), 0.6, 0.22)
    y = room(B.y, 1.3, 0.3, 7500.0)
    f = int(0.6 * SR); y = y[: int(3.0 * SR)]; y[-f:] *= (np.cos(np.linspace(0, np.pi / 2, f)) ** 2)[:, None]
    return y


@reg('count_step', '교실', '하나씩 세기', '점 · 공 · 칸을 하나씩 세는 숫자 시범(셀 때마다 한 칸씩 올라가는 음)', '또박또박, 차곡차곡 올라감',
     [('마림바 통통', '마림바 5음 음계가 한 칸씩 올라감(파일은 다섯 걸음 시범, 한 음씩은 count_step(k=번호))'),
      ('오르골 띵띵', '오르골 음이 한 칸씩 올라감')],
     mix_db=-6, params=dict(steps=5, k=0))
def count_step(v, steps=5, k=0):
    notes = penta('C5', 'A6')
    seq = [k - 1] if k else list(range(steps))
    B = Buf(0.45 * (len(seq) - 1) + 1.2)
    for j, i in enumerate(seq):
        f = notes[min(i, len(notes) - 1)]
        if v == 1: B.add(marimba(f, 0.7), 0.45 * j, 0.6); B.add(glock_soft(2 * f, 0.4, 0.2), 0.45 * j, 0.06)
        else: B.add(musicbox(f, 1.0), 0.45 * j, 0.5)
    return room(B.y, 0.5, 0.15)


@reg('dot_tap', '교실', '점 찍기 톡', '그래프 · 지도에 점을 찍을 때(째깍이 점을 찍는 장면 등)', '작고 단정한 톡',
     [('펜 점 톡', '종이에 펜 끝이 톡 닿는 소리(케플러 깃펜 점을 조금 밝게)'),
      ('퐁 점(음 있음)', '솔5 사인이 살짝 내려앉는 작은 퐁 + 아주 작은 톡')],
     mix_db=-7)
def dot_tap(v):
    t = tt(0.25)
    if v == 1:
        tap = np.sin(PI2 * 620 * t) * env(t, 0.011, 0.0005) + 0.3 * np.sin(PI2 * 1480 * t) * env(t, 0.005, 0.0004)
        y = norm(lp(tap + 0.5 * bandnoise(len(t), 1500, 7000) * env(t, 0.0016, 0.0004), 6500))
    else:
        f = N('G5') * (1 + 0.3 * np.exp(-t / 0.008))
        y = np.sin(glide(f, t)) * env(t, 0.05, 0.001)
        tk = woodtick(1300, 0.005, 0.5); y[:len(tk)] += 0.2 * tk
    return room(y, 0.3, 0.1)


@reg('flag_plant', '교실', '깃발 꽂기', '지도 · 길에 깃발을 꽂을 때(관성 편 깃발)', '톡 꽂히고 살랑',
     [('톡 + 펄럭', '나무 막대가 톡 꽂히는 소리 + 천이 두어 번 펄럭'),
      ('톡 + 작은 띵', '톡 꽂히는 소리 + 글로켄 솔6 작은 띵')],
     mix_db=-6)
def flag_plant(v):
    B = Buf(0.9); t = tt(0.3)
    tap = (np.sin(PI2 * 320 * t) + 0.5 * np.sin(PI2 * 860 * t) * np.exp(-t / 0.015)) * env(t, 0.035, 0.0006)
    tap = norm(lp(tap + 0.5 * bandnoise(len(t), 600, 4000) * env(t, 0.003, 0.0005), 6000))
    B.add(tap, 0, 0.8)
    if v == 1:
        d = 0.45; tf = tt(d); n = len(tf)
        flap = bandnoise(n, 400, 3000) * (0.5 + 0.5 * np.sin(PI2 * (16 - 10 * tf / d) * tf)) ** 2 * np.exp(-tf / 0.16) * np.minimum(1, tf / 0.02)
        B.add(flap, 0.06, 0.35, pan=0.2)
    else:
        B.add(glock_soft(N('G6'), 0.8, 0.3), 0.05, 0.25)
    return room(B.y, 0.4, 0.12)


@reg('board_on', '교실', '전광판 불 켜짐', '전광판 · 화면 · 표가 켜질 때', '딸깍 하고 환해짐',
     [('딸깍 + 웅(부드럽게 켜짐)', '스위치 딸깍 + 낮은 웅 소리가 밝아지며 차오르다 잦아듦'),
      ('딸깍 + 삐삐빅(숫자 켜짐)', '스위치 딸깍 + 부드러운 전자음 세 개가 올라감(도6 · 미6 · 솔6)')],
     mix_db=-6)
def board_on(v):
    B = Buf(1.2)
    def click(f1, f2, amp, tau):
        t = tt(0.06); body = (np.sin(PI2 * f1 * t) + 0.5 * np.sin(PI2 * f2 * t)) * env(t, tau, 0.0004)
        return amp * norm(body + 0.8 * bandnoise(len(t), 900, 5000) * env(t, 0.0025, 0.0002))
    B.add(lp(click(1650, 3100, 0.8, 0.008), 5000), 0.0, 0.7); B.add(lp(click(2100, 3600, 1.0, 0.006), 5000), 0.05, 0.7)
    if v == 1:
        d = 0.9; t = tt(d); u = t / d
        hum = sum(a * np.sin(PI2 * h * 120 * t) for h, a in ((1, 1.0), (2, 0.5), (3, 0.3), (4, 0.15), (6, 0.08)))
        hum = lp(hum * (np.sin(np.pi * np.clip(u / 0.35, 0, 1) / 2) ** 2) * np.exp(-np.maximum(t - 0.3, 0) / 0.3), 1500)
        B.add(hum, 0.08, 0.35)
    else:
        for j, nm in enumerate(('C6', 'E6', 'G6')): B.add(blip(N(nm), 0.06, 0.5, 2400), 0.16 + 0.085 * j, 0.32)
    return room(B.y, 0.4, 0.12)


@reg('note_stick', '교실', '쪽지 붙이기', '쪽지 · 문제 카드가 보드에 탁 붙을 때(화이트보드 풀이 첫 장면)', '탁, 시작!',
     [('탁(종이 붙임)', '종이가 보드에 붙는 짧은 탁 + 낮은 툭'),
      ('탁 + 쓱(문질러 붙임)', '탁 붙인 뒤 손바닥으로 쓱 한 번 문지름')],
     mix_db=-5)
def note_stick(v):
    B = Buf(0.8); t = tt(0.25)
    slap = bandnoise(len(t), 500, 4000) * env(t, 0.008, 0.0004) + 0.7 * np.sin(PI2 * 180 * t) * env(t, 0.02, 0.001)
    B.add(norm(slap), 0, 0.85)
    if v == 2:
        d = 0.24; tf = tt(d); B.add(bandnoise(len(tf), 900, 5000) * np.sin(np.pi * tf / d) ** 1.2, 0.16, 0.25, pan=0.15)
    return room(B.y, 0.35, 0.1)


@reg('check_done', '교실', '확인 끝', '마지막 확인이 끝나 체크 표시를 할 때', '깔끔하게 끝, 뿌듯함',
     [('쓱 체크 + 띠링', '마커로 짧게 쓱-쓱 체크한 뒤 글로켄 미6 · 솔6 두 음'),
      ('도장 톡 + 딩', '나무 도장이 톡 찍히고 맑은 종 도6')],
     mix_db=-5)
def check_done(v):
    B = Buf(1.6)
    if v == 1:
        for a, L in ((0.0, 0.08), (0.1, 0.16)):
            d = L; t = tt(d); B.add(svf(rng.standard_normal(len(t)), 2400, 1.4) * np.sin(np.pi * t / d) ** 0.7, a, 0.35)
        B.add(glock_soft(N('E6'), 1.0, 0.35), 0.3, 0.35); B.add(glock_soft(N('G6'), 1.2, 0.35), 0.38, 0.4)
    else:
        t = tt(0.4)
        wood = (np.sin(PI2 * 410 * t) + 0.55 * np.sin(PI2 * 1030 * t) * np.exp(-t / 0.02)) * env(t, 0.045, 0.0006)
        thud = np.sin(PI2 * (95 + 40 * np.exp(-t / 0.01)) * t) * env(t, 0.06, 0.001)
        B.add(norm(wood + 0.8 * thud + 0.5 * bandnoise(len(t), 600, 4000) * env(t, 0.004, 0.0003)), 0, 0.7)
        B.add(bell(N('C6'), 1.2), 0.18, 0.4)
    return room(B.y, 0.6, 0.16)


# ───────────────────────── 예능 ─────────────────────────
@reg('ttiyong', '예능', '띠용', '어리둥절 · 갸우뚱한 순간, 물음표가 뜰 때', '용수철처럼 통통, 귀여운 당황',
     [('용수철 띠용', '음높이가 오른 뒤 출렁이며 잦아드는 용수철 소리(FM으로 띠잉 하는 결)'),
      ('물음표 띠요옹', '삼각파가 천천히 올라가며 크게 떨리는 "띠요오옹?"'),
      ('통통 용수철(zzfx)', 'zzfx 값 한 줄: zzfx(1,0,240,.01,.3,.3,0,1,12,0,0,0,.08,0,0,0,0,.7,.05) — 280 → 610 Hz 오름을 0.08초마다 되풀이(뾰옹뾰옹)')],
     mix_db=-4)
def ttiyong(v):
    B = Buf(1.3)
    if v == 1:
        d = 0.8; t = tt(d); f0 = 210 * (1 + 0.45 * (1 - np.exp(-t / 0.05)))
        f = f0 * (1 + 0.13 * np.exp(-t / 0.35) * np.sin(PI2 * 10 * t))
        ph = glide(f, t); I = 0.4 + 2.0 * np.exp(-t / 0.08)
        y = np.sin(ph + I * np.sin(2 * ph)) * env(t, 0.32, 0.004)
        B.add(lp(y, 3000), 0, 0.7)
    elif v == 2:
        d = 0.85; t = tt(d); f = 300 * (1 + 0.5 * (t / d) ** 1.4) * (1 + 0.06 * np.sin(PI2 * 6.5 * t))
        ph = glide(f, t); y = (2 / np.pi) * np.arcsin(np.sin(ph))
        y = y * np.minimum(1, t / 0.03) * np.minimum(1, (d - t) / 0.12).clip(0, 1)
        B.add(lp(y, 2400), 0, 0.6)
    else:
        B.add(lp(zz(1, 0, 240, .01, .3, .3, 0, 1, 12, 0, 0, 0, .08, 0, 0, 0, 0, .7, .05), 3500), 0, 0.7)
    return room(B.y, 0.45, 0.14)


@reg('pyororong', '예능', '뾰로롱', '반짝 등장 · 무언가가 짠 하고 나타날 때', '마법 같은 반짝, 사랑스러움',
     [('글로켄 뾰로롱', '부드러운 글로켄이 솔5 → 라6 5음 음계로 빠르게 오르고 꼭대기 음이 울림'),
      ('하프 + 첼레스타 반짝', '하프가 훑어 오르고 첼레스타가 꼭대기 세 음을 겹침 + 옅은 반짝임 바람'),
      ('오르골 트릴', '오르골이 솔5 → 솔6으로 오른 뒤 꼭대기에서 또르르 떨기')],
     mix_db=-4)
def pyororong(v):
    B = Buf(1.8)
    if v == 1:
        _gliss(B, penta('G5', 'A6'), 0.0, 0.3, lambda f, d: glock_soft(f, d, 0.35), 0.2, 0.42, accel=1.0, pan=0.5, dur=1.0)
    elif v == 2:
        ns = penta('C5', 'C7'); _gliss(B, ns, 0.0, 0.26, lambda f, d: O2.harp(round(f, 2), 1.2), 0.22, 0.4, pan=0.5)
        for j, f in enumerate(ns[-3:]): B.add(O2.celesta(f, 1.1), 0.18 + 0.04 * j, 0.25, pan=0.3 - 0.3 * j)
        B.add(shimmer(1.0, 5000, 9000, 0.2, 0.35, 0.035))
    else:
        _gliss(B, penta('G5', 'G6'), 0.0, 0.24, lambda f, d: musicbox(f, d), 0.25, 0.4, pan=0.4, dur=0.9)
        for j in range(8): B.add(musicbox(N('A6') if j % 2 == 0 else N('C7'), 0.5), 0.3 + 0.055 * j, 0.32 * (1 - j / 10))
    return room(B.y, 0.9, 0.25, 7500.0)


@reg('dudung', '예능', '두둥!', '놀라운 사실 · 반전이 나오기 직전/순간', '두근, 긴장되는 공개(무섭지 않게)',
     [('북 두둥', '팀파니 비슷한 북이 솔2 → 도2 두 번 + 낮은 현 받침'),
      ('건반 두둥', '피아노 낮은 옥타브 두 번(솔 → 도) + 현 받침'),
      ('신스 두둥', '부드러운 서브베이스 둥 · 둥 + 거른 톱니 플럭')],
     mix_db=-4)
def dudung(v):
    B = Buf(1.9)
    if v == 1:
        B.add(timp(N('G2'), 0.6, 0.7), 0.0, 0.7); B.add(timp(N('C2'), 1.6, 1.0), 0.22, 1.0)
        B.add(O2.ens((N('C3'), N('G3')), 0.8, att=0.05, rel=0.8, fc=1200.0, voices=3), 0.22, 0.3)
    elif v == 2:
        for f, a, g in ((N('G2'), 0.0, 0.7), (N('G1'), 0.0, 0.5), (N('C2'), 0.22, 0.9), (N('C3'), 0.22, 0.6)):
            B.add(lp(sat(O2.piano(round(f, 2), 0.4 if a == 0 else 1.2, 0.9), 1.3), 3000), a, g)
        B.add(O2.ens((N('C3'), N('G3'), N('C4')), 0.8, att=0.04, rel=0.8, fc=1400.0, voices=3), 0.22, 0.25)
    else:
        B.add(thump(85, 55, 0.12, 0.5), 0.0, 0.7); B.add(thump(75, 41, 0.45, 1.4, 2.5), 0.22, 1.0)
        B.add(lp(O2.sawpluck(N('C3'), 0.6, 2400.0, 500.0, 0.08, 0.4), 1800), 0.22, 0.35)
    return room(B.y, 0.9, 0.18, 6000.0)


@reg('ppabam', '예능', '빠밤!', '짠 하고 공개 · 결과 발표 · "정답은 바로!"', '신나는 짠!',
     [('금관 빠밤', '부드러운 금관 화음 짧게(솔 · 시 · 레) → 길게(도 · 미 · 솔 · 도)'),
      ('마림바 빠밤', '마림바 + 글로켄 화음 두 번 + 비브라폰 울림 + 옅은 심벌'),
      ('신스 짠!', '부드러운 톱니 플럭 화음 + 신스 벨 꼭대기 + 옅은 심벌')],
     mix_db=-4)
def ppabam(v):
    B = Buf(1.7); a1, a2 = 0.0, 0.16
    if v == 1:
        for nm in ('G4', 'B4', 'D5'): B.add(O2.brass(N(nm), 0.11, 0.7, 0.4), a1, 0.28)
        for nm in ('C5', 'E5', 'G5', 'C6'): B.add(O2.brass(N(nm), 0.85, 0.85, 0.35), a2, 0.26)
        B.y = lp(B.y, 5000)
    elif v == 2:
        for nm in ('G5', 'B5', 'D6'): B.add(marimba(N(nm), 0.3), a1, 0.35); B.add(glock_soft(N(nm), 0.3, 0.3), a1, 0.12)
        for nm in ('C6', 'E6', 'G6'): B.add(marimba(N(nm), 1.0), a2, 0.4); B.add(glock_soft(N(nm), 1.2, 0.3), a2, 0.15)
        for nm in ('C5', 'E5', 'G5'): B.add(O2.vibes(N(nm), 1.4), a2, 0.12)
        B.add(lp(O2.crash(1.2), 7000), a2, 0.08)
    else:
        for nm in ('G4', 'B4', 'D5'): B.add(lp(O2.sawpluck(N(nm), 0.1, 3000.0, 900.0), 3500), a1, 0.3)
        for nm in ('C5', 'E5', 'G5'): B.add(lp(O2.sawpluck(N(nm), 0.8, 3600.0, 900.0, 0.12, 0.5), 3800), a2, 0.32)
        B.add(O2.bellpluck(N('C6'), 1.2), a2, 0.3); B.add(lp(O2.crash(1.2), 7000), a2, 0.07)
    return room(B.y, 0.8, 0.2)


@reg('ppyong', '예능', '뿅', '캐릭터 · 물건이 순식간에 나타나거나 사라질 때', '가볍고 재빠른, 장난스러운',
     [('뿅(올라감, 나타남)', 'zzfx 값 한 줄: zzfx(1,0,300,.005,.04,.08,0,1,16,40)'),
      ('뿅(내려감, 사라짐)', 'zzfx 값 한 줄: zzfx(1,0,1150,.005,.05,.1,0,1,-13,-8)'),
      ('퐁퐁(물방울 둘)', '물방울 톡 두 번(높이 다르게)')],
     mix_db=-5)
def ppyong(v):
    B = Buf(0.6)
    if v == 1: B.add(lp(zz(1, 0, 300, .005, .04, .08, 0, 1, 16, 40), 4500), 0, 0.7)
    elif v == 2: B.add(lp(zz(1, 0, 1150, .005, .05, .1, 0, 1, -13, -8), 4500), 0, 0.7)
    else: B.add(pop(420, 980, 0.03, 0.15), 0, 0.7, pan=-0.2); B.add(pop(560, 1300, 0.03, 0.15), 0.09, 0.6, pan=0.2)
    return room(B.y, 0.35, 0.12)


@reg('ttoreureu', '예능', '또르르', '머쓱한 순간 · 썰렁한 농담 뒤 · 작은 실수(눈물 한 방울 또르르)', '머쓱, 귀여운 민망함',
     [('마림바 또르르(내려감)', '마림바가 미6에서 5음 음계로 점점 느려지며 내려옴'),
      ('첼레스타 또르르 + 똑', '첼레스타가 천천히 내려오다 물방울이 똑'),
      ('구슬 또르르(굴러감)', '작은 구슬이 통통 튀다 또르르 구르는 소리')],
     mix_db=-4)
def ttoreureu(v):
    B = Buf(1.8)
    if v == 1:
        ns = penta('E5', 'E6')[::-1]; at = 0.0
        for j, f in enumerate(ns): B.add(marimba(f, 0.6), at, 0.55 * (1 - 0.06 * j), pan=0.3 - 0.1 * j); at += 0.06 + 0.018 * j
    elif v == 2:
        ns = [N(x) for x in ('A6', 'G6', 'E6', 'D6', 'C6')]; at = 0.0
        for j, f in enumerate(ns): B.add(O2.celesta(f, 0.9), at, 0.4); at += 0.11 + 0.02 * j
        B.add(pop(1300, 620, 0.03, 0.16, up=False), at + 0.12, 0.5)
    else:
        gap, at, amp = 0.2, 0.0, 1.0
        while gap > 0.025 and at < 1.2:
            t = tt(0.08); f = 1400 + 200 * rng.random()
            tk = (np.sin(PI2 * f * t) + 0.4 * np.sin(PI2 * 2.6 * f * t) * np.exp(-t / 0.004)) * env(t, 0.012, 0.0004)
            B.add(lp(tk, 5000), at, 0.5 * amp); at += gap; gap *= 0.78; amp *= 0.88
    return room(B.y, 0.5, 0.15)


@reg('kung', '예능', '쿵', '충격 · 깨달음 · 무거운 결론이 툭 떨어질 때', '묵직하지만 둥근 쿵',
     [('묵직한 쿵', '음높이가 툭 떨어지는 낮은 쿵 + 방 울림(휴대폰에서도 들리게 배음을 더함)'),
      ('쿵 + 울림', '쿵 뒤에 낮은 현이 길게 울림'),
      ('쿵 → 반짝(깨달음)', '부드러운 쿵 뒤에 글로켄 미6 · 라6 반짝')],
     mix_db=-4)
def kung(v):
    B = Buf(2.0)
    if v == 1: B.add(thump(90, 42, 0.32, 1.3, 2.4, 0.04), 0, 1.0)
    elif v == 2:
        B.add(thump(85, 44, 0.25, 1.0, 2.2, 0.04), 0, 0.9)
        B.add(O2.ens((N('C2'), N('G2'), N('C3')), 0.6, att=0.03, rel=1.2, fc=900.0, voices=3), 0.0, 0.45)
    else:
        B.add(thump(80, 48, 0.18, 0.7, 2.0), 0, 0.8)
        B.add(glock_soft(N('E6'), 1.1, 0.35), 0.28, 0.3); B.add(glock_soft(N('A6'), 1.2, 0.35), 0.36, 0.3)
    return room(B.y, 0.9, 0.18, 6000.0)


@reg('ppibik', '예능', '삐빅', '기계 판정 · 검사기 · 로봇이 답을 낼 때', '또랑또랑 전자음(날카롭지 않게)',
     [('삐빅(맞아요, 높게 두 번)', '부드러운 전자음 미6 · 라6 짧게 두 번'),
      ('삐-빅(아니에요, 내려감)', '라5를 조금 길게 → 미5 짧게, 둥근 전자음'),
      ('로봇 삐빅삐빅', 'zzfx 사각파 여덟 개가 도5 ~ 도6 5음 음계로 재잘(값 한 줄: zzfx(.6,0,<음>,.002,.03,.015,5,1,0,0,0,0,0,0,0,0,0,1,0,0,900)) — 생각하는 기계')],
     mix_db=-6)
def ppibik(v):
    B = Buf(1.0)
    if v == 1:
        for a, nm in ((0.0, 'E6'), (0.11, 'A6')):
            t = tt(0.07); f = N(nm); y = (np.sin(PI2 * f * t) + 0.15 * np.sin(PI2 * 2 * f * t)) * np.minimum(1, t / 0.003) * np.clip((0.07 - t) / 0.01, 0, 1)
            B.add(y, a, 0.5)
    elif v == 2:
        for a, nm, d in ((0.0, 'A5', 0.15), (0.2, 'E5', 0.1)): B.add(blip(N(nm), d, 0.5, 2000), a, 0.45)
    else:
        ns = penta('C5', 'C6'); r = np.random.default_rng(7)
        for j in range(8):
            f = ns[int(r.integers(len(ns)))]
            B.add(lp(zz(.6, 0, f, .002, .03, .015, 5, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 900), 2200), 0.065 * j, 0.45)
    return room(B.y, 0.3, 0.1)


@reg('hwiik', '예능', '휘익', '빠른 움직임 · 휙 지나가기 · 재빨리 돌아보기', '날렵하고 상쾌',
     [('바람 휘익', '통과 대역이 700 → 2,800 → 1,000 Hz로 빠르게 휘는 바람, 왼쪽→오른쪽'),
      ('휘파람 휘익(올라감)', '부드러운 휘파람이 700 → 1,900 Hz로 쓱 올라감 + 숨소리'),
      ('쌩(지나감)', '삼각파 소리가 다가왔다 멀어지며 음이 떨어짐(도플러) + 바람, 왼쪽→오른쪽')],
     mix_db=-5)
def hwiik(v):
    B = Buf(1.0)
    if v == 1:
        d = 0.32; t = tt(d); u = t / d; fc = np.where(u < 0.5, 700 * (2800 / 700) ** (u / 0.5), 2800 * (1000 / 2800) ** ((u - 0.5) / 0.5))
        e = np.sin(np.pi * u) ** 1.3; B.add(pan_move(norm(svf(rng.standard_normal(len(t)), fc, 1.1)) * e, -0.8, 0.8))
    elif v == 2:
        d = 0.22; t = tt(d); u = t / d; f = 700 * (1900 / 700) ** (u ** 0.8)
        y = np.sin(glide(f, t)) * np.sin(np.pi * np.clip(u * 1.1, 0, 1)) ** 0.8 + 0.08 * bandnoise(len(t), 1500, 6000) * np.sin(np.pi * u)
        B.add(lp(y, 4000), 0, 0.5)
    else:
        d = 0.6; t = tt(d); u = t / d; x = (u - 0.5) * 4; vr = x / np.sqrt(1 + x * x)
        f = 520 * (1 - 0.12 * vr); ph = glide(f, t); y = (2 / np.pi) * np.arcsin(np.sin(ph))
        amp = 1 / (1 + x * x) ** 0.8
        y = lp(y * amp, 2600) + 0.5 * norm(svf(rng.standard_normal(len(t)), 1200 + 1500 * amp, 1.0)) * amp
        B.add(pan_move(y, -0.8, 0.8), 0, 0.6)
    return room(B.y, 0.4, 0.12)


@reg('kkwagwang', '예능', '꽈광', '작은 폭발 · 대성공 · 실험이 펑 하고 될 때(무섭지 않게)', '펑! 하고 신남',
     [('펑 + 반짝', '둥글게 거른 펑(구름 퍼지는 소리) + 낮은 쿵 + 글로켄 반짝 다섯'),
      ('축하 꽈광', '북 · 작은북 + 옅은 심벌 + 금관 도 · 미 · 솔 화음'),
      ('폭죽 퐁퐁팡', '작은 폭죽이 퐁 · 퐁 · 팡 터지고 반짝이는 알갱이가 흩어짐')],
     mix_db=-5)
def kkwagwang(v):
    B = Buf(2.0)
    if v == 1:
        d = 0.9; t = tt(d); burst = lp(rng.standard_normal(len(t)), 1100) * env(t, 0.16, 0.004)
        B.add(norm(burst), 0, 0.7); B.add(thump(80, 50, 0.15, 0.5), 0, 0.6)
        ns = penta('E6', 'E7')
        for j in range(5): B.add(glock_soft(ns[int(rng.integers(len(ns)))], 0.9, 0.25), 0.12 + 0.09 * j, 0.18, pan=float(rng.uniform(-0.7, 0.7)))
    elif v == 2:
        B.add(lp(O2.kick2(110, 50, 0.03, 0.2), 3000), 0, 0.7); B.add(lp(O2.snare2(), 6000), 0, 0.35); B.add(lp(O2.crash(1.6), 6500), 0.0, 0.12)
        for nm in ('C5', 'E5', 'G5'): B.add(O2.brass(N(nm), 0.6, 0.8, 0.4), 0.02, 0.25)
        B.y = lp(B.y, 6000)
    else:
        for j, a in enumerate((0.0, 0.26, 0.55)):
            d = 0.5; t = tt(d); p = lp(rng.standard_normal(len(t)), 1800 + 500 * j) * env(t, 0.03 + 0.02 * j, 0.002)
            crack = np.zeros(len(t)); k = np.where((rng.random(len(t)) < 120 / SR) & (t > 0.04))[0]; crack[k] = rng.uniform(0.2, 0.7, len(k))
            crack = lp(hp(crack, 1500), 6000) * np.exp(-t / 0.18)
            B.add(norm(p) + 0.6 * norm(crack), a, 0.5 + 0.15 * j, pan=(-0.5, 0.4, 0.0)[j])
        for j in range(4): B.add(O2.celesta(penta('C6', 'C7')[int(rng.integers(6))], 0.8), 0.6 + 0.07 * j, 0.15, pan=float(rng.uniform(-0.6, 0.6)))
    return room(B.y, 0.9, 0.2, 6500.0)


@reg('laugh_rhythm', '예능', '웃음 포인트 리듬', '농담 · 말장난 뒤, 웃음 포인트를 짚을 때', '장난스럽고 가벼운 마무리',
     [('쿵짝 칭(드럼)', '북 두 번(높게 · 낮게) 뒤 옅은 심벌 칭'),
      ('장난감 삑삑 짠', '장난감 피리 같은 부드러운 사각파 미5 · 솔5 · 미5 · 도6'),
      ('통통통 띵(피치카토)', '현 피치카토 도4 · 미4 · 솔4, 한 박 쉬고 도5 띵')],
     mix_db=-4)
def laugh_rhythm(v):
    B = Buf(1.7)
    if v == 1:
        B.add(lp(O2.kick2(190, 120, 0.02, 0.12, 0.1, 0.4), 4000), 0.0, 0.55); B.add(lp(O2.kick2(150, 95, 0.02, 0.16, 0.1, 0.4), 4000), 0.17, 0.6)
        B.add(lp(O2.hat(0.28, 6000, 11000), 9000), 0.42, 0.35); B.add(lp(O2.crash(1.0), 8000), 0.42, 0.08)
    elif v == 2:
        for j, (nm, d) in enumerate((('E5', 0.1), ('G5', 0.1), ('E5', 0.1), ('C6', 0.3))):
            t = tt(d); f = N(nm) * (1 + 0.012 * np.sin(PI2 * 9 * t)); y = np.tanh(3 * np.sin(glide(f, t))) * np.minimum(1, t / 0.006) * np.clip((d - t) / 0.02, 0, 1)
            B.add(lp(y, 2400), 0.13 * j, 0.4)
    else:
        for j, nm in enumerate(('C4', 'E4', 'G4')): B.add(O2.pizz(N(nm), 0.6, 3, 0.8), 0.14 * j, 0.6)
        B.add(O2.pizz(N('C5'), 0.9, 3, 0.9), 0.62, 0.65); B.add(glock_soft(N('C6'), 0.9, 0.3), 0.62, 0.15)
    return room(B.y, 0.5, 0.15)


@reg('heartbeat', '예능', '두근두근 심장', '설렘 · 긴장 · 결과를 기다리는 순간(두근두근러닝!)', '두근두근, 콩닥콩닥',
     [('차분한 두근(72)', '쿵-쿵 두 박(첫 박 크게) 1분에 72번, 네 번'),
      ('콩닥콩닥 빠른(124)', '1분에 124번, 여섯 번'),
      ('점점 빨라지는 두근', '70 → 140으로 빨라지는 여덟 번')],
     mix_db=-4, params=dict(beats=0, bpm=0))
def heartbeat(v, beats=0, bpm=0):
    if v == 1: bs = [bpm or 72] * (beats or 4)
    elif v == 2: bs = [bpm or 124] * (beats or 6)
    else:
        nb = beats or 8; bs = list(np.linspace(70, bpm or 140, nb))
    tot = sum(60 / b for b in bs) + 0.6; B = Buf(tot); at = 0.0
    for b in bs:
        lub = thump(72, 48, 0.07, 0.3, 2.6, 0.02); dub = thump(84, 56, 0.06, 0.25, 2.4, 0.02)
        gap = min(0.3, 0.38 * 60 / b)
        B.add(lub, at, 1.0); B.add(dub, at + gap, 0.7); at += 60 / b
    return room(B.y, 0.4, 0.08, 4000.0)


@reg('applause', '예능', '박수 · 환호', '발표를 마쳤을 때 · 축하 · 친구를 응원할 때(합성이라 진짜 군중 녹음보다 단순)', '따뜻한 응원',
     [('교실 박수', '열여섯 명쯤 2.5초'),
      ('큰 박수', '마흔다섯 명쯤 3.5초, 차올랐다 잦아듦'),
      ('박수 + 와아 환호', '교실 박수 + 여러 목소리의 "와아"(모음 울림을 거른 합성 — 가볍게 깔기)')],
     mix_db=-6)
def applause(v):
    people, dur = {1: (16, 2.5), 2: (45, 3.5), 3: (18, 2.8)}[v]
    shapes = [clap_shape(900 + 1500 * (k / 23), 300 + k) for k in range(24)]
    B = Buf(dur + 0.6); r = np.random.default_rng(40 + v)
    for p in range(people):
        rate = r.uniform(3.2, 5.0); at = r.uniform(0, 0.35); pan = r.uniform(-0.85, 0.85); g = r.uniform(0.5, 1.0); sh = shapes[int(r.integers(24))]
        stop = dur - r.uniform(0.2, 0.9)
        while at < stop:
            u = at / dur; e = min(1.0, at / 0.4) * (1 - max(0, u - 0.6) / 0.4 * 0.85)
            B.add(sh, at, 0.25 * g * e, pan=pan); at += 1 / rate * r.uniform(0.85, 1.15)
    if v == 3:
        d = 2.2; t = tt(d); voices = np.zeros(len(t))
        for k in range(14):
            f0 = r.uniform(170, 340); on = r.uniform(0.1, 0.5); tv = np.clip(t - on, 0, None)
            f = f0 * (1 + 0.12 * (1 - np.exp(-tv / 0.15))) * (1 + 0.015 * np.sin(PI2 * r.uniform(4.5, 6) * t))
            saw = 2 * ((np.cumsum(f) / SR) % 1.0) - 1
            e = np.clip(tv / 0.25, 0, 1) * np.exp(-np.maximum(tv - 0.7, 0) / 0.6) * (t > on)
            voices += saw * e * r.uniform(0.6, 1.0)
        formant = O2.chain(O2.g_lp(3000, 2), O2.g_bell(800, 10, 0.35), O2.g_bell(1250, 8, 0.3), O2.g_bell(2600, 3, 0.3))
        vo = O2.fftfilt(voices, formant) + 0.3 * bandnoise(len(t), 400, 3000) * np.max(np.abs(voices)) * 0.1
        B.add(norm(vo) * 0.45, 0.25, 1.0)
    return room(B.y, 0.8, 0.2)


@reg('drumroll', '예능', '두구두구 → 짠', '결과 발표 직전 두구두구, 공개 순간 짠(공개 순간 = dur초)', '두근두근 기대 → 짠!',
     [('작은북 두구두구 → 짠', '작은북 굴림이 점점 커진 뒤 북 + 옅은 심벌 + 글로켄 화음'),
      ('탐탐 두구두구 → 빠밤', '북 두 개를 번갈아 굴린 뒤 마림바 · 글로켄 빠밤')],
     mix_db=-5, params=dict(dur=1.6))
def drumroll(v, dur=1.6):
    B = Buf(dur + 1.6); r = np.random.default_rng(9)
    if v == 1:
        rate = 22.0; n = int(dur * rate)
        for j in range(n):
            a = j / rate; u = a / dur; g = (0.25 + 0.75 * u ** 1.5) * (1.0 if j % 2 == 0 else 0.8) * r.uniform(0.9, 1.1)
            B.add(lp(O2.snare2(200, 0.03, 0.06, 1500, 7000, 0.75, 0.2), 6500), a, 0.32 * g, pan=0.1 if j % 2 else -0.1)
        B.add(lp(O2.kick2(110, 50, 0.03, 0.2), 3000), dur, 0.6); B.add(lp(O2.crash(1.4), 6500), dur, 0.12)
        for j, nm in enumerate(('C6', 'E6', 'G6', 'C7')): B.add(glock_soft(N(nm), 1.3, 0.35), dur + 0.01 * j, 0.18)
    else:
        rate = 14.0; n = int(dur * rate)
        for j in range(n):
            a = j / rate; u = a / dur; g = (0.3 + 0.7 * u ** 1.3) * r.uniform(0.9, 1.1)
            f0 = 170 if j % 2 == 0 else 135
            B.add(lp(O2.kick2(f0, f0 * 0.62, 0.02, 0.12, 0.08, 0.3), 4000), a, 0.45 * g, pan=-0.3 if j % 2 == 0 else 0.3)
        for nm in ('G5', 'B5', 'D6'): B.add(marimba(N(nm), 0.3), dur - 0.16, 0.35)
        for nm in ('C6', 'E6', 'G6'): B.add(marimba(N(nm), 1.0), dur, 0.42); B.add(glock_soft(N(nm), 1.2, 0.3), dur, 0.15)
    return room(B.y, 0.7, 0.16)


@reg('ttaeng', '예능', '땡', '틀렸을 때 · 시간 끝(종 한 번, 가볍게)', '아쉬움, 하지만 웃으며',
     [('땡(종 한 번)', '손종 미5 한 번이 길게 잦아듦'),
      ('땡땡(두 번)', '손종 미5 두 번')],
     mix_db=-5)
def ttaeng(v):
    B = Buf(1.9); B.add(handbell(N('E5'), 1.6), 0, 0.6)
    if v == 2: B.add(handbell(N('E5'), 1.6), 0.2, 0.55)
    return room(B.y, 0.7, 0.15)


@reg('idea_tiring', '예능', '띠링(아이디어)', '좋은 생각이 번뜩 떠오를 때 · 전구가 켜질 때', '반짝, 번뜩!',
     [('띠링(두 음)', '글로켄 + 첼레스타 미6 → 시6 두 음'),
      ('쓱 + 반짝 띠링', '아주 짧게 쓱 올라간 뒤 신스 벨 도6 · 솔6 + 옅은 반짝임')],
     mix_db=-4)
def idea_tiring(v):
    B = Buf(1.6)
    if v == 1:
        for a, nm in ((0.0, 'E6'), (0.08, 'B6')): B.add(glock_soft(N(nm), 1.1, 0.35), a, 0.32); B.add(O2.celesta(N(nm), 1.1), a, 0.3)
    else:
        d = 0.14; t = tt(d); u = t / d; B.add(norm(svf(rng.standard_normal(len(t)), 1200 * 4 ** u, 1.4)) * u ** 1.5, 0, 0.25)
        B.add(O2.bellpluck(N('C6'), 1.2), d, 0.4); B.add(O2.bellpluck(N('G6'), 1.2), d + 0.07, 0.38); B.add(shimmer(0.9, 5000, 9000, 0.1, 0.3, 0.035), d)
    return room(B.y, 0.7, 0.18)


# ═════════════════════════ 마무리 · 음량 ═════════════════════════
def finish(y, low=False, tail_db=-60.0):
    """말소리 대역 덜기(3 kHz −4 dB) · 아주 높은 소리 살짝 · 낮은 웅웅 거르기 → 꼬리 자르기 → 앞뒤 페이드(클릭 없음)."""
    y = to_st(y)
    y = O2.fftfilt(y, O2.chain(O2.g_hp(32 if low else 50, 2), O2.g_bell(3000, -4.0, 0.7), O2.g_shelf(10000, -2.0)))
    a = np.max(np.abs(y), axis=1); thr = a.max() * 10 ** (tail_db / 20); idx = np.where(a > thr)[0]
    end = min(len(y), int(idx[-1]) + int(0.03 * SR)) if len(idx) else len(y)
    y = y[:end].copy()
    fi = int(0.0015 * SR); y[:fi] *= (np.sin(np.linspace(0, np.pi / 2, fi)) ** 2)[:, None]
    fo = min(len(y) // 3, int(0.04 * SR)); y[-fo:] *= (np.cos(np.linspace(0, np.pi / 2, fo)) ** 2)[:, None]
    y[0] = 0; y[-1] = 0
    return y


def k_weight(x):
    n = len(x); nf = 1 << int(np.ceil(np.log2(n + 8192)))
    z1 = np.exp(-1j * PI2 * np.fft.rfftfreq(nf)); z2 = z1 * z1
    H = ((1.53512485958697 - 2.69169618940638 * z1 + 1.19839281085285 * z2) / (1 - 1.69065929318241 * z1 + 0.73248077421585 * z2)
         * (1 - 2 * z1 + z2) / (1 - 1.99004745483398 * z1 + 0.99007225036621 * z2))
    return np.stack([np.fft.irfft(np.fft.rfft(x[:, c], nf) * H, nf)[:n] for c in (0, 1)], 1)


def momentary_max(y):
    """K 가중 400 ms 창(10 ms 간격)의 최댓값(LUFS). 짧은 소리는 앞뒤 0.5초를 0으로 채워 잰다(케플러 sfx.py 와 같은 잣대)."""
    y = to_st(y); pad = int(0.5 * SR); x = np.zeros((len(y) + 2 * pad, 2)); x[pad:pad + len(y)] = y
    k = k_weight(x); blk = int(0.4 * SR); hop = int(0.01 * SR)
    c = np.concatenate([[0.0], np.cumsum((k ** 2).sum(1))])
    p = (c[blk::hop][: (len(k) - blk) // hop + 1] - c[0:len(k) - blk + 1:hop][: (len(k) - blk) // hop + 1]) / blk
    return float(-0.691 + 10 * np.log10(p.max() + 1e-12))


def true_peak_db(y):
    y = to_st(y); n = len(y); nf = 1 << int(np.ceil(np.log2(n + 2048)))
    X = np.fft.rfft(y, nf, axis=0); up = np.fft.irfft(X, 4 * nf, axis=0) * 4
    return float(20 * np.log10(np.max(np.abs(up)) + 1e-12))


def level(y):
    g = 10 ** ((TARGET_M - momentary_max(y)) / 20); y = y * g
    tp = true_peak_db(y); capped = tp > TP_CAP
    if capped: y = y * 10 ** ((TP_CAP - tp) / 20)
    return y, capped


LOW = {'dudung', 'kung', 'heartbeat', 'kkwagwang', 'drumroll', 'laugh_rhythm'}


def make(base, v, leveled=True, **kw):
    s = get(base); reseed(int(hashlib.md5(f"{base}{v}".encode()).hexdigest()[:6], 16))
    p = dict(s['params']); p.update(kw)
    y = finish(s['fn'](v, **p), low=base in LOW)
    return level(y)[0] if leveled else y


def write_wav(path, y):
    y = np.clip(to_st(y), -1, 1); tmp = path + '.tmp.wav'
    with wave.open(tmp, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(np.round(y * 32767).astype('<i2').tobytes())
    os.replace(tmp, path)


def ff_measure(path):
    """ffmpeg ebur128: 순간 음량 최댓값(M) · 트루 피크. 뒤에 0.6초 무음을 붙여 잰다."""
    r = subprocess.run(['ffmpeg', '-v', 'verbose', '-nostats', '-hide_banner', '-i', path, '-af', 'apad=pad_dur=0.6,ebur128=peak=true:framelog=verbose',
                        '-f', 'null', '-'], capture_output=True, text=True)
    M = [float(x.split('M:')[1].split()[0]) for x in r.stderr.splitlines() if 'TARGET:' in x and 'M:' in x]
    tp = None
    lines = r.stderr.splitlines()
    for i, x in enumerate(lines):
        if 'True peak:' in x:
            for z in lines[i + 1:i + 3]:
                if 'Peak:' in z: tp = float(z.split('Peak:')[1].split()[0])
    return (max(M) if M else None), tp


def encode(wav, m4a, mp3):
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', wav, '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', m4a], check=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', wav, '-c:a', 'libmp3lame', '-b:a', '192k', mp3], check=True)


def all_items():
    for s in SOUNDS:
        for v, (vt, how) in enumerate(s['variants'], 1):
            yield s, v, vt, how


def build(only=None):
    for d in ('wav', 'm4a', 'mp3'): os.makedirs(os.path.join(OUT, d), exist_ok=True)
    jpath = os.path.join(OUT, 'sounds.json')
    old = {e['id']: e for e in json.load(open(jpath))} if (only and os.path.exists(jpath)) else {}
    rows = []
    for s, v, vt, how in all_items():
        sid = f"sfx_{s['base']}_{v}"
        if only and s['base'] not in only:
            if sid in old: rows.append(old[sid])
            continue
        y = make(s['base'], v, leveled=False); y, capped = level(y)
        w = os.path.join(OUT, 'wav', sid + '.wav'); m = os.path.join(OUT, 'm4a', sid + '.m4a'); p = os.path.join(OUT, 'mp3', sid + '.mp3')
        write_wav(w, y); encode(w, m, p)
        mm, tp_w = ff_measure(w); _, tp_m = ff_measure(m); _, tp_p = ff_measure(p)
        e0 = float(np.max(np.abs(y[0]))); e1 = float(np.max(np.abs(y[-1]))); e10 = float(np.max(np.abs(y[-int(0.01 * SR):])))
        params = ', '.join(f'{k}={val}' for k, val in s['params'].items())
        row = dict(
            id=sid, kind='sfx', style=s['style'], group=f"sfx_{s['base']}", variant=v, variants=len(s['variants']),
            title=f"{s['title']} {v}", variant_title=vt, desc=how,
            file=f'wav/{sid}.wav', preview=f'm4a/{sid}.m4a', mp3=f'mp3/{sid}.mp3',
            seconds=round(len(y) / SR, 2), situation=s['situation'], mood=s['mood'],
            made_by=f"numpy 직접 합성 — {how}", tool=f"tools/sound/sfx_class.py make('{s['base']}', {v}{', ' + params if params else ''})",
            mix_db=s['mix_db'], lufs=round(momentary_max(y), 1), lufs_ffmpeg=mm,
            lufs_basis='순간 음량 최댓값(400 ms 창, BS.1770 K 가중, 뒤에 0.6초 무음) — 짧은 소리라 통합 음량 대신. 목표 −20, 트루 피크 −1.5 dBTP 상한에 걸리면 더 작음',
            peak_capped=bool(capped), true_peak_db=dict(wav=tp_w, m4a=tp_m, mp3=tp_p),
            edges=dict(first_sample=round(e0, 5), last_sample=round(e1, 5), last_10ms_max=round(e10, 5), fade_in_ms=1.5, fade_out_ms=40),
            format='wav 48 kHz · 16비트 · 스테레오 / m4a aac 192k / mp3 192k', date='2026-11-18',
            license='CC BY-NC 4.0', credit='두근두근러닝(greatsong)', uses_zzfx=('zzfx' in how),
            sha1=hashlib.sha1(open(w, 'rb').read()).hexdigest(), bytes=os.path.getsize(w),
            status='후보 — PD님이 아직 고르지 않음', used_in=[])
        rows.append(row)
        print(f"{sid:24s} {row['seconds']:5.2f}초  M {row['lufs']:6.1f} (ffmpeg {mm})  TP wav {tp_w} m4a {tp_m} mp3 {tp_p}{'  [상한]' if capped else ''}")
    json.dump(rows, open(jpath, 'w'), ensure_ascii=False, indent=1)
    return rows


def sheet(rows):
    """스펙트로그램 모음(눈으로 확인용) → sheet.jpg"""
    from PIL import Image, ImageDraw, ImageFont
    font = _font('NotoSansKR-700.ttf', 15)
    cw, ch, cols = 330, 150, 6; n = len(rows); H = ((n + cols - 1) // cols) * ch
    im = Image.new('RGB', (cw * cols, H), (250, 247, 240)); dr = ImageDraw.Draw(im)
    for i, r in enumerate(rows):
        with wave.open(os.path.join(OUT, r['file'])) as w: y = np.frombuffer(w.readframes(w.getnframes()), '<i2').reshape(-1, 2).mean(1) / 32767
        nfft, hop = 1024, 256; fr = max(1, (len(y) - nfft) // hop)
        S = np.array([np.abs(np.fft.rfft(y[k * hop:k * hop + nfft] * np.hanning(nfft)))[:384] for k in range(fr)]).T if len(y) > nfft else np.zeros((384, 1))
        D = np.clip((20 * np.log10(S + 1e-6) + 55) / 70, 0, 1)
        img = Image.fromarray((255 * (1 - D[::-1])).astype(np.uint8)).resize((cw - 12, ch - 34))
        x0, y0 = (i % cols) * cw, (i // cols) * ch
        im.paste(Image.merge('RGB', (img, img, img)), (x0 + 6, y0 + 28))
        dr.text((x0 + 6, y0 + 4), f"{r['id'][4:]} · {r['seconds']}초 · 0~9 kHz", fill=(40, 40, 60), font=font)
    im.save(os.path.join(OUT, 'sheet.jpg'), quality=85)


# ═════════════════════════ 듣기 모음 영상 ═════════════════════════
def read_wav(path):
    with wave.open(path) as w: return np.frombuffer(w.readframes(w.getnframes()), '<i2').reshape(-1, 2) / 32767.0


def preview(out_path=None, max_mb=30.0):
    """듣기 모음 영상(720p): 소개 → [교실] 예시 장면(퀴즈) + 효과음마다 한 장 → [예능] 예시 장면(놀라운 사실) + 한 장씩.
    효과음은 만들어 둔 wav 그대로(실제로 쓸 크기, 순간 음량 최댓값 −20 LUFS) 들려준다. 30 MB 를 넘으면 두 개로 나눈다."""
    import shutil, tempfile
    from PIL import Image, ImageDraw, ImageFont
    rows = json.load(open(os.path.join(OUT, 'sounds.json')))
    W, H = 1280, 720
    FD = os.path.join(KIT, 'engine', 'fonts')
    F = lambda name, sz: _font(name, sz)
    jua = lambda sz: F('Jua-Regular.ttf', sz)
    b7 = lambda sz: F('NotoSansKR-700.ttf', sz)
    b9 = lambda sz: F('NotoSansKR-900.ttf', sz)
    BG, CARD, INK, SUB = (255, 248, 236), (255, 255, 255), (38, 38, 56), (78, 78, 98)
    GC = {'교실': (52, 120, 200), '예능': (214, 84, 72)}
    chars = {k: Image.open(os.path.join(REPO, 'characters', f'char_{n}.png')).convert('RGBA') for k, n in (('교실', 'chorong'), ('예능', 'dugeun'))}   # 저장소 사본: characters/
    tmp = tempfile.mkdtemp(prefix='sfx_preview_')
    frames, events = [], []           # frames: (png, 초) · events: (시각, 스테레오 소리)
    clock = [0.0]

    def wrap(dr, text, font, width):
        out, cur = [], ''
        for word in text.split(' '):
            t = (cur + ' ' + word).strip()
            if dr.textlength(t, font=font) <= width: cur = t
            else:
                if cur: out.append(cur)
                cur = word
                while dr.textlength(cur, font=font) > width:      # 띄어쓰기 없이 긴 줄
                    k = len(cur)
                    while dr.textlength(cur[:k], font=font) > width: k -= 1
                    out.append(cur[:k]); cur = cur[k:]
        if cur: out.append(cur)
        return out

    def canvas(bg=BG):
        im = Image.new('RGB', (W, H), bg); return im, ImageDraw.Draw(im)

    def rrect(dr, box, r, fill, outline=None, width=0):
        dr.rounded_rectangle(box, r, fill=fill, outline=outline, width=width)

    def chip(dr, x, y, text, col, font=None):
        font = font or b7(24); w = dr.textlength(text, font=font)
        rrect(dr, (x, y, x + w + 36, y + 44), 22, col); dr.text((x + 18, y + 22), text, font=font, fill=(255, 255, 255), anchor='lm')
        return x + w + 36

    def put_char(im, style, h=170, x=None, y=None):
        c = chars[style]; c = c.resize((int(c.width * h / c.height), h), Image.LANCZOS)
        im.paste(c, (x if x is not None else W - c.width - 30, y if y is not None else H - h - 18), c)

    def push(im, dur):
        p = os.path.join(tmp, f'f{len(frames):04d}.png'); im.save(p); frames.append((p, dur)); clock[0] += dur

    def wavebar(dr, y, box, col):
        x0, y0, x1, y1 = box; m = y.mean(1); n = x1 - x0
        k = max(1, len(m) // n); e = np.abs(m[: k * n]).reshape(-1, k).max(1) if len(m) >= n else np.abs(m)
        e = e / (e.max() + 1e-9); mid = (y0 + y1) / 2; hh = (y1 - y0) / 2
        for i, v in enumerate(e[:n]):
            a = max(1.0, v * hh); dr.line((x0 + i, mid - a, x0 + i, mid + a), fill=col, width=1)

    # ── 소개 ──
    styles = [('교실', [r for r in rows if r['style'] == '교실']), ('예능', [r for r in rows if r['style'] == '예능'])]
    im, dr = canvas()
    dr.text((W / 2, 150), '두근두근러닝 효과음 듣기', font=jua(72), fill=INK, anchor='mm')
    n1, n2 = (len({r['group'] for r in g}) for _, g in styles)
    dr.text((W / 2, 250), f"교실 묶음 {n1}가지({len(styles[0][1])}개)  ·  예능 묶음 {n2}가지({len(styles[1][1])}개)", font=b7(34), fill=SUB, anchor='mm')
    for i, ln in enumerate(['효과음마다 1 · 2 · 3번 판을 차례로 들려 드려요. 마음에 드는 번호를 골라 주세요.',
                            '모두 직접 합성한 소리예요(밖에서 받은 소리 없음, 특정 방송 소리를 따라 하지 않음).',
                            '실제로 쓸 크기로 들려 드려요 — 대사보다 작게 깔리는 소리라 조금 작게 들릴 수 있어요.']):
        dr.text((W / 2, 360 + i * 56), ln, font=b7(27), fill=INK, anchor='mm')
    put_char(im, '교실', 190, 70, H - 210); put_char(im, '예능', 190, W - 230, H - 210)
    push(im, 6.0)

    def example_quiz():
        T0, dq = 2.2, 3.6
        NAVY, YEL, BLUE, INK2 = (16, 25, 42), (255, 214, 80), (91, 192, 255), (236, 242, 255)
        def card(rem=None, ans=False, show_opts=True):
            im, dr = canvas(NAVY)
            dr.text((W / 2, 70), '잠깐 퀴즈!', font=jua(46), fill=YEL, anchor='mm')
            dr.text((W / 2, 140), '공을 굴리면 언젠가 멈추는 까닭은?', font=b9(38), fill=INK2, anchor='mm')
            opts = ['힘이 다 닳아서', '바닥이 마찰로 붙잡아서', '공이 지쳐서']
            if show_opts:
                for i, o in enumerate(opts):
                    x = W / 2 + (i - 1) * 400; on = ans and i == 1
                    rrect(dr, (x - 180, 220, x + 180, 420), 22, (40, 70, 100) if on else (30, 42, 66), outline=BLUE if on else (70, 84, 110), width=5 if on else 2)
                    dr.ellipse((x - 160, 238, x - 112, 286), fill=BLUE if on else (43, 58, 85)); dr.text((x - 136, 262), str(i + 1), font=b9(26), fill=NAVY if on else INK2, anchor='mm')
                    for j, ln in enumerate(wrap(dr, o, b9(30), 320)): dr.text((x, 330 + j * 42 - 10), ln, font=b9(30), fill=BLUE if on else (INK2 if not ans else (150, 160, 180)), anchor='mm')
                    if on: dr.text((x, 450), '정답', font=b9(28), fill=BLUE, anchor='mm')
            if rem:
                dr.ellipse((W / 2 - 52, 500, W / 2 + 52, 604), outline=YEL, width=6); dr.text((W / 2, 552), str(rem), font=b9(54), fill=YEL, anchor='mm')
            dr.text((W / 2, 680), '예시 장면 · 소리: 카드 톡 1 → 퀴즈 생각 시간 1(종 없이) → 정답 딩동 2', font=b7(24), fill=(170, 182, 205), anchor='mm')
            return im
        t_start = clock[0]
        events.append((t_start + 0.3, read_wav(os.path.join(OUT, 'wav', 'sfx_card_pop_1.wav'))))
        push(card(show_opts=False), 0.9); push(card(), T0 - 0.9)
        y = make('quiz_think', 1, dur=dq, bell=False); events.append((t_start + T0, y))
        segs = [(4, 0.3), (3, 1.0), (2, 1.0), (1, 1.0), (None, 0.3)]
        for rem, d in segs: push(card(rem), d)
        events.append((t_start + T0 + dq, read_wav(os.path.join(OUT, 'wav', 'sfx_answer_ding_2.wav'))))
        push(card(ans=True), 2.6)

    def example_reveal():
        PINK, INK2 = (255, 240, 244), INK
        def scene(big, small, col=(214, 84, 72), char=False):
            im, dr = canvas(PINK)
            dr.text((W / 2, 250), big, font=jua(84), fill=col, anchor='mm')
            if small: dr.text((W / 2, 360), small, font=b7(34), fill=INK2, anchor='mm')
            if char: put_char(im, '예능', 240, W // 2 - 90, 400)
            dr.text((W / 2, 690), '예시 장면 · 소리: 두둥 1 → 두구두구 → 짠 1 → 또르르 1', font=b7(24), fill=SUB, anchor='mm')
            return im
        t0 = clock[0]
        events.append((t0 + 0.4, read_wav(os.path.join(OUT, 'wav', 'sfx_dudung_1.wav'))))
        push(scene('그런데 놀라운 사실!', '공은 마찰이 없으면 계속 굴러가요'), 2.0)
        events.append((t0 + 2.0, read_wav(os.path.join(OUT, 'wav', 'sfx_drumroll_1.wav'))))
        push(scene('결과는...?', '두구두구두구'), 1.6)
        push(scene('정답은 2번!', '바닥이 마찰로 붙잡아서', (52, 120, 200)), 2.2)
        events.append((t0 + 5.8 + 0.25, read_wav(os.path.join(OUT, 'wav', 'sfx_ttoreureu_1.wav'))))
        push(scene('앗, 나는 1번 골랐는데...', None, (120, 110, 140), True), 2.4)

    for style, group in styles:
        col = GC[style]; bases = []
        for r in group:
            if r['group'] not in bases: bases.append(r['group'])
        im, dr = canvas()
        dr.text((W / 2, 110), f'{style} 효과음', font=jua(80), fill=col, anchor='mm')
        dr.text((W / 2, 185), f'{len(bases)}가지 · 판 {len(group)}개', font=b7(30), fill=SUB, anchor='mm')
        names = [next(r for r in group if r['group'] == b)['title'][:-2] for b in bases]
        half = (len(names) + 1) // 2
        for i, nm in enumerate(names):
            x = 300 if i < half else 720; y = 260 + (i % half) * 46
            dr.text((x, y), f'{i + 1:2d}. {nm}', font=b7(28), fill=INK)
        put_char(im, style, 160)
        push(im, 4.5)
        example_quiz() if style == '교실' else example_reveal()
        for gi, b in enumerate(bases):
            vs = [r for r in group if r['group'] == b]
            for r in vs:
                y = read_wav(os.path.join(OUT, r['file'])); dur = max(2.6, 0.6 + r['seconds'] + 1.0)
                im, dr = canvas()
                x = chip(dr, 40, 30, f'{style} 효과음', col)
                dr.text((x + 16, 52), f'{gi + 1} / {len(bases)}', font=b7(24), fill=SUB, anchor='lm')
                dr.text((60, 150), r['title'][:-2], font=jua(70), fill=INK, anchor='lm')
                tw = dr.textlength(r['title'][:-2], font=jua(70))
                for k in range(1, r['variants'] + 1):
                    cx = 60 + tw + 50 + (k - 1) * 66; cy = 152
                    if k == r['variant']: dr.ellipse((cx - 26, cy - 26, cx + 26, cy + 26), fill=col); fc = (255, 255, 255)
                    else: dr.ellipse((cx - 26, cy - 26, cx + 26, cy + 26), outline=(190, 190, 205), width=3); fc = (150, 150, 165)
                    dr.text((cx, cy), str(k), font=b9(30), fill=fc, anchor='mm')
                dr.text((60, 232), f"{r['variant']}번 · {r['variant_title']}", font=b9(36), fill=col, anchor='lm')
                rrect(dr, (40, 280, W - 40, 560), 26, CARD, outline=(232, 222, 205), width=2)
                yy = 312
                for lab, txt in (('어울리는 상황', r['situation']), ('분위기', r['mood']), ('만든 법', r['desc'])):
                    dr.text((70, yy), lab, font=b9(24), fill=col)
                    lines = wrap(dr, txt, b7(26), W - 380)
                    for j, ln in enumerate(lines[:2]): dr.text((250, yy - 2 + j * 36), ln, font=b7(26), fill=INK)
                    yy += 36 * max(1, min(2, len(lines))) + 20
                wavebar(dr, y, (60, 590, 900, 680), col)
                dr.text((920, 635), f"{r['seconds']}초", font=b9(30), fill=INK, anchor='lm')
                dr.text((W - 40, 700), r['id'], font=b7(18), fill=SUB, anchor='rm')
                put_char(im, style, 130, W - 150, 560)
                events.append((clock[0] + 0.6, y)); push(im, dur)
    im, dr = canvas()
    dr.text((W / 2, 300), '끝 — 고르신 번호를 알려 주세요', font=jua(64), fill=INK, anchor='mm')
    dr.text((W / 2, 390), '예: "띠용 2, 딩동 1, 퀴즈 생각 시간 3"', font=b7(32), fill=SUB, anchor='mm')
    push(im, 3.0)

    total = clock[0]; mix = np.zeros((int(total * SR) + SR, 2))
    for at, y in events:
        i = int(round(at * SR)); n = min(len(y), len(mix) - i); mix[i:i + n] += y[:n]
    mix = mix[: int(total * SR)]
    pk = np.max(np.abs(mix))
    if pk > 0.89: mix *= 0.89 / pk
    aw = os.path.join(tmp, 'audio.wav'); write_wav(aw, mix)
    out_path = out_path or os.path.join(PREVIEW, '교실효과음_듣기.mp4'); os.makedirs(os.path.dirname(out_path), exist_ok=True)

    def encode_part(fr, t_from, t_to, path):
        lst = os.path.join(tmp, f'list_{os.path.basename(path)}.txt')
        with open(lst, 'w') as f:
            for p, d in fr: f.write(f"file '{p}'\nduration {d:.4f}\n")
            f.write(f"file '{fr[-1][0]}'\n")
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-ss', f'{t_from:.3f}', '-t', f'{t_to - t_from:.3f}', '-i', aw,
                        '-vf', 'fps=30,format=yuv420p', '-c:v', 'libx264', '-preset', 'medium', '-crf', '24', '-tune', 'stillimage',
                        '-c:a', 'aac', '-b:a', '160k', '-t', f'{t_to - t_from:.3f}', '-movflags', '+faststart', path], check=True)
    encode_part(frames, 0.0, total, out_path)
    outs = [out_path]
    if os.path.getsize(out_path) > max_mb * 1e6:          # 두 개로 나누기: 예능 묶음 첫 장에서
        acc, cut = 0.0, None
        for i, (p, d) in enumerate(frames):
            if cut is None and i > 0 and acc >= total / 2: cut = (i, acc)
            acc += d
        i, tcut = cut
        a, b = out_path.replace('.mp4', '_1.mp4'), out_path.replace('.mp4', '_2.mp4')
        encode_part(frames[:i], 0.0, tcut, a); encode_part(frames[i:], tcut, total, b); outs = [a, b]
    shutil.rmtree(tmp, ignore_errors=True)
    for o in outs: print(o, f'{os.path.getsize(o) / 1e6:.1f} MB')
    print(f'길이 {total:.1f}초')
    return outs


if __name__ == '__main__':
    a = sys.argv[1:]
    if '--list' in a:
        for s, v, vt, how in all_items(): print(f"[{s['style']}] sfx_{s['base']}_{v}  {s['title']} — {vt}")
        sys.exit(0)
    if '--one' in a:
        i = a.index('--one'); base, v, out = a[i + 1], int(a[i + 2]), a[i + 3]
        kw = {}
        for x in a[i + 4:]:
            k, val = x.split('='); kw[k] = float(val) if '.' in val else int(val)
        if 'bell' in kw: kw['bell'] = bool(kw['bell'])
        y = make(base, v, **kw); write_wav(out, y); print(out, round(len(y) / SR, 2), '초'); sys.exit(0)
    if '--preview' in a:
        preview(); sys.exit(0)
    only = None
    if '--only' in a: only = set(a[a.index('--only') + 1].split(','))
    rows = build(only)
    sheet(rows)
    print(f"{len(rows)}개 → {OUT}")
