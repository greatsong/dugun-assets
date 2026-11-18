#!/usr/bin/env python3
"""끝 화면(15초) 음악 시안 2차 — 후보 D~I. 직접 합성(numpy만 사용, 외부 음원·샘플·유료 API 없음).

  python3 pipeline/outro_synth2.py <D|E|F|G|H|I> <crown초> <ding초> <out.wav> [--report]
  python3 pipeline/outro_synth2.py all <crown초> <ding초> <out 폴더>

  D 로파이 건반(내림 마 장조 80)   · E 피치카토 발걸음(라 장조 124) · F 8비트 모험(가 장조 140)
  G 햇살 기타(마 장조 104)         · H 상쾌한 신스팝(내림 가 장조 122) · I 관악대 행진(내림 나 장조 116)

1차(outro_synth.py의 A·B·C)와 같은 약속: 길이 15초·48 kHz 스테레오, 왕관이 내려오는 순간(crown)에 올라가는 반짝 소리,
다음 섬에 불이 켜지는 순간(ding)에 종 한 번. 달라진 점:
- 반짝 소리의 음을 '그 순간에 울리는 화음'에서 고른다(어느 편에 얹어도 어긋나지 않게).
- 악기별 줄기(stem)로 섞고, 잔향(높은 소리가 먼저 사라지는 방)·메아리·옆사슬 누르기·부드러운 리미터를 거친다.
- 모든 곡을 같은 음량(−20 LUFS)으로 맞춰 내보낸다. 처음 4 ms와 끝 0.6초는 페이드.
실존 곡의 선율을 쓰지 않았다(직접 지은 짧은 선율).
"""
import functools, os, sys, wave
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from outro_synth import SR, N, NOTE, hz, glock     # 1차 파일의 도우미(읽기만)

rng = np.random.default_rng(21)
PI2 = 2 * np.pi


def seed(k):
    global rng
    rng = np.random.default_rng(k)


def tt(dur):
    return np.arange(max(1, int(round(dur * SR)))) / SR


def midi(name):
    return NOTE[name[:-1]] + 12 * (int(name[-1]) + 1)


def mhz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


# ───────── 거르개(주파수 영역, 위상 변화 없음) ─────────
def fftfilt(y, fn):
    n = y.shape[0]; nf = 1 << int(np.ceil(np.log2(n + 4096)))
    g = fn(np.fft.rfftfreq(nf, 1 / SR))
    if y.ndim == 1: return np.fft.irfft(np.fft.rfft(y, nf) * g, nf)[:n]
    return np.stack([np.fft.irfft(np.fft.rfft(y[:, c], nf) * g, nf)[:n] for c in range(y.shape[1])], 1)


def g_lp(fc, order=2):
    return lambda f: 1 / np.sqrt(1 + (f / fc) ** (2 * order))


def g_hp(fc, order=2):
    return lambda f: 1 / np.sqrt(1 + (fc / np.maximum(f, 1e-3)) ** (2 * order))


def g_bell(f0, db, width=0.5):      # width: 옥타브 단위 폭
    return lambda f: 10 ** (db / 20 * np.exp(-0.5 * (np.log2(np.maximum(f, 1e-3) / f0) / width) ** 2))


def g_shelf(fc, db):                # 높은 쪽 선반
    return lambda f: 10 ** (db / 20 * (1 / (1 + (fc / np.maximum(f, 1e-3)) ** 2)))


def chain(*gs):
    def fn(f):
        g = np.ones(len(f))
        for x in gs: g = g * x(f)
        return g
    return fn


def conv(x, ir):
    nf = 1 << int(np.ceil(np.log2(len(x) + len(ir))))
    return np.fft.irfft(np.fft.rfft(x, nf) * np.fft.rfft(ir, nf), nf)[: len(x)]


def norm(y):
    return y / (np.max(np.abs(y)) + 1e-9)


def layer(*ys):
    """길이가 다른 소리를 겹친다."""
    out = np.zeros(max(len(y) for y in ys))
    for y in ys: out[: len(y)] += y
    return out


# ───────── 음량(BS.1770)·리미터 ─────────
def lufs_np(x):
    n = len(x); nf = 1 << int(np.ceil(np.log2(n + 8192)))
    z1 = np.exp(-1j * PI2 * np.fft.rfftfreq(nf)); z2 = z1 * z1
    H = ((1.53512485958697 - 2.69169618940638 * z1 + 1.19839281085285 * z2) / (1 - 1.69065929318241 * z1 + 0.73248077421585 * z2)
         * (1 - 2 * z1 + z2) / (1 - 1.99004745483398 * z1 + 0.99007225036621 * z2))
    k = np.stack([np.fft.irfft(np.fft.rfft(x[:, c], nf) * H, nf)[:n] for c in (0, 1)], 1)
    blk = int(0.4 * SR); hop = blk // 4
    p = np.array([np.mean(k[i:i + blk] ** 2, axis=0).sum() for i in range(0, n - blk + 1, hop)])
    lv = lambda q: -0.691 + 10 * np.log10(q + 1e-12)
    g = p[lv(p) > -70]
    if not len(g): return -99.0
    g2 = g[lv(g) > lv(g.mean()) - 10]
    return float(lv(g2.mean()))


def limiter(x, ceil=0.7, look=0.004, rel=0.10):
    """미리 보기 리미터 — 꼭대기만 부드럽게 누른다(찌그러짐 없이)."""
    hop = 16; nb = len(x) // hop + 1
    pk = np.zeros(nb * hop); pk[: len(x)] = np.max(np.abs(x), axis=1)
    need = np.minimum(1.0, ceil / np.maximum(pk.reshape(nb, hop).max(1), 1e-9))
    Lb = max(1, int(look * SR / hop)); g = need.copy()
    for s in range(1, 2 * Lb + 1):
        g[:-s] = np.minimum(g[:-s], need[s:]); g[s:] = np.minimum(g[s:], need[:-s])
    c = np.exp(-hop / (rel * SR)); out = np.empty(nb); cur = 1.0
    for i in range(nb):
        cur = min(g[i], 1 - (1 - cur) * c); out[i] = cur
    out = np.convolve(np.pad(out, Lb, mode='edge'), np.ones(2 * Lb + 1) / (2 * Lb + 1), mode='valid')
    gs = np.interp(np.arange(len(x)), np.arange(nb) * hop + hop / 2, out)
    return x * gs[:, None]


@functools.lru_cache(maxsize=None)
def make_ir(rt60=1.6, bright=6500.0, lowcut=220.0, seedk=5):
    """방 울림: 이른 반사 몇 개 + 높은 소리가 먼저 사라지는 꼬리. 좌우는 서로 다른 잡음."""
    r = np.random.default_rng(seedk); L = int((rt60 * 1.15 + 0.1) * SR); t = np.arange(L) / SR; tau = rt60 / 6.91; irs = []
    for ch in (0, 1):
        x = r.standard_normal(L); lo = fftfilt(x, g_lp(2200, 2)); hi = x - lo
        y = (lo * np.exp(-t / tau) + hi * np.exp(-t / (0.55 * tau))) * np.minimum(1, t / 0.03) ** 0.7
        y /= np.sqrt(np.sum(y ** 2))
        for d, g in ((0.007, 0.22), (0.013, -0.18), (0.019, 0.16), (0.027, 0.13), (0.038, -0.10)):
            y[int(d * (1 + 0.17 * ch) * SR)] += g
        pre = int(0.012 * SR); y = np.concatenate([np.zeros(pre), y])[:L]
        y = fftfilt(y, chain(g_hp(lowcut, 2), g_lp(bright, 2)))
        irs.append(y / np.sqrt(np.sum(y ** 2)))
    return irs[0], irs[1]


