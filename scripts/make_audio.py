"""Synthesises the 60 s soundtrack for the DiscordPromo composition: a 120 BPM music bed plus a
SaaS-style SFX kit (whooshes, UI pops, clicks, keyboard ticks, message dings, toggles, voice-join
chimes, risers, impacts, shimmers). SFX timings come straight from src/discord/timeline.ts (read via
`node`), so sound and picture share one source of truth. Pure numpy, no samples.

Writes public/discord-promo-music.wav (gitignored) and public/discord-promo-music.mp3.
"""
import json
import shutil
import subprocess
import wave

import numpy as np

SR = 44100
BPM = 120
BEAT = 60 / BPM
BAR = BEAT * 4
FPS = 30
DUR = 60.0
N = int(SR * DUR)
rng = np.random.default_rng(11)


def load_sfx():
    js = "import('./src/discord/timeline.ts').then(m => console.log(JSON.stringify(m.SFX)))"
    out = subprocess.run(['node', '-e', js], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


# ---------------------------------------------------------------- helpers
class Bus:
    def __init__(self):
        self.L = np.zeros(N)
        self.R = np.zeros(N)

    def place(self, sig, t, gain=1.0, pan=0.0):
        i = int(round(t * SR))
        if i >= N or i < -len(sig):
            return
        s = sig
        if i < 0:
            s = s[-i:]
            i = 0
        n = min(len(s), N - i)
        pan = float(np.clip(pan, -1, 1))
        lg = gain * np.cos((pan + 1) * np.pi / 4) * np.sqrt(2)
        rg = gain * np.sin((pan + 1) * np.pi / 4) * np.sqrt(2)
        self.L[i:i + n] += s[:n] * lg
        self.R[i:i + n] += s[:n] * rg

    def place_st(self, l, r, t, gain=1.0):
        i = int(round(t * SR))
        n = min(len(l), N - i)
        self.L[i:i + n] += l[:n] * gain
        self.R[i:i + n] += r[:n] * gain


def T(d):
    return np.arange(int(d * SR)) / SR


def fft_filter(x, lo=None, hi=None):
    X = np.fft.rfft(x)
    fr = np.fft.rfftfreq(len(x), 1 / SR)
    m = np.ones_like(fr)
    if lo:
        m *= 1 / (1 + (lo / np.maximum(fr, 1)) ** 4)
    if hi:
        m *= 1 / (1 + (fr / hi) ** 4)
    return np.fft.irfft(X * m, len(x))


def sweep_noise(dur, f0, f1, width=1.8, seg=1024, curve=1.0):
    """noise through a band-pass whose centre glides f0 -> f1"""
    t = T(dur)
    n = rng.uniform(-1, 1, len(t))
    out = np.zeros_like(t)
    for i in range(0, len(t), seg):
        p = (i / max(1, len(t))) ** curve
        c = f0 * (f1 / f0) ** p
        out[i:i + seg] = fft_filter(n[i:i + seg], c / width, c * width)
    return out


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def bell(f, dur=0.8, decay=6.0, bright=0.5):
    t = T(dur)
    s = np.sin(2 * np.pi * f * t) + bright * 0.5 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 14) + 0.25 * np.sin(2 * np.pi * f * 2 * t)
    return s * np.exp(-t * decay) * np.minimum(1, t / 0.002)


# ---------------------------------------------------------------- SFX kit
def sfx_whoosh(dur=1.1):
    dur = max(0.5, dur)
    n = sweep_noise(dur, 350, 4200, 1.6, curve=1.4)
    t = T(dur)
    p = t / dur
    env = np.where(p < 0.78, (p / 0.78) ** 2.2, np.exp(-(p - 0.78) * 22))
    air = fft_filter(rng.uniform(-1, 1, len(t)), 5000, None) * 0.25
    return (n * 1.5 + air) * env


