#!/usr/bin/env python3
"""ZzFX 소리 생성 함수를 numpy(파이썬)로 옮긴 것 — 짧은 효과음을 값 한 줄로 만든다. 공용 파일.

원본: ZzFX - Zuper Zmall Zound Zynth v1.4.0 by Frank Force
      https://github.com/KilledByAPixel/ZzFX  (ZzFX.js 의 buildSamples, 2026-11-03 커밋 ac5a472 기준)
      웹 디자이너(귀로 값 고르기): https://killedbyapixel.github.io/ZzFX
옮긴 이: 두근두근러닝(greatsong) 제작 폴더, 2026-11-18 (이 파일은 저장소 사본 — 제작 폴더 pipeline/zzfx.py와 같고 사용 예의 경로만 바꿈) — 원본 자바스크립트 글을 읽고 numpy로 옮김
         (원본 패키지를 설치하거나 실행 파일을 받지 않았다). 계산 순서는 원본과 한 줄씩 같게 두었다.

쓰는 법
  import zzfx as Z
  y = Z.zzfx(1, .05, 925, .04, .3, .6, 1, .3, None, 6.27, -184, .09, .17)   # 원본과 같은 값 순서·기본값(None = 기본값)
  y = Z.zzfx(frequency=537, attack=.02, ...)                                  # 이름으로도
  y = Z.zzfx_code("zzfx(...[,,925,.04,.3,.6,1,.3,,6.27,-184,.09,.17]); // Game Over")   # 디자이너에서 복사한 줄 그대로
  Z.write_wav("out.wav", y)                                                   # 48 kHz 16비트(모노 → 스테레오)

  python3 tools/sound/zzfx.py "zzfx(...[,,537,.02,.02,.22,1,1.59,-6.98,4.97])" out.wav
  python3 tools/sound/zzfx.py --check        # 원본 README 예시 넷으로 길이·최고점·RMS·스펙트럼 중심 확인

값 순서(원본과 같음) — volume, randomness, frequency, attack, sustain, release, shape, shapeCurve, slide, deltaSlide,
  pitchJump, pitchJumpTime, repeatTime, noise, modulation, bitCrush, delay, sustainVolume, decay, tremolo, filter
  (v1.4.0은 21번째 값 filter가 있다: 양수 = 저역 통과, 음수 = 고역 통과, 2차 바이쿼드 Q=2. 원본 식 그대로 차단 주파수는 2×|filter| Hz)
  shape: 0 사인 · 1 삼각 · 2 톱니 · 3 탄젠트 · 4 잡음 · 5 사각(펄스 폭 = shapeCurve/2)

원본(44.1 kHz)과 다른 점
  1. 기본 표본율이 48 kHz다(우리 영상 표준). 모든 시간·주파수 값은 원본처럼 표본율로 나눠 계산하므로 같은 소리가 난다.
     sample_rate=44100 을 주면 원본과 같은 표본율로 만든다.
     대조(2026-11-18): 원본 ZzFX.js 의 buildSamples 글(읽고 검토한 순수 계산 부분)을 node 로 돌린 값과 이 함수(44.1 kHz, 같은 난수)를
     README 예시 넷 + 여러 기능(삼각 · 톱니 · 탄젠트 · 잡음 · 사각, bitCrush, delay, 저역/고역 filter, repeat · tremolo, pitchJump,
     modulation, deltaSlide)을 쓰는 값 여섯으로 비교 — 길이 같음, 표본 최대 차이 1.2e-7 이하(원본이 Float32Array 에 담는 반올림 차이).
  2. 원본은 '표본 개수'로 정해진 값이 둘 있다: bitCrush(100×bitCrush 표본마다 값 유지)와 attack 0일 때의 최소 9표본.
     48 kHz에서는 keep_time=True(기본)로 이 둘을 시간으로 맞춘다(48000/44100 배). 그래서 bitCrush의 '거친 정도'가 원본과 같게 들린다.
  3. noise 값과 shape 4(잡음)는 원본이 표본 번호·위상으로 만드는 '정해진 잡음'이라, 표본율이 바뀌면 잡음 알갱이의 무늬가 조금 달라진다
     (밝기·세기는 비슷). 똑같은 무늬가 필요하면 sample_rate=44100 으로 만든 뒤 바꿔 쓴다.
  4. randomness(음높이 무작위 ±5%)는 원본이 Math.random()을 쓴다. 여기서는 seed=0(기본)이면 늘 같은 소리가 나고,
     seed=None 이면 원본처럼 부를 때마다 조금씩 다르다. 원본 디자이너의 ZZFXSound 처럼 무작위를 끄려면 randomness=0.
  5. 원본 재생기는 소리 위에 전체 음량 0.3(ZZFX.volume)을, 디자이너의 wav 저장은 0.5를 곱한다. 이 함수는 원본 buildSamples 처럼
     그 곱셈 전의 값(최대 ±volume)을 돌려준다. 음량 맞춤은 쓰는 쪽에서 한다(예: sfx_class.py 의 level()).
  6. 순수 파이썬 반복문이라 1초짜리 소리에 0.1~0.3초쯤 걸린다(효과음용으로 충분).

----------------------------------------------------------------------------------------------------
원본 저작권 고지와 라이선스(전문, 원본 그대로):

ZzFX MIT License

Copyright (c) 2019 - Frank Force

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
----------------------------------------------------------------------------------------------------
"""
import math, os, random, re, sys, wave

