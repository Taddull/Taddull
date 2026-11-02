"""Synthesises the 60 s soundtrack for the DiscordPromo composition: a 120 BPM music bed plus a soft,
tuned SaaS-style UI sound layer (bubble pops, marimba plucks, muffled clicks, bell dings and chimes,
toggles, a gentle alert, shimmers, a sub impact) and a camera "air" layer that follows the 3D camera's
speed. Cue times and camera speed come straight from src/discord/timeline.ts (read via `node`), and
every cue is snapped to the 16th-note grid and pitched to the current chord. Pure numpy, no samples.

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


def load_timeline():
    js = "import('./src/discord/timeline.ts').then(m => console.log(JSON.stringify({sfx: m.SFX, speed: m.CAM_SPEED})))"
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


# ---------------------------------------------------------------- SFX kit (soft + tuned)
# Every tonal effect is pitched to a chord tone of the bar it lands in, and every event is snapped to
# the 16th-note grid, so the UI sounds read as part of the music rather than on top of it.
def chord_tones(t, step=0, octave=1):
    notes, _ = CHORDS[int(t // BAR) % 4]
    tones = sorted(set(notes + [n + 12 for n in notes]))
    return tones[step % len(tones)] + 12 * octave + 12 * (step // len(tones))


def soft_env(n, attack=0.004, decay=8.0):
    t = np.arange(n) / SR
    return np.minimum(1, t / attack) * np.exp(-t * decay)


def tone(f, dur, decay, partials=((1, 1.0),), attack=0.004):
    t = T(dur)
    s = sum(a * np.sin(2 * np.pi * f * h * t) * np.exp(-t * decay * (1 + (h - 1) * 0.8)) for h, a in partials)
    return s * np.minimum(1, t / attack)


def sfx_pop(m):
    f0 = midi(m)
    t = T(0.18)
    f = f0 * (1 + 0.25 * np.exp(-t * 90))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR)
    return s * np.minimum(1, t / 0.003) * np.exp(-t * 24)


def sfx_pluck(m):  # marimba-ish
    return tone(midi(m), 0.45, 12, ((1, 1.0), (4, 0.18), (10, 0.03)))


def sfx_ding(m):
    a = tone(midi(m), 0.9, 6, ((1, 1.0), (3, 0.08)), 0.006)
    b = tone(midi(m + 7), 0.9, 6, ((1, 0.9), (3, 0.06)), 0.006)
    out = np.zeros(len(a) + int(0.06 * SR))
    out[:len(a)] += a
    out[int(0.06 * SR):] += b
    return out * 0.6


def sfx_chime(m):
    out = np.zeros(int(1.0 * SR))
    for k, iv in enumerate((0, 4, 7)):
        n = tone(midi(m + iv), 0.8, 7, ((1, 1.0), (2, 0.12)), 0.006) * (0.75 - k * 0.12)
        i = int(k * 0.045 * SR)
        out[i:i + len(n)] += n
    return out * 0.6


def sfx_click():
    t = T(0.06)
    n = fft_filter(rng.uniform(-1, 1, len(t)), 300, 2600) * soft_env(len(t), 0.001, 260) * 0.5
    body = np.sin(2 * np.pi * 160 * t) * soft_env(len(t), 0.001, 70) * 0.6
    tick = np.sin(2 * np.pi * 1100 * t) * soft_env(len(t), 0.001, 180) * 0.25
    return n + body + tick


def sfx_tick(m):
    return tone(midi(m + 12), 0.08, 45, ((1, 1.0),), 0.002) * 0.6


def sfx_toggle(m):
    t = T(0.14)
    f = midi(m) * (1 + 0.26 * np.minimum(1, t / 0.05))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(1, t / 0.004) * np.exp(-t * 20)
    c = np.concatenate([sfx_click() * 0.6, np.zeros(len(t))])[:len(t)]
    return s * 0.7 + c


def sfx_alert(m):
    out = np.zeros(int(0.5 * SR))
    for k, iv in enumerate((0, -3)):
        n = tone(midi(m + iv), 0.3, 10, ((1, 1.0), (3, 0.1)), 0.01)
        i = int(k * 0.125 * SR)
        out[i:i + len(n)] += n * 0.7
    return out


def sfx_send(m):
    d = 0.28
    t = T(d)
    n = fft_filter(sweep_noise(d, 400, 2400, 1.5), None, 4000)
    sw = n * np.sin(np.pi * t / d) ** 2 * 0.5
    p = sfx_pluck(m + 12) * 0.5
    out = np.zeros(len(t) + len(p))
    out[:len(t)] += sw
    out[int(0.2 * SR):int(0.2 * SR) + len(p)] += p
    return out


def sfx_shimmer(t0):
    out = np.zeros(int(1.8 * SR))
    for k in range(6):
        m = chord_tones(t0, k, 2)
        n = tone(midi(m), 1.2, 4.5, ((1, 1.0), (2, 0.06)), 0.01) * (0.5 - k * 0.05)
        i = int(k * 0.06 * SR)
        out[i:i + len(n)] += n
    tt = np.arange(len(out)) / SR
    air = fft_filter(rng.uniform(-1, 1, len(out)), 4000, 9000) * np.exp(-tt * 3) * np.minimum(1, tt / 0.1) * 0.05
    return out * 0.5 + air


def sfx_thump(step):
    t = T(0.45)
    f = 48 + 70 * np.exp(-t * 30)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(1, t / 0.003) * np.exp(-t * 7)
    return s


def sfx_impact():
    t = T(2.6)
    f = 34 + 50 * np.exp(-t * 8)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(1, t / 0.004) * np.exp(-t * 2.2)
    tail = fft_filter(rng.uniform(-1, 1, len(t)), 150, 2500) * np.exp(-t * 2.5) * np.minimum(1, t / 0.02) * 0.12
    return boom + tail


def sfx_riser(dur):
    t = T(dur)
    p = t / dur
    n = fft_filter(sweep_noise(dur, 250, 3000, 1.4, curve=2.0), None, 5000)
    f = 220 + 440 * p ** 2
    tn = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.15
    return (n * 0.8 + tn) * p ** 2.4


def sfx_swell(dur):
    t = T(dur)
    p = t / dur
    n = fft_filter(rng.uniform(-1, 1, len(t)), 600, 6000)
    return n * p ** 3 * 0.6


MUSIC_GAIN = 0.55

# per-type output level (linear). Deliberately low: these sit *under* the music, not on top of it.
SFX_GAIN = {
    'pop': 0.16, 'pluck': 0.11, 'ding': 0.15, 'chime': 0.14, 'click': 0.16, 'tick': 0.08, 'toggle': 0.12,
    'alert': 0.12, 'send': 0.13, 'shimmer': 0.16, 'thump': 0.30, 'impact': 0.36, 'riser': 0.12, 'swell': 0.10,
}


def render_sfx(ev, t0):
    k = ev['type']
    st = int(ev.get('step', 0))
    if k == 'pop':
        return sfx_pop(chord_tones(t0, st, 1))
    if k == 'pluck':
        return sfx_pluck(chord_tones(t0, st, 1))
    if k == 'ding':
        return sfx_ding(chord_tones(t0, st, 1))
    if k == 'chime':
        return sfx_chime(chord_tones(t0, st, 1) - 12)
    if k == 'click':
        return sfx_click()
    if k == 'tick':
        return sfx_tick(chord_tones(t0, 0, 1))
    if k == 'toggle':
        return sfx_toggle(chord_tones(t0, st, 1))
    if k == 'alert':
        return sfx_alert(chord_tones(t0, 2, 1))
    if k == 'send':
        return sfx_send(chord_tones(t0, 2, 1))
    if k == 'shimmer':
        return sfx_shimmer(t0)
    if k == 'thump':
        return sfx_thump(st)
    if k == 'impact':
        return sfx_impact()
    if k == 'riser':
        return sfx_riser(ev.get('dur', 1.0))
    if k == 'swell':
        return sfx_swell(ev.get('dur', 1.0))
    raise ValueError(k)


def camera_air(speed):
    """continuous air/whoosh whose level and brightness follow the camera's on-screen speed"""
    sp = np.asarray(speed, dtype=float)
    k = np.ones(7) / 7
    sp = np.convolve(sp, k, mode='same')
    sp = np.clip(sp / 60.0, 0, 1) ** 1.4
    env = np.interp(np.arange(N) / SR * FPS, np.arange(len(sp)), sp)
    base = rng.uniform(-1, 1, N)
    dark = fft_filter(base, 120, 700)
    bright = fft_filter(base, 500, 2600)
    return (dark * (1 - env) + bright * env) * env


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
    return fft_filter(rng.uniform(-1, 1, len(t)), 7000, 12000) * np.exp(-t * (14 if open_ else 70))


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