def sfx_whoosh_big(dur=2.2):
    t = T(dur)
    p = t / dur
    n = sweep_noise(dur, 2500, 180, 1.7, curve=0.8)
    sub = np.sin(2 * np.pi * np.cumsum(90 - 50 * p) / SR) * 0.5
    env = np.sin(np.pi * np.clip(p * 1.1, 0, 1)) ** 1.5
    return (n * 1.6 + sub) * env


def sfx_swish(dur=0.32):
    t = T(dur)
    n = sweep_noise(dur, 6000, 1500, 1.6)
    return n * np.sin(np.pi * t / dur) ** 2 * 1.3


def sfx_pop(pitch=1.0):
    t = T(0.14)
    f = 620 * pitch * (0.62 + 0.38 * np.exp(-t * 55))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 34)
    click = fft_filter(rng.uniform(-1, 1, len(t)), 2000, 9000) * np.exp(-t * 600) * 0.4
    return np.tanh((s + 0.3 * np.sin(2 * np.pi * np.cumsum(2 * f) / SR) * np.exp(-t * 60) + click) * 1.4)


def sfx_click():
    t = T(0.09)
    tick = fft_filter(rng.uniform(-1, 1, len(t)), 2500, 12000) * np.exp(-t * 900)
    body = np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 260) * 0.45
    thock = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 90) * 0.5
    return tick + body + thock


def sfx_key(pitch=1.0):
    t = T(0.05)
    n = fft_filter(rng.uniform(-1, 1, len(t)), 1800 * pitch, 7000 * pitch) * np.exp(-t * 420)
    body = np.sin(2 * np.pi * 420 * pitch * t) * np.exp(-t * 200) * 0.35
    return (n + body) * 0.9


def sfx_ding():
    a = bell(midi(88), 0.9, 6.5)  # E6
    b = bell(midi(95), 0.9, 6.0)  # B6
    out = np.zeros(len(a) + int(0.075 * SR))
    out[:len(a)] += a * 0.55
    out[int(0.075 * SR):] += b * 0.6
    return out


def sfx_send():
    t = T(0.22)
    n = sweep_noise(0.22, 900, 6000, 1.5)
    return n * np.sin(np.pi * t / 0.22) ** 2 * 1.1 + np.concatenate([np.zeros(int(0.15 * SR)), sfx_pop(1.4)])[:len(t)] * 0.5


def sfx_join(pitch=1.0):
    a = bell(midi(72) * pitch, 0.7, 7, 0.2)
    b = bell(midi(79) * pitch, 0.9, 6, 0.2)
    out = np.zeros(len(b) + int(0.09 * SR))
    out[:len(a)] += a * 0.5
    out[int(0.09 * SR):] += b * 0.55
    return out


def sfx_toggle(pitch=1.0):
    t = T(0.08)
    f = (900 + 700 * (t / 0.08)) * pitch
    chirp = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 40) * 0.5
    return chirp


def sfx_tick():
    t = T(0.05)
    return np.sin(2 * np.pi * 1250 * t) * np.exp(-t * 150) * 0.6 + fft_filter(rng.uniform(-1, 1, len(t)), 3000, 9000) * np.exp(-t * 700) * 0.25


def sfx_alert():
    out = np.zeros(int(0.32 * SR))
    for k, (f, d) in enumerate(((988, 0.0), (740, 0.13))):
        t = T(0.11)
        s = sum(np.sin(2 * np.pi * f * h * t) / h for h in (1, 3, 5)) * np.exp(-t * 18) * np.minimum(1, t / 0.004)
        i = int(d * SR)
        out[i:i + len(s)] += s * 0.45
    return out


def sfx_fill(dur=2.0):
    t = T(dur)
    p = t / dur
    f = 380 + 900 * (1 - (1 - p) ** 2)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * (0.5 + 0.5 * np.sin(2 * np.pi * 14 * t)) * 0.22
    env = np.minimum(1, t / 0.05) * np.minimum(1, (dur - t) / 0.12)
    return s * env


