"""Synthesises the 120 s soundtrack for the DiscordPromo composition.

120 BPM, 4/4 -> one bar = 2 s = 60 video frames, so every scene cut lands on a bar line.
Pure numpy (no samples): kick, clap, hats, bass, supersaw pads, plucked arp, risers,
whooshes and impacts. Writes public/discord-promo-music.wav (44.1 kHz, 16-bit stereo) and, when ffmpeg is
available, public/discord-promo-music.mp3 (320 kbps) which the composition uses.
"""
import shutil
import subprocess
import wave
import numpy as np

SR = 44100
BPM = 120
BEAT = 60 / BPM
BAR = BEAT * 4
DUR = 120.0
N = int(SR * DUR)
rng = np.random.default_rng(7)

L = np.zeros(N)
R = np.zeros(N)


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def place(sig, t, gain=1.0, pan=0.0):
    i = int(round(t * SR))
    if i >= N:
        return
    if sig.ndim == 1:
        sl, sr_ = sig, sig
    else:
        sl, sr_ = sig[0], sig[1]
    n = min(len(sl), N - i)
    lg = gain * np.cos((pan + 1) * np.pi / 4) * np.sqrt(2)
    rg = gain * np.sin((pan + 1) * np.pi / 4) * np.sqrt(2)
    L[i:i + n] += sl[:n] * lg
    R[i:i + n] += sr_[:n] * rg


def fft_filter(x, lo=None, hi=None):
    X = np.fft.rfft(x)
    fr = np.fft.rfftfreq(len(x), 1 / SR)
    m = np.ones_like(fr)
    if lo:
        m *= 1 / (1 + (lo / np.maximum(fr, 1)) ** 4)
    if hi:
        m *= 1 / (1 + (fr / hi) ** 4)
    return np.fft.irfft(X * m, len(x))


def t_(d):
    return np.arange(int(d * SR)) / SR


# ---------------------------------------------------------------- drums
def kick():
    t = t_(0.45)
    f = 45 + 110 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-t * 7.5)
    s[:200] += np.linspace(0.6, 0, 200) * rng.uniform(-1, 1, 200)
    return np.tanh(s * 1.6)


def clap():
    t = t_(0.3)
    n = fft_filter(rng.uniform(-1, 1, len(t)), 900, 4500)
    env = np.zeros_like(t)
    for d in (0, 0.011, 0.022):
        env += (t >= d) * np.exp(-np.maximum(t - d, 0) * (60 if d < 0.02 else 14))
    return n * env * 0.9


def hat(open_=False):
    t = t_(0.25 if open_ else 0.06)
    n = fft_filter(rng.uniform(-1, 1, len(t)), 7500, None)
    return n * np.exp(-t * (14 if open_ else 70))


def snare():
    t = t_(0.22)
    n = fft_filter(rng.uniform(-1, 1, len(t)), 1200, 8000) * np.exp(-t * 22)
    b = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30)
    return n * 0.8 + b * 0.5


K, CL, HC, HO, SN = kick(), clap(), hat(), hat(True), snare()

# ---------------------------------------------------------------- harmony
# vi - IV - I - V in F major : Dm  Bbmaj7  F  C
CHORDS = [
    ([57, 62, 65, 69], 38),
    ([58, 62, 65, 69], 34),
    ([60, 65, 69, 72], 41),
    ([60, 64, 67, 72], 36),
]


def saw(freq, dur, cutoff=2600, detune_cents=(0,), phase_seed=0):
    t = t_(dur)
    out = np.zeros_like(t)
    for k, dc in enumerate(detune_cents):
        f0 = freq * 2 ** (dc / 1200)
        ph0 = (phase_seed * 0.37 + k * 0.21) * 2 * np.pi
        h = 1
        while f0 * h < cutoff:
            out += np.sin(2 * np.pi * f0 * h * t + ph0 * h) / h * (1 - (f0 * h / cutoff)) ** 1.5
            h += 1
    return out / max(1, len(detune_cents))


pad_cache = {}


def pad_bar(ci, side):
    key = (ci, side)
    if key not in pad_cache:
        notes, _ = CHORDS[ci]
        det = (-14, 0, 13) if side == 0 else (-9, 5, 17)
        s = sum(saw(midi(m), BAR + 0.6, 2400, det, phase_seed=m + side) for m in notes)
        t = t_(BAR + 0.6)
        env = np.minimum(1, t / 0.25) * np.where(t > BAR, np.exp(-(t - BAR) * 8), 1)
        pad_cache[key] = s * env * 0.16
    return pad_cache[key]