TARGET_LUFS = -16.0


def write_wav(L, R):
    pcm = (np.clip(np.stack([L, R], axis=1), -1, 1) * 32767).astype('<i2')
    with wave.open('public/discord-promo-music.wav', 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def main():
    tl = load_timeline()
    events = tl['sfx']
    mus = build_music()
    fx = Bus()
    sixteenth = BEAT / 4
    for ev in events:
        t = round((ev['f'] / FPS) / sixteenth) * sixteenth  # snap to the 16th-note grid
        sig = render_sfx(ev, t)
        fx.place(sig, t, SFX_GAIN[ev['type']] * ev.get('gain', 1.0), ev.get('pan', 0.0))
    air = camera_air(tl['speed'])
    fx.L += air * 0.07
    fx.R += np.roll(air, 400) * 0.07
    # tame anything harsh left in the effects bus
    fx.L = fft_filter(fx.L, 40, 9000)
    fx.R = fft_filter(fx.R, 40, 9000)

    ir_t = T(1.6)
    ir = fft_filter(rng.uniform(-1, 1, len(ir_t)) * np.exp(-ir_t * 4.0), 200, 6000)
    ir /= np.sqrt(np.sum(ir ** 2))
    L = mus.L * MUSIC_GAIN + fx.L
    R = mus.R * MUSIC_GAIN + fx.R
    L = L + conv(mus.L * MUSIC_GAIN * 0.18 + fx.L * 0.22, ir)
    R = R + conv(mus.R * MUSIC_GAIN * 0.18 + fx.R * 0.22, np.roll(ir, 37))

    t = np.arange(N) / SR
    fade = np.clip(t / 0.03, 0, 1) * np.clip((DUR - t) / 1.5, 0, 1)
    L *= fade
    R *= fade
    # gentle master: normalise to -1.5 dBFS peak through a soft knee
    peak = max(np.max(np.abs(L)), np.max(np.abs(R)))
    L = np.tanh(L / peak * 1.15) / np.tanh(1.15) * 0.84
    R = np.tanh(R / peak * 1.15) / np.tanh(1.15) * 0.84

    write_wav(L, R)
    if shutil.which('ffmpeg'):
        # loudness-normalise to a comfortable -16 LUFS (measured with ffmpeg's EBU R128 meter)
        meas = subprocess.run(['ffmpeg', '-hide_banner', '-i', 'public/discord-promo-music.wav', '-af', 'ebur128=framelog=quiet', '-f', 'null', '-'], capture_output=True, text=True).stderr
        lufs = float([ln for ln in meas.splitlines() if ln.strip().startswith('I:')][-1].split()[1])
        g = 10 ** ((TARGET_LUFS - lufs) / 20)
        write_wav(L * g, R * g)
        print(f'loudness {lufs:.1f} LUFS -> {TARGET_LUFS} LUFS')
    print(f'wrote public/discord-promo-music.wav  ({len(events)} sfx events)')
    if shutil.which('ffmpeg'):
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', 'public/discord-promo-music.wav', '-c:a', 'libmp3lame', '-b:a', '320k', 'public/discord-promo-music.mp3'], check=True)
        print('wrote public/discord-promo-music.mp3')


if __name__ == '__main__':
    main()
