#!/usr/bin/env python3
"""「모델이란 무엇인가」 극장판 음악 후보 — 모두 직접 합성(numpy만, 외부 음원·샘플·유료 API 없음, 새로 지은 선율).

  python3 topics/model_kepler/sound/music.py            # 전부 → build/model_kepler/sound/*.wav
  python3 topics/model_kepler/sound/music.py A B        # 일부만 (A B C class disc sketch)
  python3 topics/model_kepler/sound/music.py disc --shift -5   # 발견의 순간을 조옮김(반음 단위, 기본 바장조)

  A 「촛불 서재」  하프시코드 + 류트 + 첼레스타, 3/4 ♩=72, 라단조 → 바장조
  B 「별 헤는 밤」 하프 아르페지오 + 현 패드 + 유리 종(비브라폰·첼레스타), 4/4 ♩=66, 사장조
  C 「옛 시계 공방」 피치카토 + 나무 건반(마림바) + 우드블록 + 낮은 첼로, 4/4 ♩=92, 가단조 → 다장조
  class 교실 음악  나무 건반 + 피치카토, 다장조 ♩=88, 15초
  disc 발견의 순간 현 패드가 차오르고 하프가 훑어 올라감, 10초(바장조, --shift 로 조옮김)
  sketch 「8분」 장면 소리 스케치(약 35초) — A가 작아짐 → 슈웅 → 끊김 → 틱×4 → 못 뽑힘·실 풀림 → 낮은 첼로

대사 밑에 깔 음악이라 선율은 절제하고, 말소리가 몰린 2~4 kHz는 마스터에서 덜어 낸다. 각 곡 −20 LUFS(outro_synth2.lufs_np).
"""
import os, sys, wave
import numpy as np

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))      # 저장소 사본: tools/sound/의 outro_synth2 · outro_synth
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import outro_synth2 as O2            # 읽기·불러 쓰기만
from outro_synth import SR

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")      # 저장소 사본: tools/sound/model_kepler/out/
PI2 = 2 * np.pi
TARGET = -20.0
SPEECH_HOLE = O2.chain(O2.g_bell(2900, -7.0, 0.85), O2.g_lp(7500, 2))      # 2~4 kHz 비우기


