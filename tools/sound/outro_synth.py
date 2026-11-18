#!/usr/bin/env python3
"""끝 화면(15초) 음악 시안 — 직접 합성(numpy만 사용, 외부 음원·유료 API 없음).
  outro_music.py <A|B|C> <crown초> <ding초> <out.wav>
  A 항해 마림바(다 장조 108) · B 오르골 왈츠(바 장조 84) · C 우쿨렐레 산책(사 장조 116)
왕관이 내려오는 순간(crown)에 반짝 글리산도, 다음 섬에 불이 켜지는 순간(ding)에 종 한 번을 맞춘다.
"""
import sys, wave
import numpy as np

SR = 48000
DUR = 15.0
N = int(SR * DUR)
rng = np.random.default_rng(7)
NOTE = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}


def hz(name):
    p, o = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((NOTE[p] + (o - 4) * 12 - 9) / 12)


def tt(dur):
    return np.arange(int(dur * SR)) / SR


def marimba(f, dur=1.4):
    t = tt(dur); tau = 0.5 * (261.6 / f) ** 0.5
    y = np.sin(2 * np.pi * f * t) * np.exp(-t / tau)
    y += 0.28 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t / (tau * 0.16))
    if 9.2 * f < 18000: y += 0.08 * np.sin(2 * np.pi * 9.2 * f * t) * np.exp(-t / (tau * 0.06))
    y += 0.10 * rng.standard_normal(len(t)) * np.exp(-t / 0.003)
    return y * np.minimum(1, t / 0.002)


def glock(f, dur=2.2):
    t = tt(dur); y = np.zeros(len(t))
    for r, a, tau in ((1, 1.0, 0.9), (2.756, 0.42, 0.5), (5.404, 0.18, 0.25), (8.933, 0.07, 0.12)):
        if r * f < 19000: y += a * np.sin(2 * np.pi * r * f * t) * np.exp(-t / tau)
    return y * np.minimum(1, t / 0.001)


def musicbox(f, dur=2.4):
    t = tt(dur); y = np.zeros(len(t))
    for r, a, tau in ((1, 1.0, 1.0), (2.0, 0.16, 0.55), (3.01, 0.22, 0.3), (5.2, 0.10, 0.14)):
        if r * f < 19000: y += a * np.sin(2 * np.pi * r * f * t) * np.exp(-t / tau)
    y += 0.06 * rng.standard_normal(len(t)) * np.exp(-t / 0.002)
    return y * np.minimum(1, t / 0.0015)


def bass(f, dur=0.9):
    t = tt(dur)
    y = np.sin(2 * np.pi * f * t) + 0.45 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.12) + 0.15 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t / 0.06)
    return np.tanh(1.2 * y * np.exp(-t / 0.3)) * np.minimum(1, t / 0.004)


def pad(freqs, dur, att=0.35, rel=0.6):
    t = tt(dur + rel); y = np.zeros(len(t))
    for f in freqs:
        for d in (-0.003, 0.0, 0.003):
            y += np.sin(2 * np.pi * f * (1 + d) * t + rng.uniform(0, 6.28))
    e = np.minimum(1, t / att) * np.where(t < dur, 1.0, np.exp(-(t - dur) / (rel / 3)))
    return y * e / (3 * len(freqs))


def whistle(f, dur):
    t = tt(dur + 0.12)
    vib = 1 + 0.006 * np.sin(2 * np.pi * 5.4 * t) * np.clip((t - 0.14) / 0.2, 0, 1)
    ph = 2 * np.pi * np.cumsum(f * vib) / SR
    y = np.sin(ph) + 0.07 * np.sin(2 * ph) + 0.02 * np.sin(3 * ph)
    e = np.minimum(1, t / 0.035) * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.03))
    return y * e