def bass_note(m, dur):
    t = t_(dur)
    s = saw(midi(m), dur, 900, (0, 7)) + 0.6 * np.sin(2 * np.pi * midi(m) * t)
    env = np.minimum(1, t / 0.005) * np.exp(-t * 5)
    return s * env * 0.55


pluck_cache = {}


def pluck(m):
    if m not in pluck_cache:
        t = t_(0.5)
        f = midi(m)
        s = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(4 * np.pi * f * t) + 0.25 * np.sin(6 * np.pi * f * t)
             + 0.12 * np.sin(8 * np.pi * f * t))
        pluck_cache[m] = s * np.exp(-t * 11) * 0.16
    return pluck_cache[m]


# ---------------------------------------------------------------- fx
def riser(dur):
    t = t_(dur)
    n = rng.uniform(-1, 1, len(t))
    out = np.zeros_like(t)
    seg = 4096
    for i in range(0, len(t), seg):
        p = i / len(t)
        lo = 300 + 6000 * p ** 2
        chunk = n[i:i + seg]
        out[i:i + seg] = fft_filter(chunk, lo, lo * 2.5)
    f = 200 + 1400 * (t / dur) ** 2
    sweep = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.25
    return (out * 1.2 + sweep) * (t / dur) ** 2


def whoosh(dur=0.7):
    t = t_(dur)
    n = rng.uniform(-1, 1, len(t))
    out = np.zeros_like(t)
    seg = 2048
    for i in range(0, len(t), seg):
        p = i / len(t)
        c = 500 + 5000 * np.sin(np.pi * p) ** 2
        out[i:i + seg] = fft_filter(n[i:i + seg], c * 0.5, c * 1.6)
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2 * (t / dur)
    return out * env * 1.4


def impact(big=True):
    t = t_(2.5 if big else 1.0)
    f = 38 + 70 * np.exp(-t * 9)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (2.2 if big else 5))
    crash = fft_filter(rng.uniform(-1, 1, len(t)), 2500, 12000) * np.exp(-t * (1.6 if big else 6)) * 0.35
    return np.tanh((boom * 1.4 + crash) * 1.2)


def thump():
    t = t_(0.5)
    f = 50 + 140 * np.exp(-t * 25)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6)
    n = fft_filter(rng.uniform(-1, 1, len(t)), 200, 3000) * np.exp(-t * 30) * 0.5
    return np.tanh((s + n) * 1.5)


# ---------------------------------------------------------------- arrangement
NBARS = int(DUR / BAR)
duck = np.ones(N)


def add_kick(t):
    place(K, t, 0.95)
    i = int(t * SR)
    tt = t_(BEAT)
    n = min(len(tt), N - i)
    duck[i:i + n] = np.minimum(duck[i:i + n], 1 - 0.65 * np.exp(-tt[:n] * 9))


def section(b):
    if b < 4:
        return 'intro'
    if b < 30:
        return 'A'
    if b < 34:
        return 'break'
    if b < 57:
        return 'B'
    return 'outro'


pad_bus_L = np.zeros(N)
pad_bus_R = np.zeros(N)


def place_pad(sig_l, sig_r, t, g):
    i = int(t * SR)
    n = min(len(sig_l), N - i)
    pad_bus_L[i:i + n] += sig_l[:n] * g
    pad_bus_R[i:i + n] += sig_r[:n] * g


