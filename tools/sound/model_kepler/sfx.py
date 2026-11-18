#!/usr/bin/env python3
"""「모델이란 무엇인가」 극장판 효과음 12개 — 모두 직접 합성(numpy만, 외부 음원·샘플·유료 API 없음).

  python3 topics/model_kepler/sound/sfx.py      # → build/model_kepler/sound/sfx_01.wav … sfx_12.wav

음량: 각 소리의 '순간 음량 최댓값'(400 ms 창, BS.1770 K 가중)을 음악(−20 LUFS)보다 3.5 LU 위인 −16.5 LUFS 에 맞춘다.
다만 아주 짧은 소리는 그렇게 올리면 꼭대기가 너무 커지므로 표본 최고점이 −2.5 dBFS 를 넘지 않게 멈춘다(귀에 거슬리지 않게).
"""
import os, sys, wave
import numpy as np

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))      # 저장소 사본: tools/sound/의 outro_synth2 · outro_synth
import outro_synth2 as O2
from outro_synth import SR

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")      # 저장소 사본: tools/sound/model_kepler/out/
PI2 = 2 * np.pi
TARGET_M = -16.5            # 순간 음량 최댓값 목표
PEAK_CAP = 10 ** (-2.5 / 20)  # 표본 최고점 상한
rng = np.random.default_rng(1618)

NAMES = {
    '01': '손전등 딸깍', '02': '별가루', '03': '깃펜으로 점 찍기', '04': '깃펜 긁는 소리', '05': '고리 찍히는 도장',
    '06': '종이 넘김', '07': '못 박는 톡', '08': '실이 팽팽해지는 팅', '09': '돋보기 슈웅', '10': '눈금 짚는 틱',
    '11': '못 뽑힘 + 실 풀림', '12': '점이 고리에 드는 딩',
}


def tt(d):
    return np.arange(int(round(d * SR))) / SR


def env(t, tau, att=0.001):
    return np.minimum(1, t / att) * np.exp(-t / tau)


def bandnoise(n, lo, hi, order=2):
    return O2.norm(O2.fftfilt(rng.standard_normal(n), O2.chain(O2.g_hp(lo, order), O2.g_lp(hi, order))))


def pad_to(y, d):
    n = int(round(d * SR)); out = np.zeros(n); out[: min(n, len(y))] = y[:n]; return out


def stereo(y, pan=0.0, width=0.0):
    th = (pan + 1) * np.pi / 4
    if y.ndim == 2: return y
    s = np.stack([y * np.cos(th), y * np.sin(th)], 1) * np.sqrt(2)
    if width:
        d = int(0.0007 * SR); s[d:, 1] = (1 - width) * s[d:, 1] + width * s[:-d, 1]
    return s


def room(y, rt=0.5, wet=0.18, bright=6000.0, keep=0.25):
    """작은 방 울림(나무 책상·서재). 꼬리는 keep 초만 남기고 부드럽게 접는다(소리 하나가 1.5초를 넘지 않게)."""
    y = stereo(y)
    irL, irR = O2.make_ir(rt, bright, 200.0, 9)
    n = len(y) + int(min(rt * 1.2, keep) * SR); x = np.zeros((n, 2)); x[: len(y)] = y
    x = x + wet * np.stack([O2.conv(x[:, 0], irL), O2.conv(x[:, 1], irR)], 1)
    return fade_tail(x, min(keep, 0.2))


