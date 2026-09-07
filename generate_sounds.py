"""generate_sounds.py — Procedurally generate all missing game sound assets.
Run once: python3 generate_sounds.py
Requires only stdlib + struct (no external deps).
Produces mono 16-bit PCM WAV files in assets/sounds/ and assets/music/.
"""
import os, struct, math, array, random

SOUNDS_DIR = "assets/sounds"
MUSIC_DIR  = "assets/music"
RATE = 22050   # sample rate

os.makedirs(SOUNDS_DIR, exist_ok=True)
os.makedirs(MUSIC_DIR,  exist_ok=True)


def write_wav(path: str, samples: list[float], rate: int = RATE) -> None:
    """Write a list of floats [-1,1] as a 16-bit mono PCM WAV."""
    data = array.array("h", [max(-32767, min(32767, int(s * 32767))) for s in samples])
    raw  = data.tobytes()
    with open(path, "wb") as f:
        # RIFF header
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + len(raw)))
        f.write(b"WAVE")
        # fmt  chunk
        f.write(b"fmt ")
        f.write(struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16))
        # data chunk
        f.write(b"data")
        f.write(struct.pack("<I", len(raw)))
        f.write(raw)


def sine(freq, dur, rate=RATE, amp=0.6):
    n = int(dur * rate)
    return [amp * math.sin(2 * math.pi * freq * i / rate) for i in range(n)]

def noise(dur, rate=RATE, amp=0.4):
    n = int(dur * rate)
    return [amp * (random.random() * 2 - 1) for _ in range(n)]

def envelope(samples, attack=0.01, decay=0.05, sustain=0.7, release=0.1, rate=RATE):
    n = len(samples)
    out = []
    a, d, r = int(attack*rate), int(decay*rate), int(release*rate)
    s_start = a + d
    s_end   = max(s_start, n - r)
    for i, v in enumerate(samples):
        if i < a:
            g = i / max(a, 1)
        elif i < a + d:
            g = 1.0 - (1.0 - sustain) * (i - a) / max(d, 1)
        elif i < s_end:
            g = sustain
        else:
            g = sustain * max(0, (n - i) / max(r, 1))
        out.append(v * g)
    return out

def mix(*tracks):
    n = max(len(t) for t in tracks)
    out = []
    for i in range(n):
        v = sum(t[i] if i < len(t) else 0 for t in tracks)
        out.append(max(-1.0, min(1.0, v)))
    return out

def fade_out(samples, rate=RATE, fade=0.05):
    n    = len(samples)
    fade_n = int(fade * rate)
    out  = list(samples)
    for i in range(fade_n):
        out[n - fade_n + i] *= (1 - i / fade_n)
    return out


# ── LASER SHOOT ───────────────────────────────────────────────────────────────
def make_laser():
    dur = 0.18
    n   = int(dur * RATE)
    samples = []
    for i in range(n):
        t     = i / RATE
        freq  = 1200 * (1 - t / dur * 0.7)          # descending sweep
        freq2 = freq * 1.5
        v     = 0.5 * math.sin(2*math.pi*freq*t) + 0.2 * math.sin(2*math.pi*freq2*t)
        samples.append(v)
    return fade_out(envelope(samples, attack=0.005, decay=0.04, sustain=0.5, release=0.08))

write_wav(f"{SOUNDS_DIR}/laser.wav", make_laser())
print("  laser.wav")

# ── EXPLOSION ─────────────────────────────────────────────────────────────────
def make_explosion():
    dur = 0.55
    s1  = noise(dur, amp=0.9)
    s2  = sine(80, dur, amp=0.4)
    s3  = sine(40, dur, amp=0.3)
    samples = mix(s1, s2, s3)
    return fade_out(envelope(samples, attack=0.002, decay=0.15, sustain=0.3, release=0.25))

write_wav(f"{SOUNDS_DIR}/explosion.wav", make_explosion())
print("  explosion.wav")

# ── KA-CHING (purchase) ───────────────────────────────────────────────────────
def make_kaching():
    samples = []
    for freq, start, dur2 in [(1320, 0, 0.10), (1760, 0.06, 0.12), (2200, 0.13, 0.14)]:
        s = int(start * RATE)
        e = int((start + dur2) * RATE)
        for i in range(e - s):
            t = i / RATE
            a = math.exp(-t * 18)
            samples_at = s + i
            v = a * 0.55 * math.sin(2 * math.pi * freq * t)
            while len(samples) <= samples_at:
                samples.append(0.0)
            samples[samples_at] += v
    return fade_out(samples)