class Mix2:
    """악기별 줄기로 모았다가 한꺼번에 섞는다. 줄기마다 잔향·메아리 보내는 양과 효과(fx)를 정한다."""

    def __init__(self):
        self.L = N + 3 * SR; self.st = {}; self.cfg = {}; self.levels = {}

    def stem(self, name, wet=0.2, dly=0.0, gain=1.0, fx=None):
        self.cfg[name] = dict(wet=wet, dly=dly, gain=gain, fx=fx); self.st[name] = np.zeros((self.L, 2))

    def add(self, name, y, at, gain=1.0, pan=0.0):
        i = int(round(at * SR))
        if i < 0: y = y[-i:]; i = 0
        if i >= N or len(y) == 0: return
        if y.ndim == 1:
            th = (np.clip(pan, -1, 1) + 1) * np.pi / 4; y = np.stack([y * np.cos(th), y * np.sin(th)], 1)
        elif pan:
            y = y * np.array([min(1.0, 1 - pan), min(1.0, 1 + pan)])
        y = y[: self.L - i] * gain
        k = min(len(y) // 4, int(0.03 * SR))          # 끝을 30 ms 페이드 — 덜 사그라든 소리가 뚝 끊겨 '틱' 하지 않게
        if k > 1: y[-k:] *= (np.cos(np.linspace(0, np.pi / 2, k)) ** 2).reshape((k,) + (1,) * (y.ndim - 1))
        self.st[name][i:i + len(y)] += y

    def render(self, rt60=1.6, rev=1.0, bright=6500.0, dtime=0.3, dfb=0.4, master=None, target=-20.0, limit_db=3.0, fade_out=0.6):
        dry = np.zeros((self.L, 2)); send = np.zeros((self.L, 2)); dsend = np.zeros(self.L)
        for name, y in self.st.items():
            c = self.cfg[name]
            if c['fx']: y = c['fx'](y)
            y = y * c['gain']; self.levels[name] = y[:N]
            dry += y; send += y * c['wet']
            if c['dly']: dsend += y.sum(1) * c['dly']
        if np.any(dsend):          # 좌우를 오가는 메아리
            src = fftfilt(dsend, chain(g_hp(300, 1), g_lp(3200, 1))); d = int(dtime * SR); dl = np.zeros((self.L, 2))
            for k in range(1, 6):
                i = k * d
                if i >= self.L: break
                g = dfb ** (k - 1); ch = (k + 1) % 2
                dl[i:, ch] += 0.66 * g * src[: self.L - i]; dl[i:, 1 - ch] += 0.42 * g * src[: self.L - i]
            dry += dl; send += 0.35 * dl
        irL, irR = make_ir(rt60, bright)
        out = dry + rev * np.stack([conv(send[:, 0], irL), conv(send[:, 1], irR)], 1)
        out = fftfilt(out[:N], chain(g_hp(32, 2), master) if master else g_hp(32, 2))
        a = int(0.004 * SR); out[:a] *= np.linspace(0, 1, a)[:, None]
        f = int(fade_out * SR); out[-f:] *= (np.cos(np.linspace(0, np.pi / 2, f)) ** 2)[:, None]
        self.pre_peak = float(np.max(np.abs(out)))
        out = out / self.pre_peak
        if limit_db > 0: out = limiter(out, 10 ** (-limit_db / 20))
        out = out * 10 ** ((target - lufs_np(out)) / 20)
        pk = np.max(np.abs(out))
        if pk > 0.708: out = out * 0.708 / pk       # 최고점은 −3 dBFS를 넘지 않게
        return out

    def report(self):
        tot = np.sqrt(np.mean(sum(self.levels.values()) ** 2)) + 1e-12
        for k, y in self.levels.items():
            S = np.abs(np.fft.rfft(y.mean(1))) ** 2; f = np.fft.rfftfreq(len(y), 1 / SR)
            print(f"  {k:8s} rms {20 * np.log10(np.sqrt(np.mean(y ** 2)) / tot + 1e-12):6.1f} dB  peak {20 * np.log10(np.max(np.abs(y)) / self.pre_peak + 1e-12):6.1f} dB  중심 {int((f * S).sum() / (S.sum() + 1e-12)):5d} Hz")


# ───────── 줄기 효과 ─────────
def duck_env(times, depth=0.4, tau=0.13, hold=0.02):
    """킥이 칠 때마다 살짝 눌렀다 푸는 음량 곡선(옆사슬)."""
    n = N + 3 * SR; t = np.arange(n) / SR; e = np.ones(n)
    for tk in times:
        d = t - tk; e = np.minimum(e, np.where(d < -0.008, 1.0, np.where(d < hold, 1 - depth, 1 - depth * np.exp(-(d - hold) / tau))))
    e = np.convolve(e, np.ones(192) / 192, mode='same')
    return e[:, None]


def autopan(y, rate=1.1, depth=0.2):
    t = np.arange(len(y)) / SR; s = depth * np.sin(PI2 * rate * t)
    return y * np.stack([1 + s, 1 - s], 1)


# ───────── 악기 ─────────
@functools.lru_cache(maxsize=None)
def string(f, dur, pos=0.2, tau=1.0, damp=0.03, expo=1.2, B=5e-5, fmax=12000.0, att=0.0012):
    """뜯는 줄(모드 합성): 배음마다 따로 사그라든다. 음정이 정확하다."""
    t = tt(dur); y = np.zeros(len(t)); k = 1
    while k <= 64:
        fk = k * f * np.sqrt(1 + B * k * k)
        if fk > fmax: break
        a = np.sin(np.pi * k * pos) / k ** expo
        if abs(a) > 1e-3: y += a * np.sin(PI2 * fk * t) * np.exp(-t * (1 + damp * (k - 1) ** 2) / tau)
        k += 1
    return norm(y) * np.minimum(1, t / att)


def guitar(f, dur=2.2, vel=0.8):
    y = string(f, dur, pos=0.16, tau=1.0 * (196.0 / f) ** 0.3, damp=0.012 + 0.02 * (1 - vel), expo=1.15, B=4e-5, fmax=11000.0)
    t = tt(dur); pk = fftfilt(rng.standard_normal(len(t)), chain(g_hp(1500, 1), g_lp(6000, 1))) * np.exp(-t / 0.004)
    return (y + 0.05 * vel * norm(pk)) * vel


def harp(f, dur=2.6):
    return string(f, dur, pos=0.42, tau=0.85 * (261.6 / f) ** 0.35, damp=0.03, expo=1.5, fmax=9000.0)


def upbass(f, dur=1.2):
    """손가락으로 뜯는 콘트라베이스."""
    y = string(f, dur, pos=0.22, tau=0.55, damp=0.10, expo=1.25, B=1e-4, fmax=2600.0, att=0.004)
    t = tt(dur); th = np.sin(PI2 * 62 * t) * np.exp(-t / 0.02)
    return y + 0.12 * th


def pizz(f, dur=0.8, n=3, vel=0.8):
    """현악 피치카토(여럿이 함께): 살짝 다른 음높이·시각·자리로 겹친다. 스테레오."""
    L = int((dur + 0.03) * SR); out = np.zeros((L, 2)); tau = 0.19 * (220.0 / f) ** 0.4
    for i in range(n):
        det = 2 ** (rng.normal(0, 4) / 1200); dt = int(abs(rng.normal(0, 0.005)) * SR)
        y = string(round(f * det, 3), dur, pos=round(0.12 + 0.04 * rng.random(), 3), tau=round(tau, 4), damp=0.07, expo=1.0, fmax=8000.0, att=0.0015)
        p = (i / max(1, n - 1) - 0.5) * 0.9 if n > 1 else 0.0; th = (p + 1) * np.pi / 4
        out[dt:dt + len(y), 0] += y[: L - dt] * np.cos(th); out[dt:dt + len(y), 1] += y[: L - dt] * np.sin(th)
    return out * vel / np.sqrt(n)


@functools.lru_cache(maxsize=None)
def piano(f, dur, vel=0.7):
    """부드러운 피아노(더하기 합성): 줄 두 가닥의 미세한 어긋남, 빠른 소리 + 긴 여운, 해머 '톡'."""
    rel = 0.4; t = tt(dur + rel); y = np.zeros(len(t))
    B = 0.00022 * (f / 261.6) ** 1.2; tau0 = 0.85 * (261.6 / f) ** 0.5
    for k in range(1, 40):
        fk = k * f * np.sqrt(1 + B * k * k)
        if fk > 10000: break
        a = (0.3 + abs(np.sin(np.pi * k / 7.7))) / k ** (1.0 + 0.9 * (1 - vel)); ta = tau0 / k ** 0.6
        env = 0.7 * np.exp(-t / ta) + 0.3 * np.exp(-t / (4.5 * ta))
        y += a * env * (np.sin(PI2 * fk * 0.9995 * t) + 0.8 * np.sin(PI2 * fk * 1.0005 * t + 0.4 * k))
    nz = fftfilt(np.random.default_rng(int(f)).standard_normal(len(t)), g_lp(1800, 1)) * np.exp(-t / 0.006)
    y = norm(y) + 0.05 * vel * norm(nz)
    return y * np.minimum(1, t / 0.0015) * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.07)) * (0.4 + 0.6 * vel)


def rhodes(f, dur, vel=0.7, t_abs=0.0, wow=0.0):
    """일렉트릭 피아노(FM): 칠 때는 살짝 거칠고 곧 둥글어진다. wow = 테이프처럼 음높이가 아주 조금 흔들림."""
    rel = 0.2; t = tt(dur + rel)
    fm = 1 + wow * (0.0014 * np.sin(PI2 * 0.55 * (t + t_abs)) + 0.0004 * np.sin(PI2 * 6.1 * (t + t_abs)))
    ph = PI2 * f * np.cumsum(fm) / SR
    idx = (0.36 + 2.1 * vel * np.exp(-t / 0.25)) * min(1.3, (261.6 / f) ** 0.35)
    y = np.sin(ph + idx * np.sin(ph))
    for r_, a_, tau_ in ((4.0, 0.13, 0.30), (9.07, 0.05, 0.07)):
        if r_ * f < 9000: y += a_ * vel * np.sin(r_ * ph) * np.exp(-t / tau_)
    e = np.minimum(1, t / 0.004) * np.exp(-t / (1.9 * (261.6 / f) ** 0.45)) * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.05))
    n = min(len(t), int(0.06 * SR)); tick = np.zeros(len(t))          # 쇠막대를 때리는 짧은 '틱'
    tick[:n] = norm(fftfilt(rng.standard_normal(n), chain(g_hp(1800, 2), g_lp(5200, 2)))) * np.exp(-t[:n] / 0.008)
    return (y * e + 0.05 * vel * tick) * (0.45 + 0.55 * vel)