def fade_tail(y, d=0.02):
    k = min(len(y) // 3, int(d * SR))
    sh = (k,) + (1,) * (y.ndim - 1)
    y = y.copy(); y[-k:] *= (np.cos(np.linspace(0, np.pi / 2, k)) ** 2).reshape(sh); return y


# ───────── 소리들 ─────────
def s01_flashlight():
    """손전등 딸깍: 플라스틱 스위치가 눌리고(딸) 걸리는(깍) 두 겹. 높은 쇳소리는 빼고 둥글게."""
    def click(f1, f2, amp, tau):
        t = tt(0.06)
        body = (np.sin(PI2 * f1 * t) + 0.5 * np.sin(PI2 * f2 * t)) * env(t, tau, 0.0004)
        nz = bandnoise(len(t), 900, 5000) * env(t, 0.0025, 0.0002)
        return amp * O2.norm(body + 0.9 * nz)
    y = np.zeros(int(0.26 * SR))
    a = click(1650, 3100, 0.8, 0.008); b = click(2100, 3600, 1.0, 0.006)
    y[:len(a)] += a; i = int(0.055 * SR); y[i:i + len(b)] += b
    return room(y, 0.35, 0.10)


def s02_stardust():
    """별가루: 높은 첼레스타·종 소리가 흩어져 내려앉는다(라장조 오음 음계, 점점 여리게)."""
    pent = [O2.midi(x) for x in ('D6', 'E6', 'F#6', 'A6', 'B6', 'D7', 'E7', 'F#7')]
    d = 1.5; L = int(d * SR); out = np.zeros((L, 2)); t0 = 0.0
    for k in range(11):
        mm = pent[int(rng.integers(len(pent)))] if k else pent[-1]
        f = 440 * 2 ** ((mm - 69) / 12); dur = 0.9
        t = tt(dur); y = (np.sin(PI2 * f * t) * np.exp(-t / 0.28) + 0.18 * np.sin(PI2 * 2.76 * f * t) * np.exp(-t / 0.08)) * np.minimum(1, t / 0.002)
        amp = 0.9 * (1 - k / 13) * (0.75 + 0.25 * rng.random())
        i = int(t0 * SR); s = stereo(y * amp, pan=float(rng.uniform(-0.7, 0.7)))
        out[i:i + len(s)] += s[: L - i]
        t0 += 0.045 + 0.06 * rng.random() * (1 + k / 6)
    sh = bandnoise(L, 6000, 11000) * np.exp(-np.arange(L) / SR / 0.35) * 0.06    # 아주 옅은 반짝임 바람
    out += stereo(sh, width=0.5)
    return fade_tail(room(out, 1.2, 0.35, 8000.0)[: int(1.5 * SR)], 0.3)


def s03_quill_dot():
    """깃펜으로 점 찍기: 종이 위에 펜 끝이 '톡' 닿는 작은 소리(나무 책상 울림 조금)."""
    t = tt(0.2)
    tap = (np.sin(PI2 * 520 * t) * env(t, 0.012, 0.0006) + 0.35 * np.sin(PI2 * 1340 * t) * env(t, 0.006, 0.0004))
    nz = bandnoise(len(t), 1500, 7000) * env(t, 0.0018, 0.0002)
    return room(O2.norm(tap + 0.55 * nz), 0.3, 0.12)


def s04_quill_scratch():
    """깃펜 긁는 소리: 종이 결을 따라 사각사각 — 두 획. 잔 마찰 알갱이 + 띠 잡음."""
    d = 0.95; t = tt(d); n = len(t); y = np.zeros(n)
    for a, b in ((0.02, 0.42), (0.52, 0.90)):
        m = (t >= a) & (t < b); u = np.clip((t - a) / (b - a), 0, 1)
        e = np.sin(np.pi * u) ** 0.7 * m
        grain = np.zeros(n); k = np.where(m & (rng.random(n) < 420 / SR))[0]; grain[k] = rng.uniform(0.4, 1.0, len(k))
        grain = O2.fftfilt(grain, O2.chain(O2.g_hp(2500, 2), O2.g_lp(8000, 2)))
        hiss = O2.fftfilt(rng.standard_normal(n), O2.chain(O2.g_hp(3000, 2), O2.g_lp(7500, 2)))
        rough = 1 + 0.5 * np.sin(PI2 * 23 * t + rng.uniform(0, 6))
        y += e * (0.8 * O2.norm(grain) + 0.35 * O2.norm(hiss) * rough)
    y = O2.fftfilt(y, O2.g_bell(5500, -3.0, 0.8))            # 날카로운 꼭대기만 조금 누름
    return room(O2.norm(y), 0.3, 0.08)


def s05_stamp():
    """고리 찍히는 나무 도장: 손잡이 나무 '탁' + 책상에 닿는 낮은 '툭'."""
    t = tt(0.4)
    wood = (np.sin(PI2 * 410 * t) + 0.55 * np.sin(PI2 * 1030 * t) * np.exp(-t / 0.02) + 0.25 * np.sin(PI2 * 1720 * t) * np.exp(-t / 0.01)) * env(t, 0.045, 0.0006)
    thud = np.sin(PI2 * (95 + 40 * np.exp(-t / 0.01)) * t) * env(t, 0.06, 0.001)
    nz = bandnoise(len(t), 600, 4000) * env(t, 0.004, 0.0003)
    return room(O2.norm(wood + 0.8 * thud + 0.6 * nz), 0.45, 0.15)


def s06_page_turn():
    """종이 넘김: 사르륵 들리고(위로 쓸리는 잡음) 마지막에 살짝 '팔락'."""
    d = 0.7; t = tt(d); n = len(t)
    u = np.clip(t / 0.55, 0, 1); e = np.sin(np.pi * u) ** 1.5 * (t < 0.55)
    x = rng.standard_normal(n); y = np.zeros(n); nb = 6
    for i in range(nb):           # 통과 대역을 조금씩 옮겨 '쓸리는' 결
        fc = 1800 * (5200 / 1800) ** (i / (nb - 1)); w = np.exp(-0.5 * ((u - i / (nb - 1)) / 0.22) ** 2)
        y += O2.fftfilt(x, O2.chain(O2.g_hp(fc * 0.5, 2), O2.g_lp(fc * 1.6, 2))) * w
    crack = np.zeros(n); k = np.where((rng.random(n) < 90 / SR) & (t < 0.5))[0]; crack[k] = rng.uniform(0.3, 1, len(k))
    crack = O2.fftfilt(crack, O2.chain(O2.g_hp(1500, 2), O2.g_lp(6000, 2)))
    flap = np.zeros(n); i0 = int(0.52 * SR); tf = t[: n - i0]
    flap[i0:] = (bandnoise(n - i0, 300, 2500) * env(tf, 0.025, 0.002) + 0.5 * np.sin(PI2 * 160 * tf) * env(tf, 0.03, 0.002))
    y = O2.norm(y) * e + 0.5 * O2.norm(crack) * e + 0.55 * O2.norm(flap)
    return room(O2.norm(y), 0.35, 0.10)


def s07_nail():
    """못 박는 톡: 작은 망치가 못머리를 톡 — 쇠 부분음 몇 개(짧게) + 나무판 울림."""
    t = tt(0.35)
    metal = sum(a * np.sin(PI2 * f * t) * np.exp(-t / tau) for f, a, tau in ((2350, 1.0, 0.03), (3890, 0.5, 0.018), (6120, 0.25, 0.01)))
    board = (np.sin(PI2 * 230 * t) + 0.4 * np.sin(PI2 * 610 * t)) * env(t, 0.04, 0.0008)
    nz = bandnoise(len(t), 1000, 6000) * env(t, 0.0015, 0.0002)
    y = 0.55 * metal * np.minimum(1, t / 0.0004) + board + 0.5 * nz
    return room(O2.norm(y), 0.4, 0.12)


def s08_string_taut():
    """실이 팽팽해지는 팅: 실이 당겨지며 음이 살짝 올라갔다가(끌림) 맑게 '팅' 울린다."""
    d = 1.0; t = tt(d); f0 = 587.3          # 레(D5) 근처
    glide = f0 * (0.94 + 0.06 * (1 - np.exp(-t / 0.035)))
    ph = PI2 * np.cumsum(glide) / SR; y = np.zeros(len(t))
    for k in range(1, 9):
        y += (np.sin(np.pi * k * 0.23) / k ** 1.3) * np.sin(k * ph) * np.exp(-t * (1 + 0.15 * (k - 1) ** 2) / 0.35)
    stretch = bandnoise(len(t), 300, 2000) * np.clip(t / 0.03, 0, 1) * np.exp(-t / 0.03) * 0.25    # 실이 당겨지는 짧은 '스'
    y = O2.norm(y) * np.minimum(1, t / 0.002) + stretch
    return room(fade_tail(y, 0.15), 0.6, 0.2)


def s09_swoosh():
    """돋보기 슈웅: 부드러운 바람 소리가 위로 훑어 올라감 + 아주 옅은 오르는 휘파람."""
    d = 0.95; t = tt(d); n = len(t); x = rng.standard_normal(n); y = np.zeros(n); nb = 10
    u = t / d
    for i in range(nb):
        fc = 500 * (6000 / 500) ** (i / (nb - 1)); w = np.exp(-0.5 * ((u - i / (nb - 1)) / 0.14) ** 2)
        y += O2.fftfilt(x, O2.chain(O2.g_hp(fc * 0.7, 2), O2.g_lp(fc * 1.4, 2))) * w
    e = np.sin(np.pi * np.clip(u, 0, 1) ** 0.8) ** 1.4
    f = 380 * (1500 / 380) ** (u ** 1.3); tone = np.sin(PI2 * np.cumsum(f) / SR) * e * 0.10
    y = O2.norm(y) * e + tone
    s = stereo(O2.norm(y)); pan = -0.5 + u              # 왼쪽에서 오른쪽으로 지나감
    th = (pan + 1) * np.pi / 4; s = np.stack([y * np.cos(th), y * np.sin(th)], 1) * np.sqrt(2)
    return fade_tail(room(s, 0.6, 0.15), 0.08)


def s10_tick():
    """눈금 짚는 틱: 마른 나무 막대 끝이 눈금자를 '틱' — 짧고 깨끗하게(네 번 똑같이 쓴다)."""
    t = tt(0.12)
    body = (np.sin(PI2 * 1180 * t) + 0.45 * np.sin(PI2 * 2630 * t) * np.exp(-t / 0.004)) * env(t, 0.009, 0.0004)
    nz = bandnoise(len(t), 1500, 6000) * env(t, 0.0012, 0.0001)
    return room(O2.norm(body + 0.6 * nz), 0.25, 0.08)


def s11_pull_unwind():
    """못 뽑힘 + 실 풀림: 나무에서 못이 끽 빠지고(짧은 마찰) '뽁' → 느슨해진 실이 낮게 흔들리며 풀린다."""
    d = 1.5; L = int(d * SR); y = np.zeros(L); t = tt(d)
    # 끽(0~0.28초): 마찰 — 음높이가 조금 오르는 거친 소리, 크지 않게
    tc = t[: int(0.28 * SR)]; f = 620 + 380 * (tc / 0.28) ** 1.2
    jit = 1 + 0.6 * (rng.random(len(tc)) < 0.08)
    cr = np.sin(PI2 * np.cumsum(f) / SR) * (0.6 + 0.4 * np.sign(np.sin(PI2 * 38 * tc))) * jit
    cr = O2.fftfilt(cr, O2.chain(O2.g_hp(400, 1), O2.g_lp(3000, 2))) * np.sin(np.pi * tc / 0.28) ** 0.8
    y[: len(tc)] += 0.35 * O2.norm(cr)
    # 뽁(0.28초): 빠지는 순간
    i = int(0.28 * SR); tp = tt(0.12)
    pop = (np.sin(PI2 * (300 + 500 * np.exp(-tp / 0.01)) * tp) * env(tp, 0.025, 0.0005) + 0.4 * bandnoise(len(tp), 800, 5000) * env(tp, 0.003, 0.0002))
    y[i:i + len(tp)] += 0.9 * O2.norm(pop)
    # 실 풀림(0.32초~): 낮은 줄이 음이 흘러내리며 흔들림 + 실이 쓸리는 옅은 소리
    j = int(0.32 * SR); tu = t[: L - j]
    fu = 330 * (0.62 + 0.38 * np.exp(-tu / 0.35)) * (1 + 0.012 * np.sin(PI2 * 5.5 * tu))
    ph = PI2 * np.cumsum(fu) / SR; st = np.zeros(len(tu))
    for k in range(1, 6): st += (1 / k ** 1.4) * np.sin(k * ph) * np.exp(-tu * (1 + 0.3 * (k - 1)) / 0.5)
    rus = O2.fftfilt(rng.standard_normal(len(tu)), O2.chain(O2.g_hp(1500, 2), O2.g_lp(5000, 2))) * np.exp(-tu / 0.4) * np.clip(tu / 0.05, 0, 1)
    y[j:] += 0.55 * O2.norm(st) * np.minimum(1, tu / 0.004) + 0.12 * O2.norm(rus)
    return room(fade_tail(y, 0.2), 0.5, 0.15)[: L]


def s12_ding():
    """점이 고리에 드는 맑은 차임 '딩'(라 음 A5 바탕, 종의 부분음 조금)."""
    t = tt(1.3); f = 880.0
    y = sum(a * np.sin(PI2 * r * f * t) * np.exp(-t / tau) for r, a, tau in ((1, 1.0, 0.55), (2.0, 0.25, 0.30), (3.01, 0.10, 0.14), (4.17, 0.05, 0.07)))
    y = y * np.minimum(1, t / 0.0015)
    return fade_tail(room(y, 1.0, 0.25, 7500.0)[: len(t)], 0.25)


MAKERS = {'01': s01_flashlight, '02': s02_stardust, '03': s03_quill_dot, '04': s04_quill_scratch, '05': s05_stamp, '06': s06_page_turn,
          '07': s07_nail, '08': s08_string_taut, '09': s09_swoosh, '10': s10_tick, '11': s11_pull_unwind, '12': s12_ding}


# ───────── 음량 ─────────
def momentary_max(y):
    """K 가중 400 ms 창(100 ms 간격)의 최댓값(LUFS). 짧은 소리는 앞뒤를 0으로 채워 잰다."""
    y = stereo(y); pad = int(0.5 * SR); x = np.zeros((len(y) + 2 * pad, 2)); x[pad:pad + len(y)] = y
    n = len(x); nf = 1 << int(np.ceil(np.log2(n + 8192)))
    z1 = np.exp(-1j * PI2 * np.fft.rfftfreq(nf)); z2 = z1 * z1
    H = ((1.53512485958697 - 2.69169618940638 * z1 + 1.19839281085285 * z2) / (1 - 1.69065929318241 * z1 + 0.73248077421585 * z2)
         * (1 - 2 * z1 + z2) / (1 - 1.99004745483398 * z1 + 0.99007225036621 * z2))
    k = np.stack([np.fft.irfft(np.fft.rfft(x[:, c], nf) * H, nf)[:n] for c in (0, 1)], 1)
    blk = int(0.4 * SR); hop = int(0.01 * SR)
    p = max(np.mean(k[i:i + blk] ** 2, axis=0).sum() for i in range(0, n - blk + 1, hop))
    return -0.691 + 10 * np.log10(p + 1e-12)


def level(y):
    y = stereo(y)
    g = 10 ** ((TARGET_M - momentary_max(y)) / 20)
    pk = np.max(np.abs(y)) * g
    capped = pk > PEAK_CAP
    if capped: g *= PEAK_CAP / pk
    return y * g, capped


def all_sfx(report=None):
    out = {}
    for k, f in MAKERS.items():
        y, capped = level(f())
        out[k] = y
        if report is not None: report[k] = capped
    return out


def write_wav(path, y):
    y = np.clip(stereo(y), -1, 1); tmp = path + ".tmp.wav"
    with wave.open(tmp, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((y * 32767).astype("<i2").tobytes())
    os.replace(tmp, path)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True); rep = {}
    S = all_sfx(rep)
    for k, y in S.items():
        p = os.path.join(OUT, f"sfx_{k}.wav"); write_wav(p, y)
        print(f"{k} {NAMES[k]:14s} {len(y) / SR:5.2f}초  순간최대 {momentary_max(y):6.1f} LUFS  최고점 {20 * np.log10(np.max(np.abs(y))):6.1f} dBFS{'  (최고점 상한에 걸림)' if rep[k] else ''}")