import numpy as np

SR = 48000            # 우리 기본 표본율
ORIG_SR = 44100       # 원본 표본율

PARAMS = ('volume', 'randomness', 'frequency', 'attack', 'sustain', 'release', 'shape', 'shapeCurve', 'slide', 'deltaSlide',
          'pitchJump', 'pitchJumpTime', 'repeatTime', 'noise', 'modulation', 'bitCrush', 'delay', 'sustainVolume', 'decay',
          'tremolo', 'filter')
DEFAULTS = (1, .05, 220, 0, 0, .1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0)

# 원본 README 의 예시 소리(값 그대로) — --check 에 쓴다
README_EXAMPLES = {
    'Game Over': "zzfx(...[,,925,.04,.3,.6,1,.3,,6.27,-184,.09,.17]); // Game Over",
    'Heart': "zzfx(...[,,537,.02,.02,.22,1,1.59,-6.98,4.97]); // Heart",
    'Piano': "zzfx(...[1.5,.8,270,,.1,,1,1.5,,,,,,,,.1,.01]); // Piano",
    'Drum': "zzfx(...[,,129,.01,,.15,,,,,,,,5]); // Drum",
}


def _resolve(args, kw):
    if len(args) > len(PARAMS):
        raise TypeError(f"zzfx 값은 최대 {len(PARAMS)}개입니다(받은 수 {len(args)})")
    vals = list(DEFAULTS)
    for i, a in enumerate(args):
        if a is not None: vals[i] = a
    for k, v in kw.items():
        if k not in PARAMS: raise TypeError(f"모르는 값 이름: {k}")
        if v is not None: vals[PARAMS.index(k)] = v
    return [float(v) for v in vals]