def sfx_shimmer():
    notes = [77, 81, 84, 86, 89, 93, 96]  # F major-ish sparkle
    out = np.zeros(int(1.6 * SR))
    for k, m in enumerate(notes):
        b = bell(midi(m), 1.0, 5.0, 0.6) * (0.35 - k * 0.02)
        i = int(k * 0.045 * SR)
        out[i:i + len(b)] += b
    t = np.arange(len(out)) / SR
    out += fft_filter(rng.uniform(-1, 1, len(out)), 7000, None) * np.exp(-t * 3) * np.minimum(1, t / 0.05) * 0.12
    return out


def sfx_thump(pitch=1.0):
    t = T(0.5)
    f = 52 * pitch + 150 * np.exp(-t * 26)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6)
    n = fft_filter(rng.uniform(-1, 1, len(t)), 300, 4000) * np.exp(-t * 35) * 0.5
    return np.tanh((s + n) * 1.6)


def sfx_impact():
    t = T(2.4)
    f = 36 + 80 * np.exp(-t * 9)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.4)
    crash = fft_filter(rng.uniform(-1, 1, len(t)), 2500, 13000) * np.exp(-t * 1.8) * 0.35
    snap = fft_filter(rng.uniform(-1, 1, len(t)), 800, 6000) * np.exp(-t * 40) * 0.6
    return np.tanh((boom * 1.5 + crash + snap) * 1.2)


def sfx_riser(dur=1.5):
    t = T(dur)
    p = t / dur
    n = sweep_noise(dur, 300, 7000, 1.5, curve=2.0)
    f = 180 + 1500 * p ** 2
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.2
    return (n * 1.2 + tone) * p ** 2.2


SFX_GAIN = {
    'whoosh': 0.72, 'whooshBig': 0.7, 'swish': 0.7, 'pop': 0.5, 'click': 0.55, 'key': 0.6, 'ding': 0.48,
    'send': 0.55, 'join': 0.45, 'toggle': 0.75, 'tick': 0.5, 'alert': 0.9, 'fill': 1.8, 'shimmer': 0.5,
    'thump': 0.85, 'impact': 0.85, 'riser': 0.5,
}
MUSIC_GAIN = 0.46


def render_sfx(ev):
    k = ev['type']
    p = ev.get('pitch', 1.0)
    d = ev.get('dur', 1.0)
    if k == 'whoosh':
        return sfx_whoosh(d + 0.15)
    if k == 'whooshBig':
        return sfx_whoosh_big(d)
    if k == 'swish':
        return sfx_swish()
    if k == 'pop':
        return sfx_pop(p)
    if k == 'click':
        return sfx_click()
    if k == 'key':
        return sfx_key(p)
    if k == 'ding':
        return sfx_ding()
    if k == 'send':
        return sfx_send()
    if k == 'join':
        return sfx_join(p)
    if k == 'toggle':
        return sfx_toggle(p)
    if k == 'tick':
        return sfx_tick()
    if k == 'alert':
        return sfx_alert()
    if k == 'fill':
        return sfx_fill(d)
    if k == 'shimmer':
        return sfx_shimmer()
    if k == 'thump':
        return sfx_thump(p)
    if k == 'impact':
        return sfx_impact()
    if k == 'riser':
        return sfx_riser(d)
    raise ValueError(k)


# ---------------------------------------------------------------- music bed
def kick():
    t = T(0.45)
    f = 45 + 110 * np.exp(-t * 28)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7.5)
    s[:200] += np.linspace(0.6, 0, 200) * rng.uniform(-1, 1, 200)
    return np.tanh(s * 1.6)


def clap():
    t = T(0.3)
    n = fft_filter(rng.uniform(-1, 1, len(t)), 900, 4500)
    env = sum((t >= d) * np.exp(-np.maximum(t - d, 0) * (60 if d < 0.02 else 14)) for d in (0, 0.011, 0.022))
    return n * env * 0.9


def hat(open_=False):
    t = T(0.25 if open_ else 0.06)
    return fft_filter(rng.uniform(-1, 1, len(t)), 7500, None) * np.exp(-t * (14 if open_ else 70))


def snare():
    t = T(0.22)
    return fft_filter(rng.uniform(-1, 1, len(t)), 1200, 8000) * np.exp(-t * 22) * 0.8 + np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30) * 0.5


