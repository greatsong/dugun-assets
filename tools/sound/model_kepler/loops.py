#!/usr/bin/env python3
"""극장판 「모델이란 무엇인가」 배경 곡의 '반복용 판' — 끝없이 되풀이해도 이음매가 들리지 않게.

  python3 tools/sound/model_kepler/loops.py            # 넷 다 → tools/sound/model_kepler/out/*_loop.wav
  python3 tools/sound/model_kepler/loops.py A class    # 일부만 (A B C class)

원곡(music.py)은 마지막 마디가 '끝맺음'(길게 끄는 화음 · 트레몰로 · 페이드)이라 그대로 되풀이하면 이음매가 들린다.
반복용 판은 같은 코드 · 같은 씨앗값으로 다시 합성하되
  1) 끝맺음 마디의 음은 넣지 않고(그 앞 마디에서 처음 화음으로 돌아가게 자름),
  2) 자른 자리 뒤에 남는 잔향 · 메아리 꼬리를 곡 처음에 겹쳐 더하고(앞 바퀴의 잔향이 다음 바퀴 처음에 남듯),
  3) 원곡과 같은 −20 LUFS로 맞춘다.
자른 자리 앞부분의 음은 원곡과 표본 하나까지 같다(같은 씨앗값). 원곡 파일은 바꾸지 않는다.

  A 촛불 서재   3/4 ♩=72, 11마디 중 앞 10마디(… Bb | C → 처음 Dm)        25.0초
  B 별 헤는 밤  4/4 ♩=66, 8마디 전부(Dsus4→D → 처음 G, 끝음 F#5→G5가 처음으로 이어짐)  29.09초
  C 옛 시계 공방 4/4 ♩=92, 11마디 중 앞 10마디(… Dm–E → 처음 Am)         26.09초
  class 교실 음악 4/4 ♩=88, 5마디 중 앞 4마디(C Am F G → 처음 C)        10.91초
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import music as MK                   # 같은 폴더의 원곡 코드(읽기 · 불러 쓰기만)
O2 = MK.O2; SR = MK.SR

# 이름: (원곡 함수, 박 길이, 한 마디 박 수, 되풀이할 마디 수, 저장 이름)
JOBS = {
    'A': (MK.cand_A, 60 / 72, 3, 10, 'music_kepler_candle_study_loop.wav'),
    'B': (MK.cand_B, 60 / 66, 4, 8, 'music_kepler_starry_night_loop.wav'),
    'C': (MK.cand_C, 60 / 92, 4, 10, 'music_kepler_clock_workshop_loop.wav'),
    'class': (MK.classroom, 60 / 88, 4, 4, 'music_kepler_classroom_light_loop.wav'),
}


def render_cut(fn, cut):
    """cut 초 이후에 시작하는 음은 넣지 않고 원곡 함수를 그대로 돌린다.
    박자에 사람 손처럼 흔들림(±수 ms)을 주는 곡이라, 마디 첫 박 음이 cut 바로 앞에 놓일 수 있어 0.05초 여유를 둔다."""
    add0 = O2.Mix2.add

    def add(self, stem, y, at, *a, **k):
        if at >= cut - 0.05: return
        return add0(self, stem, y, at, *a, **k)
    O2.Mix2.add = add
    try:
        return fn()
    finally:
        O2.Mix2.add = add0


def fold(x, n):
    y = x[:n].copy(); tail = x[n:]
    for k in range(0, len(tail), n):
        part = tail[k:k + n]; y[:len(part)] += part
    return y


def make(key):
    fn, bt, bpb, bars, name = JOBS[key]
    cut = bars * bpb * bt; n = int(round(cut * SR))
    x = render_cut(fn, cut)
    y = fold(x, n)
    y = y * 10 ** ((MK.TARGET - O2.lufs_np(y)) / 20)
    pk = np.max(np.abs(y))
    if pk > 0.708: y = y * 0.708 / pk
    p = os.path.join(MK.OUT, name); MK.write_wav(p, y)
    return p, n / SR


if __name__ == '__main__':
    os.makedirs(MK.OUT, exist_ok=True)
    want = [a for a in sys.argv[1:] if a in JOBS] or list(JOBS)
    for k in want:
        p, s = make(k); print(f'{k}: {p} ({s:.3f}초)')
