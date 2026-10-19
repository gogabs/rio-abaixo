#!/usr/bin/env python3
"""Gera os sons provisórios da Canoa, só com a biblioteca padrão.

O vigia distingue os lados pelo timbre, porque tem um ouvido só: esquerda é
grave (madeira, borbulho grave, folhas graves), direita é agudo (sino,
borbulho agudo, folhas agudas) e bem na frente é um alarme duplo. Para
trocar um som, ponha um arquivo com o mesmo nome em sounds/ (WAV ou OGG) e
apague o provisório.

    python3 tools/gerar_sons.py
"""
import math
import os
import random
import struct
import wave

RATE = 22050
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sounds")
rng = random.Random(11)


def n(sec):
    return int(RATE * sec)


def tone(freq, sec, partials=((1, 1.0),), decay=0.2, attack=0.003):
    out = []
    for k in range(n(sec)):
        t = k / RATE
        env = min(1.0, t / attack) * math.exp(-t / decay)
        out.append(env * sum(a * math.sin(2 * math.pi * freq * m * t) for m, a in partials))
    return out


def noise(sec, smooth=0.5, decay=None, attack=0.01, release=0.05):
    """Ruído filtrado: smooth perto de 1 fica grave, perto de 0 fica agudo."""
    out, last = [], 0.0
    total = n(sec)
    for k in range(total):
        t = k / RATE
        last = smooth * last + (1 - smooth) * rng.uniform(-1, 1)
        env = min(1.0, t / attack, (total - k) / (RATE * release))
        if decay:
            env *= math.exp(-t / decay)
        out.append(last * env)
    return out


def highpass(samples, amount=0.9):
    out, prev_in, prev_out = [], 0.0, 0.0
    for s in samples:
        prev_out = amount * (prev_out + s - prev_in)
        prev_in = s
        out.append(prev_out)
    return out


def mix(*tracks):
    size = max(len(t) for t in tracks)
    return [sum(t[i] for t in tracks if i < len(t)) for i in range(size)]


def delay(samples, sec):
    return [0.0] * n(sec) + samples


def write(name, samples, peak=0.8):
    top = max(1e-9, max(abs(s) for s in samples))
    data = b"".join(struct.pack("<h", int(s / top * peak * 32767)) for s in samples)
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data)


def bubbles(base, count=4, spread=1.25):
    """Borbulhar: bolhas curtas que sobem de tom."""
    parts = []
    for i in range(count):
        f0 = base * spread ** (i % 3) * rng.uniform(0.95, 1.05)
        bubble, phase = [], 0.0
        for k in range(n(0.06)):
            t = k / RATE
            phase += 2 * math.pi * f0 * (1 + 6 * t) / RATE
            bubble.append(math.sin(phase) * math.exp(-t / 0.02))
        parts.append(delay(bubble, i * 0.07))
    return mix(*parts)


def loop_water(sec=2.0):
    """Água no casco, com as pontas casadas para o loop não estalar."""
    body = noise(sec + 0.2, smooth=0.93, attack=0.001, release=0.001)
    swell = [0.7 + 0.3 * math.sin(2 * math.pi * k / n(sec) * 2) for k in range(n(sec + 0.2))]
    body = [b * s for b, s in zip(body, swell)]
    fade = n(0.2)
    out = body[:n(sec)]
    for k in range(fade):
        w = k / fade
        out[k] = out[k] * w + body[n(sec) + k] * (1 - w)
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    # piloto
    write("remada_esq", mix(noise(0.35, smooth=0.75, attack=0.02, decay=0.12),
                            tone(180, 0.2, decay=0.05)), peak=0.7)
    write("remada_dir", mix(noise(0.35, smooth=0.6, attack=0.02, decay=0.12),
                            tone(240, 0.2, decay=0.05)), peak=0.7)
    write("agua", loop_water(), peak=0.5)
    write("raspa", noise(0.5, smooth=0.3, attack=0.02, release=0.2), peak=0.6)
    write("errou", noise(0.25, smooth=0.85, decay=0.08), peak=0.4)
    # os dois
    write("batida", mix(tone(70, 0.6, ((1, 1.0), (2.3, 0.5)), decay=0.15),
                        noise(0.3, smooth=0.8, decay=0.06)), peak=0.95)
    write("pegou", mix(tone(660, 0.3, decay=0.12), delay(tone(880, 0.3, decay=0.12), 0.08),
                       delay(tone(1320, 0.4, decay=0.18), 0.16)))
    write("remanso", mix(tone(392, 1.2, ((1, 1.0), (2, 0.3)), decay=0.6),
                         delay(tone(523, 1.2, ((1, 1.0), (2, 0.3)), decay=0.6), 0.25),
                         delay(tone(659, 1.4, ((1, 1.0), (2, 0.3)), decay=0.8), 0.5)))
    write("bip_teste", tone(1000, 0.35, decay=1.0, attack=0.01))
    # vigia: pedras
    write("pedra_esq", tone(320, 0.18, ((1, 1.0), (2.76, 0.4), (5.4, 0.2)), decay=0.035))
    write("pedra_dir", tone(1400, 0.6, ((1, 1.0), (2.4, 0.5), (3.9, 0.25)), decay=0.18))
    write("pedra_frente", mix(tone(700, 0.09, ((1, 1.0), (3, 0.33), (5, 0.2)), decay=1.0),
                              delay(tone(700, 0.09, ((1, 1.0), (3, 0.33), (5, 0.2)),
                                         decay=1.0), 0.13)))
    # vigia: boias e margens
    write("boia_esq", bubbles(260), peak=0.7)
    write("boia_frente", bubbles(480), peak=0.7)
    write("boia_dir", bubbles(900), peak=0.7)
    write("margem_esq", noise(0.45, smooth=0.9, attack=0.1, release=0.2), peak=0.6)
    write("margem_dir", highpass(noise(0.45, smooth=0.2, attack=0.1, release=0.2)), peak=0.5)
    # menus
    write("menu_mover", tone(880, 0.06, decay=0.03), peak=0.4)
    write("menu_confirmar", mix(tone(660, 0.1, decay=0.05), delay(tone(990, 0.12, decay=0.06),
                                                                  0.05)), peak=0.5)
    print("sons em %s" % os.path.normpath(OUT))


if __name__ == "__main__":
    main()