def m2f(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def nm(name):
    """'D4' 'Bb3' 'F#5' → MIDI 번호."""
    return O2.midi(name)


# ───────── 악기(이 편 전용, O2 의 줄 합성을 빌려 씀) ─────────
def harpsichord(f, dur=1.6, vel=0.7):
    """하프시코드 닮은 소리: 줄 끝 가까이를 깃으로 뜯음(배음 많음) + 한 옥타브 위 줄을 작게(4' 스톱) + 깃 소리."""
    f = round(f, 3)
    y = O2.string(f, dur, pos=0.07, tau=round(0.75 * (261.6 / f) ** 0.4, 4), damp=0.018, expo=0.95, B=8e-5, fmax=6500.0, att=0.0008)
    if 2 * f < 3000:
        y2 = O2.string(round(2 * f, 3), dur, pos=0.09, tau=round(0.5 * (261.6 / f) ** 0.4, 4), damp=0.03, expo=1.0, B=8e-5, fmax=6500.0, att=0.0008)
        y = y + 0.28 * y2
    t = O2.tt(dur)
    qn = O2.fftfilt(O2.rng.standard_normal(len(t)), O2.chain(O2.g_hp(1200, 1), O2.g_lp(5000, 1))) * np.exp(-t / 0.003)
    y = O2.norm(y) + 0.06 * O2.norm(qn)
    return y * vel * np.minimum(1, (dur - t) / 0.04).clip(0, 1)


def lute(f, dur=1.8, vel=0.7):
    """류트 닮은 소리: 손끝으로 뜯는 둥근 소리, 두 가닥 줄(복현)이 아주 조금 어긋남."""
    f = round(f, 3)
    a = O2.string(f, dur, pos=0.19, tau=round(0.85 * (196.0 / f) ** 0.35, 4), damp=0.05, expo=1.3, B=3e-5, fmax=4200.0, att=0.002)
    b = O2.string(round(f * 1.0025, 3), dur, pos=0.21, tau=round(0.8 * (196.0 / f) ** 0.35, 4), damp=0.06, expo=1.3, B=3e-5, fmax=4200.0, att=0.002)
    y = a + 0.7 * b
    if f < 200:                                  # 낮은 줄은 옥타브 위 가닥을 같이(옛 류트의 겹줄)
        y = y + 0.25 * O2.string(round(2 * f, 3), dur, pos=0.2, tau=0.5, damp=0.06, expo=1.3, B=3e-5, fmax=4200.0, att=0.002)
    return O2.norm(y) * vel


def marimba(f, dur=1.2, vel=0.7):
    """나무 건반(마림바): 기음 + 4배 + 10배 부분음, 부드러운 채 머리."""
    t = O2.tt(dur); tau = 0.45 * (261.6 / f) ** 0.5
    y = np.sin(PI2 * f * t) * np.exp(-t / tau)
    if 3.93 * f < 9000: y += 0.22 * np.sin(PI2 * 3.93 * f * t) * np.exp(-t / (tau * 0.18))
    if 9.8 * f < 9000: y += 0.05 * np.sin(PI2 * 9.8 * f * t) * np.exp(-t / (tau * 0.06))
    nz = O2.fftfilt(O2.rng.standard_normal(len(t)), O2.g_lp(1500, 1)) * np.exp(-t / 0.004)
    y = y + 0.06 * O2.norm(nz)
    return y * vel * np.minimum(1, t / 0.0025) * np.minimum(1, (dur - t) / 0.03).clip(0, 1)


def woodblock(f=880.0, vel=0.6):
    """작은 우드블록 '톡'(시계 초침 대신). 짧고 둥글게."""
    t = O2.tt(0.18)
    y = (np.sin(PI2 * f * t) + 0.45 * np.sin(PI2 * f * 2.37 * t) * np.exp(-t / 0.012)) * np.exp(-t / 0.035)
    return O2.norm(y) * vel * np.minimum(1, t / 0.0008)


def cello(f, dur, att=0.35, rel=0.9, vel=0.7, seedk=11):
    """낮은 첼로 한 줄(활): 두 가닥이 아주 조금 어긋난 톱니파, 어두운 거르개, 느린 떨림."""
    y = O2.ens((round(f, 3),), dur, att=att, rel=rel, fc=1300.0, voices=2, spread=4.0, vib=0.0035, expo=1.05, seedk=seedk)
    y = O2.fftfilt(y, O2.chain(O2.g_lp(2200, 2), O2.g_bell(250, 2.0, 1.0)))
    return y * vel


def arp(chord_m, n, up=True):
    """화음(MIDI 리스트)을 옥타브 위로 이어 붙여 n개."""
    out = []; i = 0
    while len(out) < n:
        out.append(chord_m[i % len(chord_m)] + 12 * (i // len(chord_m))); i += 1
    return out if up else out[::-1]


def setup(length_s):
    O2.N = int(round(length_s * SR))


# ───────── A 「촛불 서재」 ─────────
def cand_A(drop=None, end=None, pulse_after=1e9):
    """drop = {줄기: 이 시각부터 음을 더 넣지 않음}, end = 이 시각부터 아무 음도 넣지 않음(스케치용)."""
    drop = drop or {}; end = end or 1e9
    BT = 60 / 72; BAR = 3 * BT; NB = 11
    setup(NB * BAR + 1.6); O2.seed(701); r = O2.rng
    m = O2.Mix2()
    m.stem('lute', wet=0.22, fx=lambda y: O2.fftfilt(y, O2.g_lp(4000, 2)))
    m.stem('hpsi', wet=0.28, fx=lambda y: O2.fftfilt(y, O2.chain(O2.g_hp(180, 1), O2.g_lp(5200, 2))))
    m.stem('cel', wet=0.42, dly=0.12)
    m.stem('low', wet=0.15)
    # 라단조 → (나란한조) 바장조: Dm | Gm | A | Dm | Bb | F | C | F | Bb | C | F
    prog = [('D2', ['D3', 'A3', 'D4', 'F4']), ('G2', ['G3', 'D4', 'G4', 'Bb4']), ('A2', ['A3', 'E4', 'A4', 'C#5']), ('D2', ['D3', 'A3', 'D4', 'F4']),
            ('Bb1', ['Bb2', 'F3', 'Bb3', 'D4']), ('F2', ['F3', 'C4', 'F4', 'A4']), ('C2', ['C3', 'G3', 'C4', 'E4']), ('F2', ['F3', 'C4', 'F4', 'A4']),
            ('Bb1', ['Bb2', 'F3', 'Bb3', 'D4']), ('C2', ['C3', 'G3', 'C4', 'E4']), ('F2', ['F3', 'C4', 'F4', 'A4'])]
    # 첼레스타 선율(새로 지음, 드문드문): (마디, 박, 음, 박 길이)
    mel = [(0, 1, 'A5', 2), (1, 1, 'Bb5', 1), (1, 2, 'A5', 1), (2, 0, 'G5', 1.5), (2, 1.5, 'E5', 1.5), (3, 1, 'F5', 2),
           (5, 1, 'C6', 1), (5, 2, 'A5', 1), (6, 0, 'G5', 2), (6, 2, 'E5', 1), (7, 1, 'F5', 2),
           (8, 1, 'D6', 1), (8, 2, 'C6', 1), (9, 0, 'Bb5', 1.5), (9, 1.5, 'G5', 1.5), (10, 0, 'A5', 3)]
    T = lambda bar, beat: (bar * 3 + beat) * BT

    def ok(stem, at):
        return at < end and at < drop.get(stem, 1e9)

    for bar, (root, ch) in enumerate(prog):
        cm = [nm(x) for x in ch]
        # 류트: 1박에 낮은 음, 그 뒤 8분음표로 화음을 뜯어 오르내림(1·2·3박 = 여섯 개)
        if ok('low', T(bar, 0)):
            m.add('low', lute(m2f(nm(root) + 12), 2.6, 0.75), T(bar, 0), 0.55, pan=-0.1)
        for b in (1, 2):          # 스케치: 뜯는 류트가 빠진 뒤엔 낮은 음이 박마다 한 번씩(심장 박동처럼) 남는다
            if T(bar, b) >= pulse_after and ok('low', T(bar, b)):
                m.add('low', lute(m2f(nm(root) + 12), 1.6, 0.6), T(bar, b), 0.45, pan=-0.1)
        seq = [cm[0], cm[1], cm[2], cm[3], cm[2], cm[1]]
        for k, mm in enumerate(seq):
            at = T(bar, k * 0.5) + r.normal(0, 0.006)
            if k == 0: continue
            if ok('lute', at):
                m.add('lute', lute(m2f(mm), 1.6, 0.55 + 0.1 * (k == 3) + r.normal(0, 0.03)), at, 0.42, pan=-0.35)
        # 하프시코드: 2·3박에 가볍게 화음 위쪽 두 음(조금 흩어 치기), 마지막 마디는 1박에 한 번
        beats = (0,) if bar == len(prog) - 1 else (1, 2)
        for b in beats:
            for j, mm in enumerate(cm[2:]):
                at = T(bar, b) + 0.012 * j + r.normal(0, 0.004)
                if ok('hpsi', at):
                    m.add('hpsi', harpsichord(m2f(mm + 12 * (mm < 62)), 1.3 if bar < len(prog) - 1 else 2.6, 0.5), at, 0.20, pan=0.35)
    for bar, beat, n_, ln in mel:
        at = T(bar, beat)
        if ok('cel', at):
            m.add('cel', O2.celesta(m2f(nm(n_)), max(1.4, ln * BT + 0.8)), at, 0.30, pan=0.15)
    return m.render(rt60=1.7, rev=1.0, bright=5200.0, dtime=1.5 * BT, dfb=0.3, master=SPEECH_HOLE, target=TARGET, limit_db=2.0, fade_out=1.2)


# ───────── B 「별 헤는 밤」 ─────────
def cand_B():
    BT = 60 / 66; BAR = 4 * BT; NB = 8
    setup(NB * BAR + 1.8); O2.seed(702); r = O2.rng
    m = O2.Mix2()
    m.stem('harp', wet=0.32, fx=lambda y: O2.fftfilt(y, O2.g_lp(5000, 2)))
    m.stem('pad', wet=0.45, fx=lambda y: O2.autopan(O2.fftfilt(y, O2.chain(O2.g_hp(110, 1), O2.g_lp(1800, 2))), 0.13, 0.12))
    m.stem('bell', wet=0.55, dly=0.2)
    # 사장조: G | Em | C | D | G/B | Em | Cmaj7 | Dsus4→D(→G)
    prog = [('G2', ['G3', 'D4', 'G4', 'B4'], ['G3', 'B3', 'D4']), ('E2', ['E3', 'B3', 'E4', 'G4'], ['G3', 'B3', 'E4']),
            ('C2', ['C3', 'G3', 'C4', 'E4'], ['G3', 'C4', 'E4']), ('D2', ['D3', 'A3', 'D4', 'F#4'], ['F#3', 'A3', 'D4']),
            ('B1', ['B2', 'G3', 'D4', 'G4'], ['G3', 'B3', 'D4']), ('E2', ['E3', 'B3', 'E4', 'G4'], ['G3', 'B3', 'E4']),
            ('C2', ['C3', 'G3', 'B3', 'E4'], ['G3', 'B3', 'E4']), ('D2', ['D3', 'A3', 'D4', 'G4'], ['G3', 'A3', 'D4'])]
    T = lambda bar, beat: (bar * 4 + beat) * BT
    for bar, (root, ch, padv) in enumerate(prog):
        cm = [nm(x) for x in ch]
        notes = arp(cm, 8) if bar % 2 == 0 else arp(cm, 6) + [cm[3] + 12, cm[2] + 12]
        if bar == NB - 1: notes = arp(cm, 6) + [nm('F#5'), nm('G5')]      # 마지막: 이끔음 → 으뜸음
        for k, mm in enumerate(notes):
            at = T(bar, k * 0.5) + r.normal(0, 0.008); v = 0.30 if k == 0 else 0.20 - 0.01 * (k % 2)
            m.add('harp', O2.harp(m2f(mm), 2.8), at, v, pan=-0.45 + 0.12 * k)
        m.add('pad', O2.ens(tuple(round(m2f(nm(x)), 3) for x in padv), BAR + 0.15, att=1.0, rel=1.2, fc=1500.0, voices=4, spread=8.0, vib=0.002, seedk=bar), T(bar, 0) - 0.1, 0.55)
        m.add('pad', O2.ens((round(m2f(nm(root)), 3),), BAR + 0.15, att=0.8, rel=1.2, fc=700.0, voices=2, spread=5.0, vib=0.0, seedk=40 + bar), T(bar, 0) - 0.1, 0.45)
        if bar % 2 == 1:                                         # 두 마디에 한 번, 유리 종
            nn = cm[int(r.integers(1, 4))] + 24
            while nn > nm('E6'): nn -= 12
            inst = O2.vibes if bar % 4 == 1 else O2.celesta
            m.add('bell', inst(m2f(nn), 3.0), T(bar, 2), 0.16, pan=0.3)
    m.add('bell', O2.vibes(m2f(nm('D6')), 3.5), T(NB - 1, 3.5), 0.10, pan=-0.2)
    return m.render(rt60=2.6, rev=1.0, bright=5000.0, dtime=0.75 * BT, dfb=0.35, master=SPEECH_HOLE, target=TARGET, limit_db=2.0, fade_out=1.6)


# ───────── C 「옛 시계 공방」 ─────────
def cand_C():
    BT = 60 / 92; BAR = 4 * BT; NB = 11
    setup(NB * BAR + 1.2); O2.seed(703); r = O2.rng
    m = O2.Mix2()
    m.stem('pizz', wet=0.18, fx=lambda y: O2.fftfilt(y, O2.g_lp(4200, 2)))
    m.stem('mar', wet=0.24, dly=0.06)
    m.stem('wb', wet=0.12)
    m.stem('vc', wet=0.25)
    # 가단조 → 다장조: Am | Dm | E | Am | F | G | C | E | Am | Dm–E | Am(→C 피카르디 대신 다장조 쪽 화음으로 끝)
    prog = [('A2', ['A3', 'C4', 'E4']), ('D3', ['D4', 'F4', 'A4']), ('E2', ['E3', 'G#3', 'B3']), ('A2', ['A3', 'C4', 'E4']),
            ('F2', ['F3', 'A3', 'C4']), ('G2', ['G3', 'B3', 'D4']), ('C3', ['C4', 'E4', 'G4']), ('E2', ['E3', 'G#3', 'B3']),
            ('A2', ['A3', 'C4', 'E4']), ('D3', ['D4', 'F4', 'A4']), ('C3', ['C4', 'E4', 'G4'])]
    walk = {  # 걷는 베이스(피치카토, 4분음표)
        0: ['A2', 'C3', 'E3', 'C3'], 1: ['D3', 'F3', 'A3', 'F3'], 2: ['E2', 'G#2', 'B2', 'D3'], 3: ['C3', 'B2', 'A2', 'G2'],
        4: ['F2', 'A2', 'C3', 'A2'], 5: ['G2', 'B2', 'D3', 'B2'], 6: ['C3', 'E3', 'G3', 'E3'], 7: ['E2', 'G#2', 'B2', 'E3'],
        8: ['A2', 'C3', 'E3', 'C3'], 9: ['D3', 'F3', 'E3', 'G#2'], 10: ['C3', 'G2', 'C3', 'C3']}
    # 마림바 동기(새로 지음): 두 마디에 한 번, 엇박에서 '어디 보자' 하고 올라가는 세 음
    motif = {0: [(1.5, 'E5'), (2, 'A5'), (2.5, 'C6')], 2: [(1.5, 'D5'), (2, 'G#5'), (2.5, 'B5')], 4: [(1.5, 'C5'), (2, 'F5'), (2.5, 'A5')],
             6: [(1.5, 'E5'), (2, 'G5'), (2.5, 'C6')], 8: [(1.5, 'E5'), (2, 'A5'), (2.5, 'C6')], 10: [(0, 'E5'), (0.5, 'G5'), (1, 'C6')]}
    T = lambda bar, beat: (bar * 4 + beat) * BT
    for bar, (root, ch) in enumerate(prog):
        last = bar == NB - 1
        for k, n_ in enumerate(walk[bar]):
            if last and k > 0: break
            m.add('pizz', O2.pizz(m2f(nm(n_)), 0.7 if not last else 1.4, 3, 0.85 if k == 0 else 0.7), T(bar, k) + r.normal(0, 0.004), 0.55)
        # 피치카토 화음: 2·4박 엇박에 살짝(걷는 발걸음 사이)
        if not last:
            for b in (1.5, 3.5):
                for j, n_ in enumerate(ch):
                    m.add('pizz', O2.pizz(m2f(nm(n_)), 0.5, 2, 0.5), T(bar, b) + 0.008 * j, 0.22, pan=0.25)
        # 우드블록: 1·3박에 높게, 2·4박에 낮게(째깍)
        if not last:
            for b in range(4):
                m.add('wb', woodblock(1250.0 if b % 2 == 0 else 940.0, 0.6), T(bar, b) + r.normal(0, 0.002), 0.07, pan=0.45)
        if bar in motif:
            for b, n_ in motif[bar]:
                m.add('mar', marimba(m2f(nm(n_)), 1.3, 0.7), T(bar, b), 0.26, pan=-0.3)
    # 낮은 첼로 한 줄: 다섯째 마디부터 길게(온음표 둘씩)
    for bar, n_, ln in ((4, 'F2', 2), (6, 'C3', 1), (7, 'B2', 1), (8, 'A2', 2), (10, 'C3', 1.3)):
        m.add('vc', cello(m2f(nm(n_)), ln * BAR - 0.15, att=0.4, rel=0.8, vel=1.0, seedk=bar), T(bar, 0), 0.30, pan=-0.15)
    return m.render(rt60=1.3, rev=1.0, bright=5500.0, dtime=0.5 * BT, dfb=0.25, master=SPEECH_HOLE, target=TARGET, limit_db=2.0, fade_out=1.0)


# ───────── 교실 음악 ─────────
def classroom():
    BT = 60 / 88; BAR = 4 * BT; NB = 5
    setup(15.0); O2.seed(704); r = O2.rng
    m = O2.Mix2()
    m.stem('mar', wet=0.2, dly=0.05)
    m.stem('pizz', wet=0.15, fx=lambda y: O2.fftfilt(y, O2.g_lp(4200, 2)))
    m.stem('wb', wet=0.1)
    prog = [('C3', ['C4', 'E4', 'G4']), ('A2', ['A3', 'C4', 'E4']), ('F2', ['F3', 'A3', 'C4']), ('G2', ['G3', 'B3', 'D4']), ('C3', ['C4', 'E4', 'G4'])]
    T = lambda bar, beat: (bar * 4 + beat) * BT
    for bar, (root, ch) in enumerate(prog):
        cm = [nm(x) for x in ch]; last = bar == NB - 1
        m.add('pizz', O2.pizz(m2f(nm(root)), 0.9, 3, 0.85), T(bar, 0), 0.55)
        if not last: m.add('pizz', O2.pizz(m2f(nm(root) + 7), 0.6, 3, 0.7), T(bar, 2), 0.45)
        # 나무 건반: 엇박으로 통통 튀는 화음 조각
        pat = [(0.5, 1), (1, 2), (1.5, 0), (2.5, 1), (3, 2), (3.5, 1)] if not last else [(0, 0), (0.08, 1), (0.16, 2)]
        for b, j in pat:
            m.add('mar', marimba(m2f(cm[j] + 12), 1.0, 0.65 + r.normal(0, 0.04)), T(bar, b) + r.normal(0, 0.004), 0.24, pan=-0.25 + 0.25 * j)
        if last:      # 마지막 화음은 마림바 트레몰로로 끝까지 살짝 잇는다(15초 끝에서 페이드)
            k = 0; at = T(bar, 0.5)
            while at < 14.6:
                j = k % 3; v = 0.55 * max(0.25, 1 - (at - T(bar, 0.5)) / 4.5)
                m.add('mar', marimba(m2f(cm[j] + 12), 0.6, v), at + r.normal(0, 0.004), 0.16, pan=-0.25 + 0.25 * j); at += 0.105; k += 1
            m.add('pizz', O2.pizz(m2f(nm(root) - 12), 1.6, 3, 0.7), T(bar, 0), 0.35)
        if not last:
            for b in (1, 3): m.add('wb', woodblock(1100.0, 0.5), T(bar, b), 0.05, pan=0.4)
    return m.render(rt60=1.1, rev=1.0, bright=6000.0, dtime=0.5 * BT, dfb=0.2, master=SPEECH_HOLE, target=TARGET, limit_db=2.0, fade_out=1.6)


# ───────── 발견의 순간 ─────────
def discovery(shift=0):
    """바장조 기준. shift = 반음 수(예: A의 라단조→바장조면 0, B의 사장조면 +2, C의 다장조면 -5)."""
    setup(10.0); O2.seed(705); r = O2.rng
    s = shift; F = lambda name: m2f(nm(name) + s)
    m = O2.Mix2()
    m.stem('pad', wet=0.45, fx=lambda y: O2.fftfilt(y, O2.chain(O2.g_hp(90, 1), O2.g_lp(2400, 2))))
    m.stem('harp', wet=0.35, fx=lambda y: O2.fftfilt(y, O2.g_lp(5500, 2)))
    m.stem('bell', wet=0.5, dly=0.15)
    # 현 패드: Bb(add9) → C(sus4) → C → F — 점점 차오름
    chords = [(0.0, 2.2, ['Bb2', 'F3', 'Bb3', 'D4', 'C5']), (2.0, 1.5, ['C3', 'G3', 'C4', 'F4', 'G4']), (3.4, 1.8, ['C3', 'G3', 'C4', 'E4', 'G4']),
              (5.0, 4.2, ['F2', 'C3', 'F3', 'A3', 'C4', 'F4', 'A4'])]
    for i, (at, ln, ch) in enumerate(chords):
        y = O2.ens(tuple(round(F(x), 3) for x in ch), ln + 0.2, att=1.2 if i == 0 else 0.5, rel=1.6, fc=1700.0 + 300 * i, voices=4, spread=9.0, vib=0.003, seedk=50 + i)
        m.add('pad', y, at, 0.45 + 0.17 * i)
    # 하프가 훑고 올라감(3.2초 → 4.95초, 바장조 음계 2옥타브 반)
    scale = [0, 2, 4, 5, 7, 9, 11]; start = nm('C4'); seq = []
    k = 0
    while True:
        mm = nm('F3') + 12 * (k // 7) + scale[k % 7]
        if mm >= start: seq.append(mm)
        if mm >= nm('F6'): break
        k += 1
    t0, t1 = 3.2, 4.95
    for i, mm in enumerate(seq):
        u = i / (len(seq) - 1); at = t0 + (t1 - t0) * (u ** 0.85)
        m.add('harp', O2.harp(m2f(mm + s), 2.4), at, 0.10 + 0.10 * u, pan=-0.6 + 1.2 * u)
    # 도착: 낮은 하프 화음 + 첼레스타 종 한 번
    for j, x in enumerate(['F2', 'C3', 'A3', 'F4']):
        m.add('harp', O2.harp(F(x), 3.5), 5.0 + 0.03 * j, 0.32)
    m.add('bell', O2.celesta(F('A5'), 3.0), 5.02, 0.22, pan=0.2)
    m.add('bell', O2.celesta(F('C6'), 3.0), 5.5, 0.14, pan=-0.2)
    m.add('bell', O2.celesta(F('F6'), 3.0), 6.0, 0.12, pan=0.1)
    return m.render(rt60=2.8, rev=1.0, bright=5200.0, dtime=0.42, dfb=0.3, master=SPEECH_HOLE, target=TARGET, limit_db=2.0, fade_out=2.2)


# ───────── 「8분」 장면 소리 스케치 ─────────
SK = dict(full_end=12.0, swoosh=20.0, ticks0=None, gap_after_cut=2.0, tick_gap=0.9, quiet=2.5)


def sketch(sfx_lib=None):
    """반환: (스테레오 소리, 사건 목록[(시각, 이름)]). 음악 −20 LUFS 기준, 효과음은 sfx.py 의 음량 그대로."""
    import sfx as SFX
    S = sfx_lib or SFX.all_sfx()
    # 1) 후보 A — 악기가 하나씩 빠진다(12초부터 8초 동안: 첼레스타 → 하프시코드 → 류트 뜯음, 낮은 류트 음만 끊길 때까지 남음)
    fe = SK['full_end']; sw = SK['swoosh']
    a = cand_A(drop={'cel': fe, 'hpsi': fe + 2.5, 'lute': fe + 5.0}, end=sw + 1.0, pulse_after=fe + 5.0)
    a = a * 10 ** ((TARGET - O2.lufs_np(a[: int(fe * SR)])) / 20)           # 다 같이 울리는 앞 12초를 −20 LUFS 로
    swoosh = S['09']; cut = sw + len(swoosh) / SR - 0.05            # 슈웅이 끝나는 순간 음악을 끊는다
    t_ticks = [cut + SK['gap_after_cut'] + k * SK['tick_gap'] for k in range(4)]
    t_pull = t_ticks[-1] + len(S['10']) / SR + SK['quiet']
    t_cello = t_pull + len(S['11']) / SR + 0.15
    total = t_cello + 6.0
    L = int(total * SR); out = np.zeros((L, 2))
    t = np.arange(L) / SR
    env = np.ones(L)
    env = np.where(t < fe, 1.0, np.clip(1 - (t - fe) / (sw - fe), 0, 1) ** 1.3 * 0.82 + 0.18)    # 8초 동안 작아짐(바닥 −15 dB 쯤)
    k = int(0.03 * SR); ci = int(cut * SR)
    env[ci:] = 0; env[ci - k:ci] *= np.cos(np.linspace(0, np.pi / 2, k)) ** 2                   # 30 ms 안에 완전히 끊김(딸깍 없이)
    n = min(len(a), L); out[:n] += a[:n] * env[:n, None]
    ev = [(0.0, '후보 A 흐름'), (fe, '악기가 하나씩 빠짐'), (sw, '⑨ 슈웅'), (cut, '음악 끊김')]

    def put(y, at):
        i = int(round(at * SR)); y2 = y if y.ndim == 2 else np.stack([y, y], 1)
        out[i:i + len(y2)] += y2[: L - i]

    put(swoosh, sw)
    for k_, tk in enumerate(t_ticks):
        put(S['10'], tk); ev.append((tk, f'⑩ 틱 {k_ + 1}'))
    put(S['11'], t_pull); ev.append((t_pull, '⑪ 못 뽑힘 + 실 풀림'))
    # 낮은 첼로 한 음(라음 D2), 길게 → 페이드. 음악 줄기 기준(−20 LUFS 근처)으로 맞춘다.
    setup(7.0)
    vc = cello(m2f(nm('D2')), 4.6, att=0.9, rel=1.2, vel=1.0, seedk=77)
    irL, irR = O2.make_ir(2.4, 4000.0)
    vc = vc + 0.25 * np.stack([O2.conv(vc[:, 0], irL), O2.conv(vc[:, 1], irR)], 1)
    vc = O2.fftfilt(vc, O2.g_hp(40, 2))
    tv = np.arange(len(vc)) / SR; vc *= np.clip((len(vc) / SR - tv) / 1.8, 0, 1)[:, None] ** 1.5
    O2.N = len(vc); vc = vc * 10 ** ((TARGET - 1.0 - O2.lufs_np(vc)) / 20)
    put(vc, t_cello); ev.append((t_cello, '낮은 첼로 한 음'))
    ev.append((total, '끝'))
    pk = np.max(np.abs(out))
    if pk > 0.708: out *= 0.708 / pk
    return out, ev


# ───────── 저장 ─────────
def write_wav(path, y):
    y = np.clip(y, -1, 1)
    if y.ndim == 1: y = np.stack([y, y], 1)
    tmp = path + ".tmp.wav"
    with wave.open(tmp, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((y * 32767).astype("<i2").tobytes())
    os.replace(tmp, path)


JOBS = {'A': ('music_A.wav', cand_A), 'B': ('music_B.wav', cand_B), 'C': ('music_C.wav', cand_C),
        'class': ('music_class.wav', classroom)}

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    args = sys.argv[1:]
    shift = int(args[args.index('--shift') + 1]) if '--shift' in args else 0
    want = [x for x in args if x in ('A', 'B', 'C', 'class', 'disc', 'sketch')] or ['A', 'B', 'C', 'class', 'disc', 'sketch']
    for k in want:
        if k == 'disc':
            p = os.path.join(OUT, 'discovery.wav' if shift == 0 else f'discovery_{shift:+d}.wav'); write_wav(p, discovery(shift))
        elif k == 'sketch':
            y, ev = sketch(); p = os.path.join(OUT, 'sketch_8min.wav'); write_wav(p, y)
            import json
            json.dump([[round(a, 3), b] for a, b in ev], open(os.path.join(OUT, 'sketch_events.json'), 'w'), ensure_ascii=False, indent=1)
        else:
            fn, f = JOBS[k]; p = os.path.join(OUT, fn); write_wav(p, f())
        print(f"{k}: {p}")