CHORDS = [([57, 62, 65, 69], 38), ([58, 62, 65, 69], 34), ([60, 65, 69, 72], 41), ([60, 64, 67, 72], 36)]


def saw(freq, dur, cutoff=2600, det=(0,), seed=0):
    t = T(dur)
    out = np.zeros_like(t)
    for k, dc in enumerate(det):
        f0 = freq * 2 ** (dc / 1200)
        ph0 = (seed * 0.37 + k * 0.21) * 2 * np.pi
        h = 1
        while f0 * h < cutoff:
            out += np.sin(2 * np.pi * f0 * h * t + ph0 * h) / h * (1 - f0 * h / cutoff) ** 1.5
            h += 1
    return out / max(1, len(det))


_pad = {}


def pad_bar(ci, side, length=BAR):
    key = (ci, side, length)
    if key not in _pad:
        notes, _ = CHORDS[ci]
        det = (-14, 0, 13) if side == 0 else (-9, 5, 17)
        s = sum(saw(midi(m), length + 0.6, 2400, det, m + side) for m in notes)
        t = T(length + 0.6)
        env = np.minimum(1, t / 0.25) * np.where(t > length, np.exp(-(t - length) * 6), 1)
        _pad[key] = s * env * 0.16
    return _pad[key]


def bass_note(m, dur):
    t = T(dur)
    s = saw(midi(m), dur, 900, (0, 7)) + 0.6 * np.sin(2 * np.pi * midi(m) * t)
    return s * np.minimum(1, t / 0.005) * np.exp(-t * 5) * 0.55


_pl = {}


def pluck(m):
    if m not in _pl:
        t = T(0.5)
        f = midi(m)
        s = sum(a * np.sin(2 * np.pi * f * h * t) for h, a in ((1, 1), (2, 0.5), (3, 0.25), (4, 0.12)))
        _pl[m] = s * np.exp(-t * 11) * 0.16
    return _pl[m]


def section(b):
    if b < 3:
        return 'intro'
    if b < 23:
        return 'A'
    if b < 26:
        return 'break'
    if b < 29:
        return 'B'
    return 'end'


def build_music():
    mus = Bus()
    padL = np.zeros(N)
    padR = np.zeros(N)
    duck = np.ones(N)
    K, CL, HC, HO, SN = kick(), clap(), hat(), hat(True), snare()

    def add_kick(t):
        mus.place(K, t, 0.95)
        i = int(t * SR)
        tt = T(BEAT)
        n = min(len(tt), N - i)
        duck[i:i + n] = np.minimum(duck[i:i + n], 1 - 0.65 * np.exp(-tt[:n] * 9))

    nbars = int(DUR / BAR)
    for b in range(nbars):
        t0 = b * BAR
        sec = section(b)
        ci = b % 4
        notes, root = CHORDS[ci]
        if sec == 'end':
            p = pad_bar(0, 0, BAR * 0.95), pad_bar(0, 1, BAR * 0.95)
            i = int(t0 * SR)
            n = min(len(p[0]), N - i)
            padL[i:i + n] += p[0][:n] * 1.1
            padR[i:i + n] += p[1][:n] * 1.1
            continue
        pg = {'intro': 0.9 * min(1, (b + 1) / 2), 'A': 0.72, 'break': 1.0, 'B': 0.8}[sec]
        i = int(t0 * SR)
        pl, pr = pad_bar(ci, 0), pad_bar(ci, 1)
        n = min(len(pl), N - i)
        padL[i:i + n] += pl[:n] * pg
        padR[i:i + n] += pr[:n] * pg
        if sec in ('A', 'B'):
            for q in range(4):
                add_kick(t0 + q * BEAT)
            mus.place(CL, t0 + BEAT, 0.5)
            mus.place(CL, t0 + 3 * BEAT, 0.5)
            for e in range(8):
                mus.place(HC, t0 + e * BEAT / 2, 0.2 if e % 2 else 0.1, pan=0.25)
                if e % 2 and sec == 'B':
                    mus.place(HO, t0 + e * BEAT / 2, 0.14, pan=-0.2)
            for e in range(8):
                m = root + (12 if e in (3, 7) else 0)
                mus.place(bass_note(m, BEAT / 2), t0 + e * BEAT / 2, 0.4 if e % 2 else 0.28)
        if sec == 'break' and b == 25:
            for s16 in range(16):
                mus.place(SN, t0 + s16 * BEAT / 4, 0.08 + 0.4 * (s16 / 15) ** 2)
        if sec in ('A', 'B', 'break') or (sec == 'intro' and b >= 1):
            arp = notes + [notes[1] + 12, notes[2] + 12]
            pat = [0, 1, 2, 3, 4, 3, 2, 1, 0, 2, 4, 5, 4, 2, 1, 3]
            ag = {'intro': 0.55, 'A': 0.75, 'break': 0.95, 'B': 0.85}[sec]
            for s16 in range(16):
                m = arp[pat[s16] % len(arp)] + 12
                tt = t0 + s16 * BEAT / 4
                pan = -0.35 if s16 % 2 else 0.35
                mus.place(pluck(m), tt, ag, pan=pan)
                mus.place(pluck(m), tt + BEAT * 0.75, ag * 0.33, pan=-pan)
    mus.L += padL * duck
    mus.R += padR * duck
    return mus


