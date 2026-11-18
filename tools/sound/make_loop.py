#!/usr/bin/env python3
"""배경 곡을 '반복용 판'으로 바꾼다 — 끝없이 되풀이해도 이음매가 들리지 않게.

  python3 tools/sound/make_loop.py <원본.wav> <마디 길이(초)> <마디 수> <저장할.wav>
  예) python3 tools/sound/make_loop.py keys_A1.wav 3.0 16 music_bgm_keys_a1_loop.wav

하는 일
1. 곡을 <마디 길이 × 마디 수> 자리(마디 끝)에서 자른다. 그 뒤에 남는 잔향 · 메아리 꼬리는 버리지 않고
   곡 처음에 겹쳐 더한다(되풀이할 때 앞 바퀴의 잔향이 다음 바퀴 처음에 남는 것과 같다).
2. 원본 끝의 페이드아웃은 잘린 꼬리 쪽에만 있으므로 반복용 판의 본문에는 페이드가 없다.
3. 두 번 이어 붙여 이음매 앞뒤 0.2초 음량 차와 파형 튐을 잰다(갤러리 목록의 loop_note에 적은 값).
원본 파일은 바꾸지 않는다. numpy만 쓴다.
"""
import sys, wave
import numpy as np


def read(p):
    with wave.open(p) as w:
        sr, ch = w.getframerate(), w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), '<i2').reshape(-1, ch).astype(float) / 32768
    return x, sr


def write(p, x, sr):
    y = np.clip(np.round(x * 32767), -32768, 32767).astype('<i2')
    with wave.open(p, 'wb') as w:
        w.setnchannels(x.shape[1]); w.setsampwidth(2); w.setframerate(sr); w.writeframes(y.tobytes())


def fold(x, n):
    """앞 n 표본을 한 바퀴로 삼고, 그 뒤 꼬리를 처음부터 겹쳐 더한다."""
    y = x[:n].copy(); tail = x[n:]
    for k in range(0, len(tail), n):
        part = tail[k:k + n]; y[:len(part)] += part
    return y


def seam(y, sr):
    rms = lambda v: np.sqrt(np.mean(v ** 2) + 1e-20); db = lambda v: 20 * np.log10(v + 1e-12)
    L = len(y); h = int(0.2 * sr); z = np.concatenate([y, y])
    step = abs(db(rms(z[L - h:L])) - db(rms(z[L:L + h])))
    steps = [abs(db(rms(y[i:i + h])) - db(rms(y[i + h:i + 2 * h]))) for i in range(0, L - 2 * h, h)]
    dd = np.abs(np.diff(z[L - sr // 10:L + sr // 10], axis=0))
    jump = float(np.max(np.abs(z[L] - z[L - 1]) / (np.percentile(dd, 99.5, axis=0) + 1e-9)))
    return step, float(np.median(steps)), jump


if __name__ == '__main__':
    if len(sys.argv) != 5: sys.exit(__doc__)
    src, bar, bars, dst = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    x, sr = read(src)
    n = int(round(bar * bars * sr))
    if n >= len(x): sys.exit('자를 자리가 곡 길이보다 뒤에 있어요')
    y = fold(x, n)
    pk = np.max(np.abs(y))
    if pk > 0.89: y *= 0.89 / pk                       # 꼬리를 더해 최고점이 −1 dBFS를 넘으면 조금 낮춘다
    write(dst, y, sr)
    s, t, j = seam(y, sr)
    print(f'{dst}: {n / sr:.3f}초({bars}마디), 이음매 음량 차 {s:.2f} dB(곡 안 보통 {t:.2f} dB), 파형 튐 비율 {j:.2f}')