def celesta(f, dur=2.2):
    """첼레스타: 종보다 둥글고 부드러운 반짝 소리."""
    t = tt(dur); y = np.sin(PI2 * f * t) * np.exp(-t / (0.6 * (880.0 / f) ** 0.3))
    y += 0.22 * np.sin(PI2 * 2 * f * t) * np.exp(-t / 0.2)
    if 4.01 * f < 12000: y += 0.10 * np.sin(PI2 * 4.01 * f * t) * np.exp(-t / 0.07)
    return y * np.minimum(1, t / 0.003)


def vibes(f, dur=2.2):
    """비브라폰: 길게 울리고 천천히 떨린다."""
    t = tt(dur); y = np.sin(PI2 * f * t) * np.exp(-t / 1.1) + 0.14 * np.sin(PI2 * 4 * f * t) * np.exp(-t / 0.12)
    return y * (1 - 0.18 * (0.5 - 0.5 * np.cos(PI2 * 4.3 * t))) * np.minimum(1, t / 0.004)


def softflute(f, dur):
    rel = 0.2; t = tt(dur + rel); vib = 1 + 0.004 * np.sin(PI2 * 4.8 * t) * np.clip((t - 0.25) / 0.3, 0, 1)
    ph = PI2 * f * np.cumsum(vib) / SR
    y = np.sin(ph) + 0.16 * np.sin(2 * ph) + 0.05 * np.sin(3 * ph)
    br = fftfilt(rng.standard_normal(len(t)), chain(g_hp(f * 1.5, 1), g_lp(f * 5, 1)))
    y = y + 0.02 * norm(br)
    return y * (1 - np.exp(-t / 0.06)) * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.07))


@functools.lru_cache(maxsize=None)
def ens(freqs, dur, att=0.3, rel=0.6, fc=2400.0, voices=4, spread=9.0, vib=0.003, expo=1.0, seedk=3):
    """여럿이 함께 내는 지속음(현악 바탕·신스 패드). freqs는 튜플. 스테레오."""
    r = np.random.default_rng(seedk); n = int((dur + rel) * SR); t = np.arange(n) / SR; out = np.zeros((n, 2))
    for f in freqs:
        for v in range(voices):
            d = (v - (voices - 1) / 2) / max(0.5, (voices - 1) / 2) * spread + r.normal(0, 1.5); fd = f * 2 ** (d / 1200)
            vd = vib * np.clip((t - 0.15) / 0.5, 0, 1) * np.sin(PI2 * (5.0 + r.normal(0, 0.4)) * t + r.uniform(0, PI2))
            ph = PI2 * fd * np.cumsum(1 + vd) / SR + r.uniform(0, PI2); y = np.zeros(n)
            for k in range(1, int(min(32, 2.4 * fc / fd)) + 1):
                y += (1 / k ** expo) / np.sqrt(1 + (k * fd / fc) ** 4) * np.sin(k * ph)
            th = (np.clip(d / spread * 0.8, -1, 1) + 1) * np.pi / 4
            out[:, 0] += y * np.cos(th); out[:, 1] += y * np.sin(th)
    e = np.sin(np.minimum(1, t / att) * np.pi / 2) ** 2 * np.where(t < dur, 1.0, np.exp(-(t - dur) / (rel / 4)))
    return out * e[:, None] / (1.3 * np.sqrt(len(freqs) * voices))


@functools.lru_cache(maxsize=None)
def sawpluck(f, dur, fc0=5000.0, fc1=700.0, ftau=0.10, atau=0.35, det=7.0):
    """톱니파 플럭: 밝게 열렸다가 금방 둥글어지는 신스."""
    rel = 0.06; t = tt(dur + rel); cut = fc1 + (fc0 - fc1) * np.exp(-t / ftau); y = np.zeros(len(t))
    for d in ((-det, det) if det else (0.0,)):
        fd = f * 2 ** (d / 1200); ph = PI2 * fd * t
        for k in range(1, int(min(48, 9000 / fd)) + 1):
            y += (1 / k) / np.sqrt(1 + (k * fd / cut) ** 4) * np.sin(k * ph + 0.01 * d * k)
    e = np.minimum(1, t / 0.003) * np.exp(-t / atau) * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.02))
    return y * e / (3.0 if det else 1.6)


def bellpluck(f, dur=1.2):
    """신스 벨: 맑은 사인 + 짧은 FM 반짝."""
    t = tt(dur); ph = PI2 * f * t
    y = np.sin(ph + 1.1 * np.exp(-t / 0.05) * np.sin(2 * ph)) * np.exp(-t / 0.42) + 0.25 * np.sin(2 * ph) * np.exp(-t / 0.16)
    if 3 * f < 9000: y += 0.10 * np.sin(3 * ph) * np.exp(-t / 0.08)
    return y * np.minimum(1, t / 0.002)


def subbass(f, dur, bright=0.5):
    rel = 0.07; t = tt(dur + rel); ph = PI2 * f * t
    y = np.sin(ph) + (0.18 + 0.5 * bright * np.exp(-t / 0.25)) * np.sin(2 * ph) + (0.08 + 0.3 * bright * np.exp(-t / 0.15)) * np.sin(3 * ph) + 0.05 * np.sin(4 * ph)
    return y / 1.5 * np.minimum(1, t / 0.008) * np.exp(-t / 1.3) * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.025))


@functools.lru_cache(maxsize=None)
def brass(f, dur, vel=0.8, soft=0.0, fmax=7000.0, seedk=0):
    """금관(더하기 합성): 세게 불수록 높은 배음이 뒤따라 열린다. soft=1이면 호른·튜바처럼 둥글게."""
    r = np.random.default_rng(900 + seedk); rel = 0.10; t = tt(dur + rel); at = 0.03 + 0.03 * soft
    e = np.minimum(1, t / at) ** 1.5 * (1 - 0.2 * (1 - np.exp(-np.maximum(t - at, 0) / 0.15))) * np.where(t < dur, 1.0, np.exp(-(t - dur) / 0.03))
    br = vel * (0.3 + 0.7 * np.minimum(1, t / (at * 1.8))) * (1 - 0.18 * np.minimum(1, np.maximum(t - at * 1.8, 0) / 0.35)) * (1 - 0.55 * soft)
    vd = 0.0028 * np.clip((t - 0.28) / 0.3, 0, 1) * np.sin(PI2 * 5.2 * t + r.uniform(0, PI2))
    ph = PI2 * f * 2 ** (r.normal(0, 3) / 1200) * np.cumsum(1 + vd) / SR; y = np.zeros(len(t)); K = int(min(40, fmax / f))
    for k in range(1, K + 1):
        fk = k * f; fm = (1 + 1.0 * (1 - soft) * np.exp(-((fk - 1300) / 700) ** 2)) / np.sqrt(1 + (fk / (4400 - 2200 * soft)) ** 4)
        y += fm * np.exp(-(k - 1) / (0.8 + 3.6 * br)) * np.sin(k * ph - np.pi * k * (k - 1) / max(K, 2))
    return norm(y) * e * (0.5 + 0.5 * vel)


# 8비트(게임기) 소리
@functools.lru_cache(maxsize=None)
def pulse(f, dur, duty=0.25, vib=0.0, sus=0.7, fmax=8000.0):
    t = tt(dur); fr = f * (1 + vib * np.sin(PI2 * 6.0 * t) * np.clip((t - 0.16) / 0.1, 0, 1)); ph = PI2 * np.cumsum(fr) / SR; y = np.zeros(len(t))
    for k in range(1, int(fmax / f) + 1):
        y += (4 / (k * np.pi)) * np.sin(np.pi * k * duty) / np.sqrt(1 + (k * f / 6500) ** 4) * np.cos(k * ph)
    e = sus + (1 - sus) * np.exp(-t / 0.05); a = max(2, int(0.002 * SR))
    e[:a] *= np.linspace(0, 1, a); r = min(len(t), int(0.006 * SR)); e[-r:] *= np.linspace(1, 0, r)
    return y * e * 0.6