# ---------------------------------------------------------------- mix
def conv(x, h):
    n = len(x) + len(h) - 1
    nfft = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(h, nfft), nfft)[:len(x)]


def main():
    events = load_sfx()
    mus = build_music()
    fx = Bus()
    for ev in events:
        sig = render_sfx(ev)
        t = ev['f'] / FPS
        g = SFX_GAIN[ev['type']] * ev.get('gain', 1.0)
        if ev['type'] in ('whoosh', 'whooshBig'):
            # whoosh is placed to peak on the arrival frame and pans across the stereo field
            dur = len(sig) / SR
            start = t
            pan = ev.get('pan', 0.0)
            ramp = np.linspace(-pan, pan, len(sig))
            l = sig * np.cos((ramp + 1) * np.pi / 4) * np.sqrt(2) * g
            r = sig * np.sin((ramp + 1) * np.pi / 4) * np.sqrt(2) * g
            fx.place_st(l, r, start)
            continue
        if ev['type'] == 'riser':
            fx.place(sig, t, g)
            continue
        fx.place(sig, t, g, ev.get('pan', 0.0))

    ir_t = T(1.4)
    ir = fft_filter(rng.uniform(-1, 1, len(ir_t)) * np.exp(-ir_t * 4.5), 200, 7000)
    ir /= np.sqrt(np.sum(ir ** 2))
    L = mus.L * MUSIC_GAIN + fx.L
    R = mus.R * MUSIC_GAIN + fx.R
    L = L + conv(mus.L * MUSIC_GAIN * 0.2 + fx.L * 0.12, ir)
    R = R + conv(mus.R * MUSIC_GAIN * 0.2 + fx.R * 0.12, np.roll(ir, 37))

    t = np.arange(N) / SR
    fade = np.clip(t / 0.03, 0, 1) * np.clip((DUR - t) / 1.2, 0, 1)
    L *= fade
    R *= fade
    peak = max(np.max(np.abs(L)), np.max(np.abs(R)))
    L = np.tanh(L / peak * 1.4) / np.tanh(1.4) * 0.94
    R = np.tanh(R / peak * 1.4) / np.tanh(1.4) * 0.94

    pcm = (np.stack([L, R], axis=1) * 32767).astype('<i2')
    with wave.open('public/discord-promo-music.wav', 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f'wrote public/discord-promo-music.wav  ({len(events)} sfx events)')
    if shutil.which('ffmpeg'):
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', 'public/discord-promo-music.wav', '-c:a', 'libmp3lame', '-b:a', '320k', 'public/discord-promo-music.mp3'], check=True)
        print('wrote public/discord-promo-music.mp3')


if __name__ == '__main__':
    main()