def build_samples(volume=1, randomness=.05, frequency=220, attack=0, sustain=0, release=.1, shape=0, shapeCurve=1,
                  slide=0, deltaSlide=0, pitchJump=0, pitchJumpTime=0, repeatTime=0, noise=0, modulation=0, bitCrush=0,
                  delay=0, sustainVolume=1, decay=0, tremolo=0, filter=0, *, sample_rate=SR, seed=0, keep_time=True, rand=None):
    """원본 ZZFX.buildSamples 를 한 줄씩 옮긴 것. 모노 float64 배열(최대 ±volume)을 돌려준다.
    rand: 0~1 사이 수를 주면 Math.random() 대신 그 값을 쓴다(원본 대조용)."""
    sampleRate = float(sample_rate)
    ratio = sampleRate / ORIG_SR if keep_time else 1.0
    PI2 = math.pi * 2
    sign = lambda v: -1.0 if v < 0 else 1.0
    if rand is None:
        rand = (random.Random(seed) if seed is not None else random.Random()).random()

    slide *= 500 * PI2 / sampleRate / sampleRate
    startSlide = slide
    frequency *= (1 + randomness * 2 * rand - randomness) * PI2 / sampleRate
    startFrequency = frequency
    modOffset = 0          # modulation offset
    repeat = 0             # repeat offset
    crush = 0              # bit crush offset
    jump = 1               # pitch jump timer
    t = 0.0                # sample time(위상)
    s = 0.0                # sample value

    # biquad LP/HP filter
    quality = 2
    w = PI2 * abs(filter) * 2 / sampleRate
    cosw = math.cos(w); alpha = math.sin(w) / 2 / quality
    a0 = 1 + alpha; a1 = -2 * cosw / a0; a2 = (1 - alpha) / a0
    b0 = (1 + sign(filter) * cosw) / 2 / a0
    b1 = -(sign(filter) + cosw) / a0; b2 = b0
    x2 = x1 = y2 = y1 = 0.0

    # scale by sample rate
    minAttack = 9 * ratio  # prevent pop if attack is 0 (원본 9표본 — keep_time 이면 같은 시간)
    attack = attack * sampleRate or minAttack
    decay *= sampleRate
    sustain *= sampleRate
    release *= sampleRate
    delay *= sampleRate
    deltaSlide *= 500 * PI2 / sampleRate ** 3
    modulation *= PI2 / sampleRate
    pitchJump *= PI2 / sampleRate
    pitchJumpTime *= sampleRate
    repeatTime = int(repeatTime * sampleRate)           # JS: x|0 (0 쪽으로 버림)
    crushEvery = int(bitCrush * 100)                    # JS: bitCrush*100|0
    if ratio != 1.0: crushEvery = int(round(crushEvery * ratio))   # keep_time: 원본과 같은 시간만큼 값 유지

    length = int(attack + decay + sustain + release + delay)
    if length <= 0: return np.zeros(0)
    b = [0.0] * length
    if volume == 0: return np.zeros(length)
    sin, cos, tan, fmod, floor = math.sin, math.cos, math.tan, math.fmod, math.floor
    for i in range(length):
        crush += 1
        if crushEvery == 0 or crush % crushEvery == 0:          # bit crush(원본: !(++crush % d), d=0 이면 늘 참)
            if shape:                                             # wave shape
                if shape > 1:
                    if shape > 2:
                        if shape > 3:
                            if shape > 4:
                                s = 1.0 if fmod(t / PI2, 1) < shapeCurve / 2 else -1.0   # 5 square duty
                            else:
                                s = sin(t ** 3)                                        # 4 noise
                        else:
                            s = max(min(tan(t), 1.0), -1.0)                            # 3 tan
                    else:
                        s = 1 - fmod(fmod(2 * t / PI2, 2) + 2, 2)                      # 2 saw
                else:
                    s = 1 - 4 * abs(floor(t / PI2 + .5) - t / PI2)                     # 1 triangle (JS Math.round)
            else:
                s = sin(t)                                                             # 0 sin

            trem = (1 - tremolo + tremolo * sin(PI2 * i / repeatTime)) if repeatTime else 1.0   # tremolo
            cv = s if shape > 4 else sign(s) * abs(s) ** shapeCurve                    # shape curve
            if i < attack: env = i / attack                                            # attack
            elif i < attack + decay: env = 1 - ((i - attack) / decay) * (1 - sustainVolume)   # decay falloff
            elif i < attack + decay + sustain: env = sustainVolume                     # sustain volume
            elif i < length - delay: env = (length - i - delay) / release * sustainVolume   # release falloff
            else: env = 0.0                                                            # post release
            s = trem * cv * env

            if delay:                                                                  # delay(되먹임 메아리)
                s = s / 2 + (0.0 if delay > i else
                             (1.0 if i < length - delay else (length - i) / delay) * b[int(i - delay)] / 2 / volume)

            if filter:                                                                 # apply filter
                out = b2 * x2 + b1 * x1 + b0 * s - a2 * y2 - a1 * y1
                x2 = x1; x1 = s; y2 = y1; y1 = out; s = out

        b[i] = s * volume                                                              # sample

        slide += deltaSlide                                                            # frequency
        frequency += slide
        f = frequency * cos(modulation * modOffset)                                    # modulation
        modOffset += 1
        t += f + f * noise * (fmod(i * i * PI2, 2) - 1)                                # noise

        if jump:                                                                       # pitch jump
            jump += 1
            if jump > pitchJumpTime:
                frequency += pitchJump
                startFrequency += pitchJump
                jump = 0

        if repeatTime:                                                                 # repeat
            repeat += 1
            if repeat % repeatTime == 0:
                frequency = startFrequency
                slide = startSlide
                jump = jump or 1
    return np.asarray(b, dtype=np.float64)