@functools.lru_cache(maxsize=None)
def tri(f, dur):
    t = tt(dur); ph = PI2 * f * t; y = np.zeros(len(t))
    for k in range(1, 20, 2):
        if k * f > 7000: break
        y += (8 / np.pi ** 2) * (-1) ** ((k - 1) // 2) / k ** 2 * np.sin(k * ph)
    a = max(2, int(0.003 * SR)); r = min(len(t), int(0.008 * SR)); y[:a] *= np.linspace(0, 1, a); y[-r:] *= np.linspace(1, 0, r)
    return y


def chipnoise(dur, rate, tau):
    t = tt(dur); step = max(1, int(SR / rate)); x = np.repeat(rng.choice([-1.0, 1.0], len(t) // step + 1), step)[: len(t)]
    return fftfilt(x, g_lp(7500, 2)) * np.exp(-t / tau) * np.minimum(1, t / 0.001)


# 타악기
def kick2(f0=115.0, f1=47.0, ptau=0.03, tau=0.15, click=0.08, dur=0.5):
    t = tt(dur); f = f1 + (f0 - f1) * np.exp(-t / ptau)
    c = fftfilt(rng.standard_normal(len(t)), g_lp(2500, 1)) * np.exp(-t / 0.004)
    return (np.sin(PI2 * np.cumsum(f) / SR) * np.exp(-t / tau) + click * norm(c)) * np.minimum(1, t / 0.0015)


def snare2(tone=190.0, tau_b=0.05, tau_n=0.10, lo=1200.0, hi=8000.0, mixn=0.7, dur=0.35):
    t = tt(dur); body = (np.sin(PI2 * tone * t) + 0.6 * np.sin(PI2 * 1.72 * tone * t)) * np.exp(-t / tau_b) / 1.6
    nz = norm(fftfilt(rng.standard_normal(len(t)), chain(g_hp(lo, 2), g_lp(hi, 2))))
    return ((1 - mixn) * body + mixn * nz * np.exp(-t / tau_n)) * np.minimum(1, t / 0.001)


def hat(tau=0.03, lo=7000.0, hi=11500.0):
    t = tt(max(0.08, tau * 6)); nz = norm(fftfilt(rng.standard_normal(len(t)), chain(g_hp(lo, 3), g_lp(hi, 2))))
    return nz * np.exp(-t / tau) * np.minimum(1, t / 0.001)


def clap():
    t = tt(0.45); nz = norm(fftfilt(rng.standard_normal(len(t)), chain(g_hp(900, 2), g_lp(5500, 2)))); e = np.zeros(len(t))
    for d in (0.0, 0.011, 0.021): e += 0.7 * np.where(t >= d, np.exp(-(t - d) / 0.007), 0)
    e += np.where(t >= 0.03, np.exp(-(t - 0.03) / 0.09), 0)
    return nz * e


def shaker2(vel=1.0):
    t = tt(0.22); nz = norm(fftfilt(rng.standard_normal(len(t)), chain(g_hp(3500, 2), g_lp(9500, 2))))
    return vel * nz * np.minimum(1, t / 0.014) * np.exp(-np.maximum(t - 0.014, 0) / 0.04)


def crash(dur=2.4):
    t = tt(dur); nz = norm(fftfilt(rng.standard_normal(len(t)), chain(g_hp(3000, 2), g_lp(10500, 2))))
    return nz * (0.7 * np.exp(-t / 0.3) + 0.3 * np.exp(-t / 0.9)) * np.minimum(1, t / 0.003)


def riser(dur=1.0):
    """신스팝의 '쉬이익' 올라가는 바람 소리."""
    t = tt(dur); x = rng.standard_normal(len(t)); n = len(t); nb = 8; y = np.zeros(n)
    for i in range(nb):       # 구간마다 통과 대역을 위로 옮긴다
        a, b_ = i * n // nb, (i + 1) * n // nb; fc = 800 * (9000 / 800) ** (i / (nb - 1))
        seg = fftfilt(x, chain(g_hp(fc * 0.6, 2), g_lp(fc * 1.4, 2))); w = np.zeros(n); w[a:b_] = 1
        y += seg * np.convolve(w, np.hanning(n // nb), mode='same') / (n / nb / 2)
    return norm(y) * (t / dur) ** 2 * np.minimum(1, (dur - t) / 0.01)


def rim():
    t = tt(0.14); c = fftfilt(rng.standard_normal(len(t)), chain(g_hp(600, 1), g_lp(4500, 1))) * np.exp(-t / 0.006)
    return ((0.6 * np.sin(PI2 * 1650 * t) + np.sin(PI2 * 470 * t)) * np.exp(-t / 0.014) + 0.5 * norm(c)) * np.minimum(1, t / 0.0008) / 1.6


# ───────── 반짝 소리(왕관·불빛): 그 순간의 화음에서 음을 고른다 ─────────
def harm_at(tl, t, look=0.0):
    cur = tl[0]
    for x in tl:
        if x[0] <= t + look: cur = x
    return cur[1], cur[2]


def penta(root, q):
    return {(NOTE[root] + x) % 12 for x in ((0, 2, 4, 7, 9) if q == 'M' else (0, 3, 5, 7, 10))}


def run_notes(pcs, top, n):
    out = []; mm = top
    while len(out) < n:
        if mm % 12 in pcs: out.append(mm)
        mm -= 1
    return out[::-1]


def accents(m, stem, tl, crown, ding, inst_run, inst_bell, top=91, n=6, step=0.055, g_run=0.2, g_bell=0.42, bell_at=81):
    """왕관: crown에 꼭대기 음이 닿는 오름 줄 · 불빛: ding에 종 하나 + 4도 위 메아리 음.
    음은 그 순간의 화음(5음 음계)에서 고른다. 종은 길게 울리므로 0.25초 안에 화음이 바뀌면 다음 화음을 따른다."""
    root, q = harm_at(tl, crown); ns = run_notes(penta(root, q), top, n)
    for i, mm in enumerate(ns):
        m.add(stem, inst_run(mhz(mm)), crown - 0.005 - (n - 1 - i) * step, g_run * (0.7 + 0.3 * i / (n - 1)), pan=-0.4 + 0.8 * i / (n - 1))
    root, q = harm_at(tl, ding, 0.25); pc = (NOTE[root] + 7) % 12
    b1 = min((mm for mm in range(bell_at - 6, bell_at + 7) if mm % 12 == pc), key=lambda mm: abs(mm - bell_at))
    m.add(stem, inst_bell(mhz(b1)), ding, g_bell, pan=0.15); m.add(stem, inst_bell(mhz(b1 + 5)), ding + 0.09, g_bell * 0.5, pan=-0.25)


# ═════════ 후보 D ~ I ═════════
def cand_D(crown, ding):
    """로파이 건반 — 내림 마 장조, 80 BPM. 포근한 일렉트릭 피아노 + 느긋한 비트."""
    seed(104); bt = 60 / 80; t0 = 0.42; m = Mix2(); lazy = 0.07
    T = lambda bar, beat: t0 + (bar * 4 + beat + (lazy if abs(beat % 1 - 0.5) < 1e-6 else 0)) * bt
    prog = [('Eb3', ['Bb3', 'D4', 'F4', 'G4'], 'Eb', 'M'), ('C3', ['Bb3', 'D4', 'Eb4', 'G4'], 'C', 'm'),
            ('Ab2', ['Bb3', 'C4', 'Eb4', 'G4'], 'Ab', 'M'), ('Bb2', ['Ab3', 'C4', 'Eb4', 'F4'], 'Bb', 'M')]
    mel = [[(0.5, 'Bb4', 0.5), (1, 'C5', 0.5), (1.5, 'Eb5', 1.3), (3, 'G5', 1.0)], [(0, 'F5', 0.9), (1, 'Eb5', 0.5), (1.5, 'C5', 1.3), (3, 'Eb5', 1.0)],
           [(0.5, 'Bb4', 0.5), (1, 'C5', 0.5), (1.5, 'Eb5', 1.3), (3, 'Bb5', 1.0)], [(0, 'G5', 0.9), (1, 'F5', 0.5), (1.5, 'Eb5', 1.3), (3, 'F5', 0.9)]]
    kicks = [T(bar, beat) for bar in range(4) for beat in (0, 2.5)] + [t0 + 16 * bt]
    dk = duck_env(kicks, 0.22, 0.16)
    soft = chain(g_lp(6500, 2), g_bell(300, 1.5, 1.0))
    m.stem('keys', wet=0.22, dly=0.10, fx=lambda y: autopan(fftfilt(y, soft), 0.9, 0.16) * dk)
    m.stem('lead', wet=0.28, dly=0.30, fx=lambda y: fftfilt(y, g_lp(8000, 2)))
    m.stem('bass', wet=0.03, fx=lambda y: fftfilt(y, g_lp(900, 2)) * dk)
    m.stem('drums', wet=0.12, fx=lambda y: fftfilt(y, g_lp(10500, 2)))
    m.stem('fx', wet=0.5, dly=0.25)
    for i, at in enumerate((t0 - bt / 2, t0 - bt / 4)): m.add('drums', hat(0.022, 6000, 10000), at, 0.05 + 0.03 * i, pan=0.35)      # 살며시 들어오는 하이햇 두 번
    tl = [(0.0, 'Eb', 'M')]
    for bar, (root, ch, rn, q) in enumerate(prog):
        tl.append((T(bar, 0), rn, q))
        for beat, ln, v in ((0, 2.3, 0.62), (2.5, 1.4, 0.42)):          # 화음: 첫 박에 길게, 셋째 박 앞에서 가볍게 한 번 더
            for j, nm in enumerate(ch):
                at = T(bar, beat) + j * 0.014 + rng.normal(0, 0.003)
                m.add('keys', rhodes(hz(nm), ln * bt, v + rng.normal(0, 0.03), at, 1.0), at, 0.15, pan=-0.3 + 0.2 * j)
        f = hz(root)
        m.add('bass', subbass(f, 1.6 * bt, 0.6), T(bar, 0), 0.50); m.add('bass', subbass(f, 0.4 * bt, 0.5), T(bar, 2.5), 0.36)
        m.add('bass', subbass(f * (1.5 if bar != 3 else 1.0), 0.9 * bt, 0.5), T(bar, 3), 0.42)
        for nb, nm, ln in mel[bar]:
            at = T(bar, nb) + rng.normal(0, 0.004)
            m.add('lead', rhodes(hz(nm), ln * bt, 0.9, at, 1.0), at, 0.36, pan=0.08)
            m.add('lead', vibes(hz(nm) * 2, 2.0), at, 0.07, pan=0.3)
        for beat, v in ((0, 1.0), (2.5, 0.8)): m.add('drums', kick2(105, 45, 0.035, 0.17, 0.06), T(bar, beat), 0.58 * v)
        for beat in (1, 3):
            at = T(bar, beat) + 0.012
            m.add('drums', snare2(175, 0.06, 0.09, 900, 7500, 0.62), at, 0.30, pan=0.05); m.add('drums', rim(), at, 0.12, pan=-0.2)
        for k in range(8):
            m.add('drums', hat(0.022 if k % 2 == 0 else 0.03, 6000, 10000), T(bar, k / 2) + rng.normal(0, 0.004), (0.17 if k % 2 == 0 else 0.11) * (1 + rng.normal(0, 0.1)), pan=0.35)
    tf = t0 + 16 * bt; tl.append((tf, 'Eb', 'M'))                         # 마침: 천천히 펼치는 내림 마 장조 9화음
    for j, nm in enumerate(['Eb3', 'Bb3', 'G4', 'Bb4', 'D5', 'F5']):
        at = tf + j * 0.06; m.add('keys', rhodes(hz(nm), 2.1 - j * 0.06, 0.6, at, 1.0), at, 0.17, pan=-0.35 + 0.14 * j)
    m.add('bass', subbass(hz('Eb2'), 1.9, 0.6), tf, 0.50); m.add('drums', kick2(105, 45, 0.035, 0.17, 0.06), tf, 0.40)
    m.add('lead', rhodes(hz('Eb5'), 2.0, 0.85, tf, 1.0), tf, 0.36, pan=0.08); m.add('lead', vibes(hz('Eb6'), 1.8), tf, 0.07, pan=0.3)
    for j, nm in enumerate(['G5', 'Bb5', 'Eb6']): m.add('fx', celesta(hz(nm)), tf + 0.42 + j * 0.16, 0.10, pan=-0.2 + 0.25 * j)
    accents(m, 'fx', tl, crown, ding, celesta, vibes, top=89, g_run=0.15, g_bell=0.30, bell_at=79)
    return m.render(rt60=1.1, rev=0.9, bright=6000.0, dtime=0.75 * bt, dfb=0.35, master=g_shelf(2600, 4.0))


def cand_E(crown, ding):
    """피치카토 발걸음 — 라 장조, 124 BPM. 통통 튀는 현 + 피아노 선율."""
    seed(105); bt = 60 / 124; t0 = 0.2 + bt; m = Mix2()
    T = lambda bar, e: t0 + (bar * 4 + e / 2) * bt                       # e: 8분음 칸(0~7)
    body = chain(g_bell(280, 3.5, 0.35), g_bell(480, 2.5, 0.3), g_lp(7000, 2))
    m.stem('bass', wet=0.10, fx=lambda y: fftfilt(y, g_bell(110, 2.5, 0.6)))
    m.stem('pizz', wet=0.30, fx=lambda y: fftfilt(y, body))
    m.stem('piano', wet=0.26, dly=0.05)
    m.stem('pad', wet=0.5)
    m.stem('fx', wet=0.5, dly=0.15)
    bars = [(('D', 'M'), ('D2', 'A2'), (['A3', 'D4', 'F#4'], ['A3', 'D4', 'F#4']), ['D3', 'A3', 'F#4']),
            (('B', 'm'), ('B2', 'F#2'), (['B3', 'D4', 'F#4'], ['B3', 'D4', 'F#4']), ['B2', 'F#3', 'D4']),
            (('G', 'M'), ('G2', 'D3'), (['B3', 'D4', 'G4'], ['B3', 'D4', 'G4']), ['G2', 'D3', 'B3']),
            (('A', 'M'), ('A2', 'E2'), (['A3', 'C#4', 'G4'], ['A3', 'C#4', 'G4']), ['A2', 'E3', 'C#4']),
            (('D', 'M'), ('F#2', 'G2'), (['A3', 'D4', 'F#4'], ['B3', 'D4', 'G4']), ['F#2', 'D3', 'A3']),
            (('A', 'M'), ('A2', 'E2'), (['G3', 'C#4', 'E4'], ['G3', 'C#4', 'E4']), ['A2', 'E3', 'G3'])]
    mel = [['D5', 'E5', 'F#5', None, 'A5', None, 'F#5', None], ['D5', 'E5', 'F#5', None, 'B5', None, 'F#5', None],
           ['G5', 'A5', 'B5', None, 'D6', None, 'B5', None], ['C#6', 'B5', 'A5', None, 'G5', None, 'E5', None],
           ['F#5', 'G5', 'A5', None, 'B5', None, 'D6', None], ['E6', 'D6', 'C#6', None, 'A5', None, 'C#6', None]]

    def pn(nm, d, v, at):
        m.add('piano', piano(hz(nm), d, v), at, 0.42, pan=0.05); m.add('piano', piano(hz(nm) / 2, d * 0.9, 0.5), at, 0.15, pan=-0.1)
    pn('A4', 0.2, 0.5, t0 - bt); pn('C#5', 0.2, 0.58, t0 - bt / 2)                                # 못갖춘마디 두 음
    tl = [(0.0, 'D', 'M')]
    for bar, ((rn, q), bs, chs, padn) in enumerate(bars):
        tl.append((T(bar, 0), rn, q))
        if bar == 4: tl.append((T(bar, 4), 'G', 'M'))
        for i, nm in enumerate(bs): m.add('bass', upbass(hz(nm), 1.2), T(bar, i * 4) + rng.normal(0, 0.003), 0.40 if i == 0 else 0.34)
        for i, ch in enumerate(chs):
            for j, nm in enumerate(ch): m.add('pizz', pizz(hz(nm), 0.7, 3, 0.8), T(bar, 2 + i * 4) + rng.normal(0, 0.003), 0.46, pan=-0.3 + 0.3 * j)
        m.add('pad', ens(tuple(hz(x) for x in padn), 4 * bt, 0.5, 0.8, 1800.0, 3, 8.0, 0.003, 1.3, bar), T(bar, 0), 0.06)
        for e, nm in enumerate(mel[bar]):
            if nm: pn(nm, 0.44 if e in (4, 6) else 0.20, 0.82 if e in (0, 4) else 0.70, T(bar, e) + rng.normal(0, 0.003))
    tf = T(6, 0); tl.append((tf, 'D', 'M'))                                  # 마침: 다 같이 '통' + 피아노 화음 + 반짝
    for j, nm in enumerate(['D2', 'A2']): m.add('bass', upbass(hz(nm), 1.6), tf, 0.42 - 0.12 * j)
    for j, nm in enumerate(['D3', 'A3', 'D4', 'F#4', 'A4', 'D5']): m.add('pizz', pizz(hz(nm), 1.0, 3, 0.9), tf, 0.40, pan=-0.4 + 0.16 * j)
    for j, nm in enumerate(['D3', 'A3', 'F#4', 'A4', 'D5', 'F#5', 'D6']): m.add('piano', piano(hz(nm), 2.0, 0.74), tf + j * 0.022, 0.26, pan=-0.3 + 0.1 * j)
    m.add('pad', ens(tuple(hz(x) for x in ['D3', 'A3', 'F#4', 'A4']), 1.4, 0.3, 1.0, 2000.0, 3, 8.0, 0.003, 1.3, 9), tf, 0.09)
    for j, nm in enumerate(['A5', 'D6', 'F#6', 'A6']): m.add('fx', celesta(hz(nm)), tf + 0.30 + j * 0.11, 0.10, pan=-0.3 + 0.2 * j)
    accents(m, 'fx', tl, crown, ding, harp, celesta, top=93, n=7, step=0.048, g_run=0.16, g_bell=0.34, bell_at=84)
    return m.render(rt60=1.7, rev=1.0, dtime=1.5 * bt, dfb=0.3)


def cand_F(crown, ding):
    """8비트 모험 — 가 장조, 140 BPM. 게임기 소리(펄스파 선율 + 삼각파 베이스 + 잡음 북)."""
    seed(106); bt = 60 / 140; t0 = 0.12 + 0.75 * bt; m = Mix2()
    T = lambda bar, e: t0 + (bar * 4 + e / 2) * bt                       # e: 8분음 칸
    m.stem('lead', wet=0.12, dly=0.22)
    m.stem('arp', wet=0.12)
    m.stem('bass', wet=0.02)
    m.stem('drums', wet=0.08)
    m.stem('fx', wet=0.2, dly=0.2)
    bars = [(('A', 'M'), ['A3', 'C#4', 'E4', 'A4'], 'A2'), (('F#', 'm'), ['F#3', 'A3', 'C#4', 'F#4'], 'F#2'), (('D', 'M'), ['A3', 'D4', 'F#4', 'A4'], 'D3'),
            (('E', 'M'), ['G#3', 'B3', 'E4', 'G#4'], 'E2'), (('A', 'M'), ['A3', 'C#4', 'E4', 'A4'], 'A2'), (('D', 'M'), ['A3', 'D4', 'F#4', 'A4'], 'D3'),
            (('E', 'M'), ['G#3', 'B3', 'D4', 'E4'], 'E2')]
    mel = [[(0, 'E5', 2), (2, 'C#5', 1), (3, 'E5', 1), (4, 'A5', 2), (6, 'G#5', 1), (7, 'F#5', 1)], [(0, 'E5', 3), (3, 'C#5', 1), (4, 'E5', 3)],
           [(0, 'F#5', 2), (2, 'D5', 1), (3, 'F#5', 1), (4, 'B5', 2), (6, 'A5', 1), (7, 'F#5', 1)], [(0, 'G#5', 3), (3, 'E5', 1), (4, 'G#5', 3)],
           [(0, 'A5', 2), (2, 'E5', 1), (3, 'A5', 1), (4, 'C#6', 2), (6, 'B5', 1), (7, 'A5', 1)], [(0, 'F#5', 2), (2, 'A5', 2), (4, 'G#5', 2), (6, 'B5', 2)],
           [(i * 0.5, nm, 0.5) for i, nm in enumerate(['E5', 'F#5', 'G#5', 'A5', 'B5', 'C#6', 'D6', 'E6'])] + [(4, 'D6', 1), (5, 'B5', 1), (6, 'G#5', 2)]]

    def boom(at, g):
        tk = tt(0.11); m.add('drums', np.sin(PI2 * np.cumsum(55 + 150 * np.exp(-tk / 0.022)) / SR) * np.exp(-tk / 0.05), at, g)
    for i, nm in enumerate(['A4', 'C#5', 'E5']):                                                  # 못갖춘마디: 또르르 올라오는 세 음
        m.add('lead', pulse(round(hz(nm), 3), 0.22 * bt, 0.25, 0.0, 0.72), t0 - (3 - i) * bt / 4, 0.16 + 0.05 * i, pan=0.05)
    tl = [(0.0, 'A', 'M')]
    for bar, ((rn, q), arp, bs) in enumerate(bars):
        tl.append((T(bar, 0), rn, q))
        if bar == 5: tl.append((T(bar, 4), 'E', 'M'))
        for e in range(8):
            a2, b2 = (['G#3', 'B3', 'E4', 'G#4'], 'E2') if (bar == 5 and e >= 4) else (arp, bs)
            for s in range(2):         # 16분음 화음 가루
                m.add('arp', pulse(round(hz(a2[(e * 2 + s) % 4]), 3), 0.42 * bt, 0.5, 0.0, 0.5), T(bar, e + s / 2), 0.12, pan=-0.45 if (e * 2 + s) % 2 == 0 else 0.45)
            m.add('bass', tri(round(hz(b2) * (2 if e % 2 else 1), 3), 0.44 * bt), T(bar, e), 0.23)
            if e % 4 == 0: boom(T(bar, e), 0.42)
            elif e % 4 == 2: m.add('drums', chipnoise(0.16, 7000, 0.05), T(bar, e), 0.20)
            if e % 2 == 1: m.add('drums', chipnoise(0.05, 14000, 0.012), T(bar, e), 0.07, pan=0.3)
        if bar == 6:                   # 마지막 마디: 작은북이 잘게 몰아친다
            for s in range(8): m.add('drums', chipnoise(0.08, 7000, 0.03), T(bar, 4 + s / 2), 0.07 + 0.016 * s)
        for e, nm, ln in mel[bar]:
            d = ln * bt / 2; m.add('lead', pulse(round(hz(nm), 3), d * 0.92, 0.25, 0.006 if ln >= 2 else 0.0, 0.72), T(bar, e), 0.36, pan=0.05)
    tf = T(7, 0); tl.append((tf, 'A', 'M'))                                  # 마침: 길게 뻗는 으뜸음 + 잦아드는 화음 가루
    fo = lambda y, d: y * np.clip(1 - (np.arange(len(y)) / SR - d) / max(0.05, len(y) / SR - d), 0, 1) ** 1.5
    m.add('lead', fo(pulse(round(hz('A5'), 3), 1.7, 0.25, 0.007, 0.8), 0.5), tf, 0.36, pan=0.05)
    m.add('lead', fo(pulse(round(hz('C#5'), 3), 1.7, 0.25, 0.0, 0.8), 0.5), tf, 0.15, pan=-0.2)
    m.add('bass', fo(tri(round(hz('A2'), 3), 1.7), 0.6), tf, 0.23)
    for i in range(22):
        nm = ['A4', 'C#5', 'E5', 'A5'][i % 4]; m.add('arp', pulse(round(hz(nm), 3), 0.06, 0.5, 0.0, 0.5), tf + i * bt / 8, 0.12 * (1 - i / 24) ** 1.3, pan=-0.45 if i % 2 == 0 else 0.45)
    boom(tf, 0.42); m.add('drums', chipnoise(0.9, 9000, 0.22), tf, 0.11)

    def blip_run(f):          # 왕관: 짧은 펄스 음이 또르르 올라간다
        return pulse(round(f, 3), 0.075, 0.125, 0.0, 0.6)

    def coin(f):              # 불빛: 동전 소리처럼 짧게 울리는 음
        return pulse(round(f, 3), 0.55, 0.5, 0.0, 0.5) * np.exp(-tt(0.55) / 0.16)
    accents(m, 'fx', tl, crown, ding, blip_run, coin, top=93, n=6, step=0.05, g_run=0.19, g_bell=0.24, bell_at=83)
    return m.render(rt60=0.7, rev=0.9, bright=6000.0, dtime=0.75 * bt, dfb=0.3, master=chain(g_lp(8500, 2), g_shelf(2600, -2.0)))


def cand_G(crown, ding):
    """햇살 기타 — 마 장조, 104 BPM. 어쿠스틱 기타 아르페지오 + 포근한 현 + 셰이커."""
    seed(107); e8 = 60 / 104 / 2; t0 = 0.2 + 2 * e8; m = Mix2()
    durs = [e8] * 32 + [e8 * (1 + 0.035 * s) for s in range(8)]             # 마지막 마디는 조금씩 느려진다
    starts = t0 + np.concatenate([[0], np.cumsum(durs)])
    T = lambda bar, e: float(starts[bar * 8 + e])
    gbody = chain(g_bell(105, 4, 0.3), g_bell(210, 3, 0.3), g_bell(420, 1.5, 0.4), g_lp(9500, 2), g_hp(70, 2))
    m.stem('gtr', wet=0.20, fx=lambda y: fftfilt(y, gbody))
    m.stem('lead', wet=0.30, dly=0.12, fx=lambda y: fftfilt(y, gbody))
    m.stem('flute', wet=0.45)
    m.stem('pad', wet=0.5)
    m.stem('perc', wet=0.15)
    m.stem('bass', wet=0.08)
    m.stem('fx', wet=0.5, dly=0.2)
    # (화음, 베이스1, 베이스2, 가운데 줄 i·m·a, 현 바탕) — 8분음 여덟 칸: 베이스·i·m·a·베이스2·i·m·i
    bars = [(('E', 'M'), 'E2', 'B2', ('G#3', 'B3', 'E4'), ['E3', 'B3', 'G#4']), (('C#', 'm'), 'C#3', 'G#2', ('G#3', 'B3', 'E4'), ['C#3', 'G#3', 'E4']),
            (('A', 'M'), 'A2', 'E3', ('A3', 'C#4', 'E4'), ['A2', 'E3', 'C#4']), (('E', 'M'), 'G#2', 'A2', ('G#3', 'B3', 'E4'), ['G#2', 'E3', 'B3']),
            (('B', 'M'), 'B2', 'B2', ('A3', 'B3', 'E4'), ['B2', 'F#3', 'A3'])]
    mel = [[(0, 'G#4', 4), (4, 'B4', 2), (6, 'E5', 2)], [(0, 'F#5', 4), (4, 'E5', 2), (6, 'C#5', 2)], [(0, 'E5', 4), (4, 'C#5', 2), (6, 'B4', 2)],
           [(0, 'G#4', 2), (2, 'B4', 2), (4, 'C#5', 2), (6, 'E5', 2)], [(0, 'E5', 4), (4, 'D#5', 4)]]
    for k, nm in enumerate(['B3', 'E4']): m.add('gtr', guitar(hz(nm), 1.6, 0.55), t0 - (2 - k) * e8, 0.22, pan=-0.2)     # 못갖춘마디 두 음
    tl = [(0.0, 'E', 'M')]
    for bar, ((rn, q), b1, b2, (si, sm, sa), padn) in enumerate(bars):
        tl.append((T(bar, 0), rn, q)); seqn = [b1, si, sm, sa, b2, si, sm, si]
        if bar == 3: seqn = ['G#2', 'G#3', 'B3', 'E4', 'A2', 'A3', 'C#4', 'E4']; tl.append((T(bar, 4), 'A', 'M'))
        if bar == 4: seqn = ['B2', 'A3', 'B3', 'E4', 'B2', 'A3', 'B3', 'D#4']
        for e in (0, 4): m.add('bass', upbass(hz(seqn[e]), 1.1), T(bar, e), 0.30 if e == 0 else 0.22)       # 기타 베이스 음을 콘트라베이스가 살짝 받친다
        for e, nm in enumerate(seqn):
            v = (0.85 if e in (0, 4) else 0.62) + rng.normal(0, 0.03)
            m.add('gtr', guitar(hz(nm), 2.2, v), T(bar, e) + rng.normal(0, 0.004), 0.26, pan=-0.22 + (0.0 if e in (0, 4) else 0.12))
            if not (bar == 4 and e >= 5): m.add('perc', shaker2(1.0 if e in (2, 6) else 0.55), T(bar, e) + rng.normal(0, 0.003), 0.15, pan=0.45)
        m.add('pad', ens(tuple(hz(x) for x in padn), (T(bar + 1, 0) - T(bar, 0)) if bar < 4 else 8 * e8 * 1.12, 0.6, 0.9, 1700.0, 3, 8.0, 0.003, 1.3, 20 + bar), T(bar, 0), 0.075)
        for e, nm, ln in mel[bar]:
            d = (T(bar, e + ln) if bar * 8 + e + ln <= 40 else T(4, 7) + e8 * 1.3) - T(bar, e)
            m.add('lead', guitar(hz(nm), 2.4, 0.9), T(bar, e) + rng.normal(0, 0.004), 0.42, pan=0.2)
            m.add('flute', softflute(hz(nm), d * 0.96), T(bar, e), 0.05, pan=0.1)
    tf = float(starts[40]); tl.append((tf, 'E', 'M'))                                   # 마침: 천천히 긋는 마 장조 화음 + 반짝
    for j, nm in enumerate(['E2', 'B2', 'E3', 'G#3', 'B3', 'E4']): m.add('gtr', guitar(hz(nm), 2.6, 0.8), tf + j * 0.042, 0.27, pan=-0.3 + 0.08 * j)
    m.add('bass', upbass(hz('E2'), 1.8), tf, 0.32)
    m.add('lead', guitar(hz('E5'), 2.6, 0.9), tf + 0.26, 0.42, pan=0.2); m.add('flute', softflute(hz('E5'), 1.4), tf + 0.26, 0.05, pan=0.1)
    m.add('pad', ens(tuple(hz(x) for x in ['E3', 'B3', 'G#4', 'B4']), 1.4, 0.4, 1.0, 1900.0, 3, 8.0, 0.003, 1.3, 29), tf, 0.09)
    for j, nm in enumerate(['G#5', 'B5', 'E6']): m.add('fx', celesta(hz(nm)), tf + 0.55 + j * 0.14, 0.09, pan=-0.2 + 0.25 * j)
    accents(m, 'fx', tl, crown, ding, harp, celesta, top=92, n=6, step=0.058, g_run=0.15, g_bell=0.30, bell_at=83)
    return m.render(rt60=1.6, rev=1.0, dtime=3 * e8, dfb=0.3)


def cand_H(crown, ding):
    """상쾌한 신스팝 — 내림 가 장조, 122 BPM. 둥근 킥 + 박수 + 숨 쉬는 패드 + 신스 벨 선율."""
    seed(108); bt = 60 / 122; t0 = 0.3; m = Mix2()
    T = lambda bar, e: t0 + (bar * 4 + e / 2) * bt                       # e: 8분음 칸
    tf = T(6, 0); kicks = [T(bar, e) for bar in range(6) for e in (0, 2, 4, 6)] + [tf]
    dk = duck_env(kicks, 0.5, 0.14); dk2 = duck_env(kicks, 0.3, 0.10)
    m.stem('pad', wet=0.35, fx=lambda y: y * dk)
    m.stem('stab', wet=0.25, dly=0.12, fx=lambda y: y * dk2)
    m.stem('bass', wet=0.02, fx=lambda y: fftfilt(y, g_lp(1400, 2)) * dk2)
    m.stem('lead', wet=0.30, dly=0.28)
    m.stem('drums', wet=0.10)
    m.stem('fx', wet=0.45, dly=0.25)
    # (화음 이름, 베이스, 패드 화음) — 반 마디 단위
    halves = [(('Ab', 'M'), 'Ab2', ['Ab3', 'C4', 'Eb4'])] * 2 + [(('Eb', 'M'), 'G2', ['G3', 'Bb3', 'Eb4'])] * 2 + [(('F', 'm'), 'F2', ['Ab3', 'C4', 'Eb4'])] * 2 + \
             [(('Db', 'M'), 'Db3', ['Ab3', 'Db4', 'F4'])] * 2 + [(('Ab', 'M'), 'C3', ['Ab3', 'C4', 'Eb4']), (('Db', 'M'), 'Db3', ['Ab3', 'Db4', 'F4'])] + \
             [(('Eb', 'M'), 'Eb3', ['Ab3', 'Bb3', 'Eb4']), (('Eb', 'M'), 'Eb3', ['G3', 'Bb3', 'Eb4'])]
    mel = [[(0, 'C5', 3), (3, 'Eb5', 3), (6, 'Ab5', 2)], [(0, 'G5', 3), (3, 'Eb5', 3), (6, 'Bb4', 2)], [(0, 'C5', 3), (3, 'Eb5', 3), (6, 'Ab5', 2)],
           [(0, 'Bb5', 3), (3, 'Ab5', 3), (6, 'F5', 2)], [(0, 'C6', 3), (3, 'Ab5', 3), (6, 'F5', 2)], [(0, 'Eb5', 3), (3, 'F5', 3), (6, 'G5', 2)]]
    tl = []
    m.add('fx', riser(0.32), 0.0, 0.05)
    for h, ((rn, q), bs, ch) in enumerate(halves):
        bar, e0 = h // 2, (h % 2) * 4; tl.append((T(bar, e0), rn, q))
        m.add('pad', ens(tuple(hz(x) for x in ch), 2 * bt * 0.98, 0.04, 0.2, 4800.0, 4, 13.0, 0.0, 1.0, 40 + h % 4), T(bar, e0), 0.26)
        for e in range(4):
            m.add('bass', sawpluck(hz(bs), 0.42 * bt, 1500.0, 350.0, 0.08, 0.5, 0.0), T(bar, e0 + e), 0.25)
            m.add('bass', subbass(hz(bs), 0.42 * bt, 0.2), T(bar, e0 + e), 0.24)
    for bar in range(6):
        for e in (0, 3, 6):          # 3+3+2 화음 찌르기 — 선율과 같은 리듬
            ch = halves[bar * 2 + (1 if e >= 4 else 0)][2]
            for j, nm in enumerate(ch): m.add('stab', sawpluck(hz(nm) * 2, 0.5 * bt, 6000.0, 1100.0, 0.10, 0.25, 6.0), T(bar, e), 0.28, pan=-0.5 + 0.5 * j)
        for e, nm, ln in mel[bar]:
            at = T(bar, e); m.add('lead', bellpluck(hz(nm), 1.6), at, 0.42, pan=0.06)
            m.add('lead', sawpluck(hz(nm), ln * bt / 2 * 0.9, 6500.0, 2200.0, 0.12, 0.5, 5.0), at, 0.26, pan=-0.06)
        for e in range(8):
            if e % 2 == 0: m.add('drums', kick2(120, 48, 0.03, 0.16, 0.07), T(bar, e), 0.56)
            else: m.add('drums', hat(0.035, 6500, 11000), T(bar, e), 0.15, pan=0.3)
            if e in (2, 6): m.add('drums', clap(), T(bar, e), 0.30, pan=-0.05)
            m.add('drums', hat(0.012, 7500, 11500), T(bar, e + 0.5), 0.06, pan=-0.3)
        if bar == 5:                 # 마지막 마디: 몰아가는 작은북 + 올라가는 바람 소리
            for s in range(8): m.add('drums', snare2(210, 0.04, 0.07, 1500, 7000, 0.75), T(bar, 4 + s / 2), 0.08 + 0.018 * s)
            m.add('fx', riser(2 * bt), T(bar, 4), 0.10)
    tl.append((tf, 'Ab', 'M'))                                               # 마침: 내림 가 장조 9화음이 활짝 + 위로 흩어지는 벨
    m.add('pad', ens(tuple(hz(x) for x in ['Ab3', 'Bb3', 'C4', 'Eb4', 'Ab4']), 1.5, 0.02, 1.2, 3600.0, 4, 13.0, 0.0, 1.0, 49), tf, 0.26)
    m.add('bass', subbass(hz('Ab2'), 1.6, 0.4), tf, 0.36); m.add('bass', sawpluck(hz('Ab2'), 1.2, 1500.0, 300.0, 0.15, 0.8, 0.0), tf, 0.25)
    m.add('drums', kick2(120, 48, 0.03, 0.2, 0.07), tf, 0.56); m.add('drums', crash(2.0), tf, 0.07)
    m.add('lead', bellpluck(hz('Ab5'), 1.8), tf, 0.42, pan=0.06); m.add('lead', sawpluck(hz('Ab5'), 1.2, 6500.0, 2200.0, 0.12, 0.6, 5.0), tf, 0.26, pan=-0.06)
    for j, nm in enumerate(['C6', 'Eb6', 'Ab6', 'Eb6', 'C6', 'Ab6']): m.add('fx', bellpluck(hz(nm), 1.6), tf + bt / 2 + j * bt / 4, 0.09 * (1 - j / 9), pan=-0.4 + 0.16 * j)
    accents(m, 'fx', tl, crown, ding, lambda f: bellpluck(f, 1.6), lambda f: layer(bellpluck(f, 2.0), 0.5 * celesta(f * 2, 2.0)), top=92, n=6, step=0.055, g_run=0.17, g_bell=0.26, bell_at=82)
    return m.render(rt60=1.5, rev=0.9, dtime=0.75 * bt, dfb=0.38, master=g_shelf(3000, 2.5))


def cand_I(crown, ding):
    """관악대 행진 — 내림 나 장조, 116 BPM. 트럼펫 선율 + 쿵짝 호른·튜바 + 작은북 + 글로켄슈필."""
    seed(109); bt = 60 / 116; t0 = 0.42; m = Mix2()
    T = lambda bar, e: t0 + (bar * 4 + e / 2) * bt                       # e: 8분음 칸
    m.stem('tpt', wet=0.30)
    m.stem('horns', wet=0.32)
    m.stem('tuba', wet=0.12, fx=lambda y: fftfilt(y, g_lp(1800, 2)))
    m.stem('glock', wet=0.4)
    m.stem('drums', wet=0.22)
    m.stem('fx', wet=0.5, dly=0.1)
    bars = [(('Bb', 'M'), ('Bb2', 'F3'), (['D4', 'F4', 'Bb4'], ['D4', 'F4', 'Bb4'])), (('Eb', 'M'), ('Eb3', 'Bb2'), (['Eb4', 'G4', 'Bb4'], ['Eb4', 'G4', 'Bb4'])),
            (('Bb', 'M'), ('F3', 'Bb2'), (['D4', 'F4', 'Bb4'], ['D4', 'F4', 'Bb4'])), (('F', 'M'), ('F3', 'C3'), (['Eb4', 'F4', 'A4'], ['Eb4', 'F4', 'A4'])),
            (('Eb', 'M'), ('Eb3', 'F3'), (['Eb4', 'G4', 'Bb4'], ['Eb4', 'F4', 'A4']))]
    mel = [[(0, 'D5', 2), (2, 'D5', 1), (3, 'Eb5', 1), (4, 'F5', 2), (6, 'Bb5', 2)], [(0, 'G5', 2), (2, 'G5', 1), (3, 'F5', 1), (4, 'Eb5', 2), (6, 'G5', 2)],
           [(0, 'F5', 2), (2, 'F5', 1), (3, 'G5', 1), (4, 'F5', 2), (6, 'D5', 2)], [(0, 'C5', 2), (2, 'Eb5', 1), (3, 'D5', 1), (4, 'C5', 3.4)],
           [(0, 'G5', 2), (2, 'Bb5', 2), (4, 'A5', 2), (6, 'C6', 2)]]

    def tpt(nm, d, v=0.85):
        f = hz(nm); return 0.6 * brass(f, d, v, 0.0, 7000.0, 0) + 0.5 * brass(f, d, v * 0.9, 0.15, 7000.0, 1)

    def drum(at, v, acc=False):
        m.add('drums', snare2(205, 0.04, 0.085, 1400, 8000, 0.72), at + rng.normal(0, 0.002), (0.26 if acc else 0.15) * v, pan=-0.05)
    for i in range(7): drum(0.02 + i * 0.055, 0.25 + 0.11 * i)                 # 못갖춘마디: 작은북이 살며시 굴러 들어온다
    tl = [(0.0, 'Bb', 'M')]
    for bar, ((rn, q), bs, chs) in enumerate(bars):
        tl.append((T(bar, 0), rn, q))
        if bar == 4: tl.append((T(bar, 4), 'F', 'M'))
        for i, nm in enumerate(bs):
            m.add('tuba', brass(hz(nm), 0.85 * bt, 0.75, 1.0, 2400.0, 2), T(bar, i * 4), 0.40)
            m.add('drums', kick2(82, 48, 0.05, 0.22, 0.12, 0.7), T(bar, i * 4), 0.30)
        for i, ch in enumerate(chs):
            for j, nm in enumerate(ch): m.add('horns', brass(hz(nm), 0.45 * bt, 0.6, 0.75, 5000.0, 3 + j), T(bar, 2 + i * 4), 0.16, pan=-0.45 + 0.3 * j)
        for e, nm, ln in mel[bar]:
            d = ln * bt / 2; m.add('tpt', tpt(nm, d * (0.9 if ln >= 2 else 0.8)), T(bar, e), 0.36, pan=0.08)
            m.add('glock', glock(hz(nm) * 2, 2.0), T(bar, e), 0.055, pan=-0.3)
        for s, acc in ((0, True), (4, False), (6, False), (8, True), (12, False), (13, False), (14, False), (15, False)):      # 쿵, 따닥, 쿵, 따라라락
            drum(T(bar, s / 2), 1.0 if s < 12 else 0.6 + 0.12 * (s - 12), acc)
    # 마침 마디: '빰, 빰, 빠암—'
    b6 = T(5, 0); tf = T(5, 4); tl += [(b6, 'Bb', 'M'), (T(5, 2), 'F', 'M'), (tf, 'Bb', 'M')]
    for at, top, ch, bs, d in ((b6, 'Bb5', ['D4', 'F4', 'Bb4'], 'Bb2', 0.5 * bt), (T(5, 2), 'A5', ['Eb4', 'F4', 'A4'], 'F3', 0.5 * bt), (tf, 'Bb5', ['D4', 'F4', 'Bb4', 'D5'], 'Bb2', 1.75)):
        m.add('tpt', tpt(top, d, 0.9), at, 0.36, pan=0.08); m.add('glock', glock(hz(top) * 2, 2.4), at, 0.06, pan=-0.3)
        for j, nm in enumerate(ch): m.add('horns', brass(hz(nm), d, 0.7, 0.6, 5000.0, 3 + j), at, 0.17, pan=-0.45 + 0.25 * j)
        m.add('tuba', brass(hz(bs), d, 0.8, 1.0, 2400.0, 2), at, 0.40); m.add('drums', kick2(82, 48, 0.05, 0.22, 0.12, 0.7), at, 0.34)
        drum(at, 1.0, True)
    m.add('tpt', tpt('F5', 1.75, 0.8), tf, 0.20, pan=-0.15); m.add('drums', crash(2.2), tf, 0.065)
    for i in range(14): drum(tf + 0.12 + i * 0.05, 0.55 * (1 - i / 16))             # 끝음 아래로 잦아드는 작은북
    accents(m, 'fx', tl, crown, ding, lambda f: glock(f, 2.0), lambda f: layer(glock(f, 2.6), 0.6 * celesta(f, 2.2)), top=94, n=6, step=0.05, g_run=0.10, g_bell=0.15, bell_at=86)
    return m.render(rt60=1.8, rev=1.0)


CANDS = {'D': ('로파이 건반', cand_D), 'E': ('피치카토 발걸음', cand_E), 'F': ('8비트 모험', cand_F),
         'G': ('햇살 기타', cand_G), 'H': ('상쾌한 신스팝', cand_H), 'I': ('관악대 행진', cand_I)}


def write_wav(y, outp):
    pcm = (np.clip(y, -1, 1) * 32767).astype('<i2')
    with wave.open(outp, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    which, crown, ding, outp = a[0], float(a[1]), float(a[2]), a[3]
    if which == 'all':
        os.makedirs(outp, exist_ok=True)
        for k, (name, fn) in CANDS.items():
            p = os.path.join(outp, f'cand_{k}.wav'); write_wav(fn(crown, ding), p); print(p, name)
    else:
        if '--report' in sys.argv:      # 줄기별 음량을 보려고 Mix2.render를 살짝 감싼다
            _r = Mix2.render

            def _wrap(self, *aa, **kw):
                y = _r(self, *aa, **kw); self.report(); return y
            Mix2.render = _wrap
        write_wav(CANDS[which][1](crown, ding), outp); print(outp, CANDS[which][0])