for b in range(NBARS):
    t0 = b * BAR
    sec = section(b)
    ci = b % 4
    notes, root = CHORDS[ci]
    # pads everywhere (quieter in grooves)
    pg = {'intro': 0.9 * min(1, (b + 1) / 2), 'A': 0.75, 'break': 1.0, 'B': 0.8, 'outro': 1.0}[sec]
    place_pad(pad_bar(ci, 0), pad_bar(ci, 1), t0, pg)
    if sec == 'outro' and b == NBARS - 1:
        pass
    # drums
    if sec in ('A', 'B') or (sec == 'outro' and b == 57 and False):
        for q in range(4):
            add_kick(t0 + q * BEAT)
        place(CL, t0 + BEAT, 0.55)
        place(CL, t0 + 3 * BEAT, 0.55)
        for e in range(8):
            place(HC, t0 + e * BEAT / 2 + BEAT / 2 * 0, 0.22 if e % 2 else 0.12, pan=0.25)
            if e % 2 == 1:
                place(HO if sec == 'B' else HC, t0 + e * BEAT / 2, 0.16 if sec == 'B' else 0.2, pan=-0.2)
        if sec == 'B':
            for s16 in range(16):
                if s16 % 4 == 3:
                    place(HC, t0 + s16 * BEAT / 4, 0.1, pan=0.4)
        # bass: off-beat 8ths + root on downbeat
        for e in range(8):
            m = root + (12 if e in (3, 7) else 0)
            place(bass_note(m, BEAT / 2), t0 + e * BEAT / 2, 0.42 if e % 2 else 0.3)
    if sec == 'break':
        if b >= 32:
            for e in range(8):
                place(HC, t0 + e * BEAT / 2, 0.12, pan=0.2)
        if b == 33:
            for s16 in range(16):
                place(SN, t0 + s16 * BEAT / 4, 0.1 + 0.45 * (s16 / 15) ** 2)
    # arp
    if sec in ('A', 'B', 'break') or (sec == 'intro' and b >= 2):
        arp = notes + [notes[1] + 12, notes[2] + 12]
        pattern = [0, 1, 2, 3, 4, 3, 2, 1, 0, 2, 4, 5, 4, 2, 1, 3]
        ag = {'intro': 0.6, 'A': 0.8, 'break': 1.0, 'B': 0.9}[sec]
        for s16 in range(16):
            m = arp[pattern[s16] % len(arp)] + 12
            tt = t0 + s16 * BEAT / 4
            pan = -0.35 if s16 % 2 else 0.35
            place(pluck(m), tt, ag, pan=pan)
            place(pluck(m), tt + BEAT * 0.75, ag * 0.35, pan=-pan)  # dotted-8th echo
        if sec == 'B' and b % 2 == 1:
            for s8 in range(8):
                place(pluck(notes[(s8 * 2) % 4] + 24), t0 + s8 * BEAT / 2, 0.35, pan=0.1)

# sidechain the pads
L += pad_bus_L * duck
R += pad_bus_R * duck

# intro word slams on beats 1,2,3 (0.5s, 1.0s, 1.5s) + logo hit at 4s, riser into the 8s drop
for tt in (0.5, 1.0, 1.5):
    place(thump(), tt, 0.8)
place(impact(True), 4.0, 0.9)
r = riser(3.5)
place(r, 8.0 - len(r) / SR, 0.35)
place(impact(True), 8.0, 0.75)
# breakdown riser + drop at 68s
r = riser(4.0)
place(r, 68.0 - len(r) / SR, 0.4)
place(impact(True), 68.0, 0.8)
# whooshes on every scene cut
CUTS = [18, 28, 40, 50, 60, 78, 88, 96, 104, 108, 114]
for c in CUTS:
    w = whoosh(0.8)
    place(w, c - 0.55, 0.38, pan=0.0)
for c in (18, 28, 40, 50, 60, 78, 88, 96, 108):
    place(impact(False), c, 0.35)
# stats counters: three quick hits
for i, tt in enumerate((104.2, 104.47, 104.73)):
    place(thump(), tt, 0.5)
# outro hit
place(impact(True), 114.0, 0.95)
r = riser(2.0)
place(r, 114.0 - len(r) / SR, 0.3)

# ---------------------------------------------------------------- master
# small algorithmic reverb: convolution with decaying noise IR
ir_t = t_(1.6)
ir = rng.uniform(-1, 1, len(ir_t)) * np.exp(-ir_t * 4.2)
ir = fft_filter(ir, 200, 7000)
ir /= np.sqrt(np.sum(ir ** 2))


def conv(x, h):
    n = len(x) + len(h) - 1
    nfft = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(h, nfft), nfft)[:len(x)]


wetL = conv(L, ir) * 0.18
wetR = conv(R, np.roll(ir, 37)) * 0.18
L = L + wetL
R = R + wetR

# fades
t = np.arange(N) / SR
fade = np.clip(t / 0.05, 0, 1) * np.clip((DUR - t) / 2.0, 0, 1)
L *= fade
R *= fade

peak = max(np.max(np.abs(L)), np.max(np.abs(R)))
L = np.tanh(L / peak * 1.3) / np.tanh(1.3) * 0.93
R = np.tanh(R / peak * 1.3) / np.tanh(1.3) * 0.93

st = np.stack([L, R], axis=1)
pcm = (st * 32767).astype('<i2')
with wave.open('public/discord-promo-music.wav', 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print('wrote public/discord-promo-music.wav', st.shape, 'peak', np.max(np.abs(st)))
if shutil.which('ffmpeg'):
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', 'public/discord-promo-music.wav',
                    '-c:a', 'libmp3lame', '-b:a', '320k', 'public/discord-promo-music.mp3'], check=True)
    print('wrote public/discord-promo-music.mp3')