def zzfx(*args, sample_rate=SR, seed=0, keep_time=True, **kw):
    """원본 zzfx(...) 와 같은 값 순서·기본값. None 은 기본값. 모노 float64 배열."""
    return build_samples(*_resolve(args, kw), sample_rate=sample_rate, seed=seed, keep_time=keep_time)


def parse_code(text):
    """디자이너에서 복사한 줄 → 값 목록(빈 칸 = None).
    받는 꼴: 'zzfx(...[,,925,.04]); // 이름' · 'zzfx(1,.05,220)' · 'new Sound([...])' · 'zzfx({...}) -- 이름' · '[,,925,.04]' · ',,925,.04'"""
    s = text.split('//')[0].split('--')[0].strip()
    m = re.search(r'\[([^\]]*)\]', s) or re.search(r'\{([^}]*)\}', s) or re.search(r'zzfx\s*\(([^)]*)\)', s)
    body = m.group(1) if m else s
    out = []
    for p in body.split(','):
        p = p.strip()
        if p in ('', 'undefined', 'null', 'nil'): out.append(None); continue
        out.append(float(p))
    while out and out[-1] is None: out.pop()
    return out


def zzfx_code(text, **opt):
    """'zzfx(...[,,925,.04,.3,.6,1,.3,,6.27,-184,.09,.17])' 처럼 디자이너에서 복사한 줄을 그대로 넣는다."""
    return zzfx(*parse_code(text), **opt)


# ───────── 쓰기 · 확인 도우미 ─────────
def write_wav(path, y, sr=SR, stereo=True):
    """float 배열(모노 또는 (n,2)) → 16비트 wav. 1을 넘으면 잘린다(먼저 음량을 맞출 것)."""
    y = np.asarray(y, dtype=np.float64)
    if y.ndim == 1 and stereo: y = np.stack([y, y], 1)
    ch = 1 if y.ndim == 1 else y.shape[1]
    tmp = path + '.tmp.wav'
    with wave.open(tmp, 'wb') as w:
        w.setnchannels(ch); w.setsampwidth(2); w.setframerate(int(sr))
        w.writeframes((np.clip(y, -1, 1) * 32767).astype('<i2').tobytes())
    os.replace(tmp, path)


def describe(y, sr=SR):
    """길이 · 최고점 · RMS · 스펙트럼 중심 · 밝은 대역 비율(간단한 확인용)."""
    if not len(y): return dict(sec=0.0)
    S = np.abs(np.fft.rfft(y * np.hanning(len(y)))) ** 2; f = np.fft.rfftfreq(len(y), 1 / sr)
    tot = S.sum() + 1e-20
    return dict(sec=round(len(y) / sr, 3), peak_db=round(20 * math.log10(np.max(np.abs(y)) + 1e-12), 1),
                rms_db=round(20 * math.log10(np.sqrt(np.mean(y ** 2)) + 1e-12), 1),
                centroid_hz=int((f * S).sum() / tot), above_4k=round(float(S[f > 4000].sum() / tot), 3),
                dc=round(float(np.mean(y)), 4))


def _check():
    import time
    print('원본 README 예시 넷(값 그대로, seed=0) — 48 kHz')
    for name, code in README_EXAMPLES.items():
        t0 = time.time(); y = zzfx_code(code); dt = time.time() - t0
        y44 = zzfx_code(code, sample_rate=ORIG_SR)
        d, d44 = describe(y), describe(y44, ORIG_SR)
        print(f"  {name:9s} {d['sec']:5.2f}초  최고점 {d['peak_db']:6.1f} dB  RMS {d['rms_db']:6.1f} dB  중심 {d['centroid_hz']:5d} Hz"
              f"  4kHz 위 {d['above_4k']:.2f}  | 44.1k: {d44['sec']:5.2f}초 중심 {d44['centroid_hz']:5d} Hz  ({dt:.2f}초 걸림)")


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a or a[0] in ('-h', '--help'):
        print(__doc__.split('-' * 100)[0]); sys.exit(0)
    if a[0] == '--check':
        _check(); sys.exit(0)
    code = a[0]; out = a[1] if len(a) > 1 else 'zzfx.wav'
    y = zzfx_code(code)
    pk = np.max(np.abs(y)) or 1.0
    write_wav(out, y * min(1.0, 0.891 / pk))       # 최고점 −1 dBFS 아래로만 줄여 저장
    print(out, describe(y))