def pluck(f, dur=1.1, bright=0.5):
    """카플러스-스트롱 나일론 줄(96 kHz에서 만들고 절반으로 줄여 음정 오차를 줄임)."""
    sr2 = SR * 2; P = max(2, int(round(sr2 / f))); n = int(dur * sr2)
    buf = rng.uniform(-1, 1, P)
    k = int(2 + (1 - bright) * 10)
    buf = np.convolve(buf, np.ones(k) / k, mode='same'); buf -= buf.mean()
    out = np.empty(n); pos = 0; dec = 0.996 ** (220.0 / max(f, 60)) if f < 220 else 0.9955
    while pos < n:
        m = min(P, n - pos); out[pos:pos + m] = buf[:m]; pos += m
        buf = dec * 0.5 * (buf + np.roll(buf, 1))
    y = 0.5 * (out[0::2][: n // 2] + out[1::2][: n // 2])
    t = np.arange(len(y)) / SR
    return y * np.minimum(1, t / 0.002) * np.exp(-t / 0.9)


def shaker(vel=1.0):
    t = tt(0.16); x = rng.standard_normal(len(t)); x = np.diff(x, prepend=0)
    return vel * x * np.minimum(1, t / 0.006) * np.exp(-t / 0.035)


def snap():
    t = tt(0.2); x = rng.standard_normal(len(t))
    x = x - np.convolve(x, np.ones(24) / 24, mode='same'); x = np.convolve(x, np.ones(4) / 4, mode='same')
    e = np.exp(-t / 0.018) + 0.5 * np.exp(-np.abs(t - 0.011) / 0.004)
    return x * e


def kick():
    t = tt(0.4); f = 48 + 75 * np.exp(-t / 0.028)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.13)


class Mix:
    def __init__(self):
        self.dry = np.zeros((N + SR * 4, 2)); self.send = np.zeros(N + SR * 4)

    def add(self, y, at, gain=1.0, pan=0.0, wet=0.2):
        i = int(round(at * SR))
        if i < 0 or i >= N: return
        y = y[: len(self.send) - i] * gain
        th = (pan + 1) * np.pi / 4
        self.dry[i:i + len(y), 0] += y * np.cos(th); self.dry[i:i + len(y), 1] += y * np.sin(th)
        self.send[i:i + len(y)] += y * wet

    def render(self, wetlvl=1.0):
        L = int(1.6 * SR); t = np.arange(L) / SR; out = self.dry.copy()
        nfft = 1 << int(np.ceil(np.log2(len(self.send) + L)))
        S = np.fft.rfft(self.send, nfft)
        for ch in (0, 1):
            ir = rng.standard_normal(L) * np.exp(-t / 0.32)
            ir = np.convolve(ir, np.ones(10) / 10, mode='same'); ir[: int(0.012 * SR)] = 0
            ir /= np.sqrt(np.sum(ir ** 2))
            out[:, ch] += wetlvl * np.fft.irfft(S * np.fft.rfft(ir, nfft), nfft)[: len(out)]
        out = out[:N]
        fade = int(0.5 * SR); out[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 2
        out /= np.max(np.abs(out)) + 1e-9
        return np.tanh(out * 1.05) * 0.5     # 최고점 약 −7 dBFS(나중에 음량 맞춤)


def accents(m, key, crown, ding):
    """왕관 반짝(오름 글리산도) + 다음 섬 종."""
    pent = {'C': ['G5', 'A5', 'C6', 'D6', 'E6', 'G6'], 'F': ['C6', 'D6', 'F6', 'G6', 'A6', 'C7'], 'G': ['D6', 'E6', 'G6', 'A6', 'B6', 'D7']}[key]
    for i, nm in enumerate(pent):
        m.add(glock(hz(nm), 1.6), crown - 0.28 + i * 0.055, 0.20 + 0.03 * i, pan=-0.4 + 0.16 * i, wet=0.5)
    top = {'C': ('C6', 'G6'), 'F': ('F6', 'C7'), 'G': ('G6', 'D7')}[key]
    m.add(glock(hz(top[0]), 2.4), ding, 0.42, pan=0.25, wet=0.5)
    m.add(glock(hz(top[1]), 2.0), ding + 0.09, 0.22, pan=0.35, wet=0.5)


def cand_A(crown, ding):
    """항해 마림바 — 다 장조, 108 BPM. 마림바 선율 + 통통 베이스 + 셰이커."""
    b = 60 / 108; m = Mix()
    chords = [('C3', ['E4', 'G4', 'C5']), ('B2', ['D4', 'G4', 'B4']), ('A2', ['C4', 'E4', 'A4']), ('F2', ['C4', 'F4', 'A4']),
              ('G2', ['E4', 'G4', 'C5']), ('G2', ['D4', 'G4', 'B4'])]
    mel = [['E5', None, 'G5', None, 'C6', None, 'G5', None], ['D5', None, 'G5', None, 'B5', None, 'G5', None],
           ['C5', 'E5', 'A5', None, 'G5', None, 'E5', None], ['F5', 'A5', 'C6', None, 'A5', None, 'F5', None],
           ['E5', None, 'G5', None, 'C6', None, 'E6', None], ['D6', None, 'B5', None, 'G5', 'A5', 'B5', 'D6']]
    for bar, (root, ch) in enumerate(chords):
        t0 = bar * 4 * b
        m.add(bass(hz(root)), t0, 0.55, wet=0.05); m.add(bass(hz(root) * (1.5 if bar != 1 else 1.335)), t0 + 2 * b, 0.42, wet=0.05)
        if bar >= 1: m.add(kick(), t0, 0.35, wet=0.02); m.add(kick(), t0 + 2 * b, 0.28, wet=0.02)
        for k in range(8):
            tk = t0 + k * b / 2
            if k % 2 == 1:      # 엇박 화음
                for j, nm in enumerate(ch): m.add(marimba(hz(nm), 0.9), tk + j * 0.004, 0.13, pan=-0.35 + 0.1 * j, wet=0.25)
                m.add(shaker(0.9), tk, 0.05, pan=0.5, wet=0.1)
            else: m.add(shaker(0.5), tk, 0.035, pan=0.5, wet=0.1)
            if mel[bar][k]: m.add(marimba(hz(mel[bar][k])), tk, 0.34, pan=0.12, wet=0.3)
    tf = 24 * b      # 마침 화음
    for j, nm in enumerate(['C3', 'G3', 'E4', 'G4', 'C5', 'E5', 'C6']):
        m.add(marimba(hz(nm), 2.2), tf + j * 0.03, 0.30 if j else 0.4, pan=-0.3 + 0.1 * j, wet=0.4)
    m.add(bass(hz('C2'), 1.4), tf, 0.5, wet=0.05); m.add(glock(hz('C7'), 2.0), tf + 0.25, 0.10, pan=0.3, wet=0.6)
    accents(m, 'C', crown, ding)
    return m.render(0.9)


def cand_B(crown, ding):
    """오르골 왈츠 — 바 장조, 84 BPM, 3박. 오르골 선율 + 부드러운 화음 바탕."""
    b = 60 / 84; m = Mix()
    chords = [('F2', ['A3', 'C4', 'F4']), ('D2', ['A3', 'D4', 'F4']), ('Bb1', ['Bb3', 'D4', 'F4']), ('C2', ['G3', 'C4', 'E4']),
              ('F2', ['A3', 'C4', 'F4']), ('C2', ['Bb3', 'C4', 'E4'])]
    mel = [[('A5', 0), ('C6', 1), ('F6', 2)], [('A5', 0), ('D6', 1), ('F6', 2)], [('Bb5', 0), ('D6', 1), ('F6', 2), ('D6', 2.5)],
           [('G5', 0), ('C6', 1), ('E6', 2)], [('F6', 0), ('C6', 1), ('A5', 2)], [('Bb5', 0), ('G5', 1), ('E5', 2), ('G5', 2.5)]]
    for bar, (root, ch) in enumerate(chords):
        t0 = bar * 3 * b
        m.add(bass(hz(root) * 2, 1.2), t0, 0.33, wet=0.1)
        m.add(pad([hz(x) for x in ch], 3 * b, 0.5, 0.8), t0, 0.16, wet=0.5)
        for beat in (1, 2):
            for j, nm in enumerate(ch[1:]): m.add(musicbox(hz(nm) * 2, 1.4), t0 + beat * b + j * 0.012, 0.085, pan=-0.3 + 0.2 * j, wet=0.4)
        for nm, at in mel[bar]: m.add(musicbox(hz(nm)), t0 + at * b, 0.36, pan=0.1, wet=0.45)
    tf = 18 * b
    m.add(pad([hz('F3'), hz('A3'), hz('C4'), hz('F4')], 1.6, 0.3, 1.0), tf, 0.2, wet=0.5); m.add(bass(hz('F2'), 1.4), tf, 0.36, wet=0.1)
    for j, nm in enumerate(['F5', 'A5', 'C6', 'F6', 'A6', 'C7']): m.add(musicbox(hz(nm)), tf + j * 0.11, 0.30 - 0.02 * j, pan=-0.3 + 0.12 * j, wet=0.5)
    accents(m, 'F', crown, ding)
    return m.render(1.0)


def cand_C(crown, ding):
    """우쿨렐레 산책 — 사 장조, 116 BPM. 우쿨렐레 스트럼 + 휘파람 선율 + 손가락 튕기기."""
    b = 60 / 116; m = Mix()
    chords = [('G2', ['G4', 'B4', 'D5', 'G5']), ('E2', ['G4', 'B4', 'E5', 'G5']), ('C2', ['G4', 'C5', 'E5', 'G5']), ('D2', ['A4', 'D5', 'F#5', 'A5']),
              ('G2', ['G4', 'B4', 'D5', 'G5']), ('C2', ['G4', 'C5', 'E5', 'G5'])]
    strum = [(0, 'd', 1.0), (2, 'd', 0.7), (3, 'u', 0.55), (5, 'u', 0.55), (6, 'd', 0.75), (7, 'u', 0.5)]
    lead = [[('B4', 0, 1), ('D5', 1, 1), ('G5', 2, 1.8)], [('G5', 0, 1), ('E5', 1, 1), ('B4', 2, 1.8)], [('C5', 0, 1), ('E5', 1, 1), ('G5', 2, 1), ('E5', 3, 0.9)],
            [('F#5', 0, 1), ('A5', 1, 1), ('D5', 2, 1.8)], [('B4', 0, 1), ('D5', 1, 1), ('G5', 2, 1), ('B5', 3, 0.9)], [('C6', 0, 1.8), ('A5', 2, 1.8)]]
    for bar, (root, ch) in enumerate(chords):
        t0 = bar * 4 * b; cc = ch
        if bar == 5: half = [('C2', ['G4', 'C5', 'E5', 'G5']), ('D2', ['A4', 'D5', 'F#5', 'A5'])]
        for k, d, v in strum:
            tk = t0 + k * b / 2
            if bar == 5: cc = half[0][1] if k < 4 else half[1][1]
            order = cc if d == 'd' else cc[::-1]
            for j, nm in enumerate(order): m.add(pluck(hz(nm), 0.9, 0.55), tk + j * (0.014 if d == 'd' else 0.010), 0.16 * v, pan=-0.25 + 0.05 * j, wet=0.18)
        r1 = root; r2 = root if bar != 5 else 'D2'
        m.add(bass(hz(r1) * 2), t0, 0.5, wet=0.05); m.add(bass(hz(r2) * 2 * (1.5 if bar != 5 else 1)), t0 + 2 * b, 0.4, wet=0.05)
        m.add(snap(), t0 + b, 0.16, pan=0.45, wet=0.3); m.add(snap(), t0 + 3 * b, 0.16, pan=0.45, wet=0.3)
        for nm, at, ln in lead[bar]: m.add(whistle(hz(nm) * 2, ln * b * 0.92), t0 + at * b, 0.115, pan=0.1, wet=0.45)
    tf = 24 * b
    for j, nm in enumerate(['G3', 'D4', 'G4', 'B4', 'D5', 'G5']): m.add(pluck(hz(nm), 2.4, 0.6), tf + j * 0.035, 0.26, pan=-0.3 + 0.12 * j, wet=0.35)
    m.add(bass(hz('G2'), 1.4), tf, 0.5, wet=0.05); m.add(whistle(hz('G6'), 0.9), tf, 0.10, pan=0.1, wet=0.5)
    accents(m, 'G', crown, ding)
    return m.render(0.9)


if __name__ == '__main__':
    which, crown, ding, outp = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
    y = {'A': cand_A, 'B': cand_B, 'C': cand_C}[which](crown, ding)
    pcm = (np.clip(y, -1, 1) * 32767).astype('<i2')
    with wave.open(outp, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    print(outp)