write_wav(f"{SOUNDS_DIR}/kaching.wav", make_kaching())
print("  kaching.wav")

# ── BOARDING THUD ─────────────────────────────────────────────────────────────
def make_boarding():
    s1 = noise(0.08, amp=0.7)
    s2 = sine(120, 0.12, amp=0.5)
    s3 = sine(60,  0.18, amp=0.4)
    samples = mix(s1 + [0]*int(0.04*RATE),
                  s2 + [0]*int(0.02*RATE),
                  s3)
    return fade_out(envelope(samples, attack=0.003, decay=0.06, sustain=0.4, release=0.10))

write_wav(f"{SOUNDS_DIR}/boarding.wav", make_boarding())
print("  boarding.wav")

# ── HIT / HULL IMPACT ─────────────────────────────────────────────────────────
def make_hull_hit():
    s1 = noise(0.12, amp=0.6)
    s2 = sine(200, 0.10, amp=0.3)
    return fade_out(envelope(mix(s1, s2), attack=0.002, decay=0.05, sustain=0.3, release=0.06))

write_wav(f"{SOUNDS_DIR}/hull_hit.wav", make_hull_hit())
print("  hull_hit.wav")

# ── SHIELD HIT ────────────────────────────────────────────────────────────────
def make_shield_hit():
    dur = 0.14
    n   = int(dur * RATE)
    samples = [0.5 * math.sin(2*math.pi*800*(1 - i/(n*0.8))*i/RATE)
               * math.exp(-i/RATE*20) for i in range(n)]
    return fade_out(envelope(samples, attack=0.002, decay=0.04, sustain=0.2, release=0.06))

write_wav(f"{SOUNDS_DIR}/shield_hit.wav", make_shield_hit())
print("  shield_hit.wav")

# ── UI CLICK ──────────────────────────────────────────────────────────────────
def make_click():
    s1 = noise(0.04, amp=0.4)
    s2 = sine(900, 0.04, amp=0.3)
    return fade_out(envelope(mix(s1, s2), attack=0.001, decay=0.02, sustain=0.1, release=0.01))

write_wav(f"{SOUNDS_DIR}/click.wav", make_click())
print("  click.wav")

# ── LOOT PICKUP ───────────────────────────────────────────────────────────────
def make_loot():
    s = []
    for freq in [660, 880, 1100]:
        s += sine(freq, 0.08, amp=0.35)
    return fade_out(envelope(s, attack=0.005, decay=0.04, sustain=0.4, release=0.06))

write_wav(f"{SOUNDS_DIR}/loot.wav", make_loot())
print("  loot.wav")

# ── LEVEL UP ──────────────────────────────────────────────────────────────────
def make_levelup():
    s = []
    for freq in [523, 659, 784, 1047]:
        s += sine(freq, 0.12, amp=0.4)
    return fade_out(envelope(s, attack=0.005, decay=0.06, sustain=0.5, release=0.10))

write_wav(f"{SOUNDS_DIR}/levelup.wav", make_levelup())
print("  levelup.wav")

# ── QUEST COMPLETE ────────────────────────────────────────────────────────────
def make_quest():
    return make_levelup()   # reuse

write_wav(f"{SOUNDS_DIR}/quest.wav", make_quest())
print("  quest.wav")

# ── MISSILE FIRE ──────────────────────────────────────────────────────────────
def make_missile():
    n = int(0.22 * RATE)
    s = [0.6 * noise(0.22)[i] * math.exp(-i/RATE*4) +
         0.3 * math.sin(2*math.pi*300*(1+i/n)*i/RATE) for i in range(n)]
    return fade_out(envelope(s, attack=0.01, decay=0.08, sustain=0.4, release=0.10))

write_wav(f"{SOUNDS_DIR}/missile.wav", make_missile())
print("  missile.wav")

print("\nAll sound assets generated.")
print("Note: music/ tracks (combat.ogg etc.) require actual audio files.")
print("The game silently skips missing music files.")
