#!/usr/bin/env python3
"""Gera os sons da Canoa por síntese, só com a biblioteca padrão.

Nada é gravado nem baixado: cada som sai das fórmulas abaixo, então os
arquivos têm a mesma licença do jogo e não pedem crédito a ninguém.

A água é feita de bolhas (cada bolha é um seno curto que sobe de tom e
apaga, o modelo de van den Doel) e de ruído filtrado. Madeira e pedra são
modos: alguns senos inarmônicos que apagam depressa.

O vigia tem um ouvido só, então o lado vem do próprio som:
  - pedra: um toque de pedra. Esquerda e direita são o mesmo toque, só muda
    a altura (grave à esquerda, agudo à direita). Bem na frente é outro som,
    um baque duplo e encorpado: hora de desviar.
  - boia: na frente é um punhado de bolhas; dos lados é um sino de boia, o
    mesmo sino grave à esquerda e agudo à direita.
  - margem: folhas e água batendo no barranco; o mesmo som, mais grave à
    esquerda e mais agudo à direita.

Os sons gravados (CC0, de terceiros) saem de tools/preparar_sons.py e este
gerador pula esses nomes. Para trocar um som, ponha um arquivo com o mesmo
nome em sounds/ (WAV ou OGG).

    python3 tools/gerar_sons.py            # sons do jogo em sounds/
    python3 tools/gerar_sons.py --previa   # também as opções e as cenas de amostra
"""
import math
import os
import random
import struct
import sys
import wave

from preparar_sons import SOUNDS as RECORDED

RATE = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "sounds")
PREVIEW = os.path.join(HERE, "..", "previa-sons")
rng = random.Random(7)


def n(sec):
    return int(RATE * sec)


def silence(sec):
    return [0.0] * n(sec)


def white(sec):
    return [rng.uniform(-1, 1) for _ in range(n(sec))]


def pink(sec):
    """Ruído rosa (Paul Kellet, versão econômica): mais natural que o branco."""
    b0 = b1 = b2 = 0.0
    out = []
    for _ in range(n(sec)):
        w = rng.uniform(-1, 1)
        b0 = 0.99765 * b0 + w * 0.0990460
        b1 = 0.96300 * b1 + w * 0.2965164
        b2 = 0.57000 * b2 + w * 1.0526913
        out.append((b0 + b1 + b2 + w * 0.1848) * 0.2)
    return out


def biquad(x, kind, freq, q=0.707):
    """Filtro de segunda ordem (receitas de Robert Bristow-Johnson)."""
    w = 2 * math.pi * freq / RATE
    alpha = math.sin(w) / (2 * q)
    c = math.cos(w)
    if kind == "low":
        b = ((1 - c) / 2, 1 - c, (1 - c) / 2)
    elif kind == "high":
        b = ((1 + c) / 2, -(1 + c), (1 + c) / 2)
    else:  # "band", ganho 1 no centro
        b = (alpha, 0.0, -alpha)
    a0, a1, a2 = 1 + alpha, -2 * c, 1 - alpha
    b0, b1, b2 = (v / a0 for v in b)
    a1, a2 = a1 / a0, a2 / a0
    out, x1, x2, y1, y2 = [], 0.0, 0.0, 0.0, 0.0
    for s in x:
        y = b0 * s + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1, y2, y1 = x1, s, y1, y
        out.append(y)
    return out


def sweep(x, freqs, q=2.0):
    """Passa-faixa com o centro mudando a cada amostra (filtro de estado variável)."""
    low = band = 0.0
    damp = 1.0 / q
    out = []
    for s, f in zip(x, freqs):
        f1 = 2 * math.sin(math.pi * min(f, RATE / 6) / RATE)
        high = s - low - damp * band
        band += f1 * high
        low += f1 * band
        out.append(band)
    return out


def env(size, attack, release, hold=None):
    """Envelope: sobe em attack, fica, e desce em release (segundos)."""
    a, r = max(1, n(attack)), max(1, n(release))
    out = []
    for k in range(size):
        g = min(1.0, k / a, (size - k) / r)
        out.append(max(0.0, g))
    return out


def decay(size, tau, attack=0.002):
    a = max(1, n(attack))
    return [min(1.0, k / a) * math.exp(-k / (RATE * tau)) for k in range(size)]


def mul(x, y):
    return [a * b for a, b in zip(x, y)]


def gain(x, g):
    return [s * g for s in x]


def add_at(track, part, start, wrap=False):
    """Soma part em track a partir de start (segundos). wrap dá a volta (para loops)."""
    i0 = n(start)
    size = len(track)
    for k, s in enumerate(part):
        i = i0 + k
        if wrap:
            track[i % size] += s
        else:
            if i >= size:
                track.extend([0.0] * (i - size + 1))
                size = len(track)
            track[i] += s
    return track


def mix(*tracks):
    out = []
    for t in tracks:
        add_at(out, t, 0)
    return out


def bubble(freq, amp=1.0, damping=None, rise=0.1):
    """Uma bolha: seno que sobe de tom enquanto apaga (van den Doel, 2004)."""
    if damping is None:
        damping = 0.13 * freq + 0.0072 * freq ** 1.5     # bolhas pequenas apagam rápido
    tau = 1.0 / damping
    size = n(min(0.25, 6 * tau))
    out, phase = [], 0.0
    for k in range(size):
        t = k / RATE
        f = freq * (1 + rise * damping * t)
        phase += 2 * math.pi * f / RATE
        out.append(amp * math.sin(phase) * math.exp(-t * damping))
    return out


def modes(freq, ratios, taus, amps, sec, attack=0.0005):
    """Corpo que vibra: senos inarmônicos, cada um com o seu tempo de apagar."""
    size = n(sec)
    a = max(1, n(attack))
    out = [0.0] * size
    for r, tau, amp in zip(ratios, taus, amps):
        f = freq * r
        if f >= RATE / 2:
            continue
        w = 2 * math.pi * f / RATE
        ph = rng.uniform(0, 2 * math.pi)
        for k in range(size):
            out[k] += amp * math.sin(w * k + ph) * math.exp(-k / (RATE * tau))
    return [s * min(1.0, k / a) for k, s in enumerate(out)]


def soft(x, top=4500):
    """Tira o chiado de cima: água e madeira de verdade não são tão brilhantes."""
    return biquad(biquad(x, "low", top, q=0.6), "low", top, q=0.6)


def write(folder, name, samples, peak=0.8, loop=False):
    os.makedirs(folder, exist_ok=True)
    # tira o desvio de zero e suaviza as pontas, para não estalar
    mean = sum(samples) / max(1, len(samples))
    samples = [s - mean for s in samples]
    edge = 0 if loop else min(n(0.003), len(samples) // 2)
    for k in range(edge):
        samples[k] *= k / edge
        samples[-1 - k] *= k / edge
    top = max(1e-9, max(abs(s) for s in samples))
    data = b"".join(struct.pack("<h", int(s / top * peak * 32767)) for s in samples)
    with wave.open(os.path.join(folder, name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data)


# --- piloto -------------------------------------------------------------------

def stroke(color):
    """Remada: a pá entra (plop), puxa a água (chuá) e pinga ao sair.
    color perto de 1 é a remada da esquerda; um pouco mais aguda é a da direita."""
    size = n(1.1)
    out = [0.0] * size
    # entrada da pá: estalo curto de água e duas ou três bolhas graves
    splash = biquad(white(0.06), "band", 1000 * color, q=1.0)
    add_at(out, mul(splash, decay(len(splash), 0.012)), 0.0)
    for i in range(3):
        add_at(out, bubble(rng.uniform(220, 380) * color, amp=0.6), 0.01 + i * 0.025)
    # a puxada: ruído rosa num passa-faixa que abre e fecha, como água passando
    body = pink(0.75)
    k_total = len(body)
    centers = [(380 + 900 * math.sin(math.pi * k / k_total) ** 1.5) * color
               for k in range(k_total)]
    pull = sweep(body, centers, q=1.6)
    pull = mul(pull, [math.sin(math.pi * min(1.0, k / (k_total * 0.85))) ** 1.2
                      for k in range(k_total)])
    add_at(out, gain(pull, 2.2), 0.04)
    # pingos ao tirar a pá
    for i in range(4):
        add_at(out, bubble(rng.uniform(1300, 2600) * color, amp=0.12 + 0.05 * rng.random()),
               0.62 + 0.09 * i + rng.uniform(0, 0.05))
    return soft(out, 3500 * color)


def water_loop(sec=6.0):
    """Água no casco, em loop: marulho grave que respira e gotinhas espalhadas.
    Tudo é somado em volta do fim, então o loop não tem emenda."""
    size = n(sec)
    out = [0.0] * size
    # marulho: ruído rosa grave com duas ondas lentas (número inteiro de ciclos no loop)
    extra = n(0.5)
    base = biquad(biquad(pink(sec + 0.5), "low", 520, q=0.6), "high", 70)
    for k in range(extra):        # emenda o rabo no começo
        w = k / extra
        base[k] = base[k] * w + base[size + k] * (1 - w)
    for k in range(size):
        t = k / size
        swell = 0.55 + 0.25 * math.sin(2 * math.pi * 2 * t) + 0.2 * math.sin(2 * math.pi * 3 * t + 1)
        out[k] += base[k] * swell * 1.4
    # batidinhas da água na madeira: bolhas graves, de vez em quando
    t = 0.0
    while t < sec:
        add_at(out, bubble(rng.uniform(140, 320), amp=rng.uniform(0.15, 0.35), rise=0.05), t,
               wrap=True)
        t += rng.uniform(0.25, 0.7)
    # gotinhas agudas, bem baixo
    t = 0.1
    while t < sec:
        add_at(out, bubble(rng.uniform(900, 2200), amp=rng.uniform(0.03, 0.08)), t, wrap=True)
        t += rng.uniform(0.3, 0.9)
    return out


def scrape():
    """Casco raspando no barranco: areia e cascalho no fundo e a madeira vibrando."""
    sec = 0.9
    size = n(sec)
    out = [0.0] * size
    # o arrasto grave, irregular
    drag = biquad(biquad(white(sec), "low", 260, q=0.9), "high", 60)
    rough = [0.0] * size
    level = 0.0
    for k in range(size):
        if k % n(0.012) == 0:
            target = rng.uniform(0.3, 1.0)
        level += (target - level) * 0.004
        rough[k] = level
    add_at(out, gain(mul(drag, rough), 2.0), 0)
    # o corpo da canoa ressoando (madeira oca)
    hull = mix(gain(biquad(white(sec), "band", 165, q=8), 1.0),
               gain(biquad(white(sec), "band", 395, q=10), 0.6))
    add_at(out, gain(mul(hull, rough), 3.0), 0)
    # grãos de areia e pedrinhas
    for _ in range(140):
        grain = biquad(white(0.004), "band", rng.uniform(1800, 4500), q=1.5)
        add_at(out, gain(mul(grain, decay(len(grain), 0.0015)), rng.uniform(0.05, 0.35)),
               rng.uniform(0, sec - 0.01))
    return soft(mul(out, env(len(out), 0.05, 0.35)), 4000)


def thud():
    """Batida na pedra: madeira oca levando a pancada e água espirrando."""
    wood = modes(88, (1, 2.15, 3.9, 5.7), (0.18, 0.09, 0.05, 0.03), (1, 0.6, 0.35, 0.2), 0.8)
    click = biquad(white(0.02), "band", 900, q=0.7)
    click = mul(click, decay(len(click), 0.004))
    splash = biquad(white(0.45), "band", 1800, q=0.6)
    splash = mul(splash, [min(1.0, k / n(0.03)) * math.exp(-k / n(0.11))
                          for k in range(len(splash))])
    out = mix(wood, gain(click, 1.5))
    add_at(out, gain(splash, 0.9), 0.04)
    for i in range(5):
        add_at(out, bubble(rng.uniform(250, 700), amp=0.25), 0.06 + i * 0.04)
    return soft(out)


def miss():
    """Mão na água sem achar a boia: um espirro curto."""
    splash = biquad(white(0.25), "band", 2200, q=0.7)
    splash = mul(splash, [min(1.0, k / n(0.008)) * math.exp(-k / n(0.06))
                          for k in range(len(splash))])
    out = list(splash)
    for i in range(3):
        add_at(out, bubble(rng.uniform(500, 900), amp=0.35), 0.02 + i * 0.035)
    return soft(out, 3500)


# --- vigia --------------------------------------------------------------------

STONE = ((1, 2.32, 4.25, 6.63), (0.045, 0.025, 0.012, 0.007), (1, 0.55, 0.3, 0.15))


def knock(freq):
    """Toque de pedra: pancada seca de pedra com pedra."""
    body = modes(freq, *STONE, sec=0.22)
    click = biquad(white(0.008), "band", freq * 3, q=1.0)
    return mix(body, gain(mul(click, decay(len(click), 0.002)), 0.6))


ROCK_LEFT, ROCK_RIGHT = 520, 1250      # mais que uma oitava de distância


def rock_front():
    """Pedra bem na frente: baque duplo, grave e cheio, para não confundir com os lados."""
    def boom():
        body = modes(150, (1, 1.5, 2.32, 4.25), (0.12, 0.08, 0.04, 0.02), (1, 0.5, 0.45, 0.2),
                     0.32)
        top = modes(780, *STONE, sec=0.2)
        return mix(body, gain(top, 0.45))
    out = boom()
    add_at(out, boom(), 0.15)
    return out


def bubble_cluster(center, count=5, spread=0.25, gap=0.055):
    """Punhado de bolhas sem ordem: o som da boia bem na frente."""
    out = []
    for i in range(count):
        f = center * (1 + rng.uniform(-spread, spread))
        add_at(out, bubble(f, amp=rng.uniform(0.7, 1.0), damping=f * 0.11, rise=0.2),
               i * gap + rng.uniform(0, 0.015))
    return out


def bubble_line(start, ratio, count=4, gap=0.075):
    """Fileira de bolhas que sobe (ratio > 1) ou desce (ratio < 1) de tom."""
    out = []
    f = start
    for i in range(count):
        add_at(out, bubble(f, amp=1.0, damping=f * 0.11, rise=0.2), i * gap)
        f *= ratio
    return out


def bell(freq):
    """Sino de boia: metal oco, com uma bolha antes."""
    body = modes(freq, (1, 2.0, 2.76, 4.07, 5.4), (0.35, 0.25, 0.18, 0.1, 0.07),
                 (1, 0.4, 0.5, 0.25, 0.15), 0.6, attack=0.001)
    out = gain(bubble(freq * 0.6, damping=freq * 0.6 * 0.11, rise=0.2), 0.7)
    add_at(out, gain(body, 0.8), 0.05)
    return out


def bank(color):
    """Margem: folhas e capim farfalhando e água batendo no barranco.
    color 1 é o meio; menos é mais grave (esquerda), mais é mais agudo (direita)."""
    sec = 0.7
    size = n(sec)
    out = [0.0] * size
    # folhas: ruído em pedacinhos, com estalidos
    leaves = biquad(biquad(white(sec), "band", 2600 * color, q=0.8), "high", 600 * color)
    crackle = [0.0] * size
    level = 0.0
    for k in range(size):
        if k % n(0.008) == 0:
            target = rng.random() ** 3
        level += (target - level) * 0.05
        crackle[k] = level
    add_at(out, gain(mul(leaves, crackle), 1.3), 0)
    # água no barranco: marulho e duas bolhas
    lap = biquad(pink(sec), "band", 480 * color, q=1.2)
    add_at(out, gain(mul(lap, [math.sin(math.pi * k / size) ** 2 for k in range(size)]), 2.0), 0)
    for t in (0.18, 0.33):
        add_at(out, bubble(rng.uniform(260, 340) * color, amp=0.3, rise=0.05), t)
    return soft(mul(out, env(len(out), 0.12, 0.25)), 4000 * color)


# --- os dois e os menus (iguais aos provisórios, só na nova taxa) ----------------

def tone(freq, sec, partials=((1, 1.0),), tau=0.2, attack=0.003):
    return modes(freq, [p[0] for p in partials], [tau] * len(partials),
                 [p[1] for p in partials], sec, attack)


def game_sounds():
    s = {}
    s["remada_esq"] = (stroke(1.0), 0.75)
    s["remada_dir"] = (stroke(1.18), 0.75)
    s["agua"] = (water_loop(), 0.5)
    s["raspa"] = (scrape(), 0.7)
    s["errou"] = (miss(), 0.45)
    s["batida"] = (thud(), 0.95)
    s["pegou"] = (mix(tone(660, 0.3, tau=0.12), add_at([], tone(880, 0.3, tau=0.12), 0.08),
                      add_at([], tone(1320, 0.4, tau=0.18), 0.16)), 0.8)
    chord = ((1, 1.0), (2, 0.3))
    s["remanso"] = (mix(tone(392, 1.2, chord, tau=0.6),
                        add_at([], tone(523, 1.2, chord, tau=0.6), 0.25),
                        add_at([], tone(659, 1.4, chord, tau=0.8), 0.5)), 0.8)
    s["bip_teste"] = (tone(1000, 0.35, tau=1.0, attack=0.01), 0.8)
    s["pedra_esq"] = (knock(ROCK_LEFT), 0.8)
    s["pedra_dir"] = (knock(ROCK_RIGHT), 0.8)
    s["pedra_frente"] = (rock_front(), 0.85)
    s["boia_esq"] = (bell(520), 0.75)
    s["boia_frente"] = (bubble_cluster(520), 0.75)
    s["boia_dir"] = (bell(1170), 0.75)
    s["margem_esq"] = (bank(0.65), 0.6)
    s["margem_dir"] = (bank(1.45), 0.6)
    s["menu_mover"] = (tone(880, 0.06, tau=0.03), 0.4)
    s["menu_confirmar"] = (mix(tone(660, 0.1, tau=0.05),
                               add_at([], tone(990, 0.12, tau=0.06), 0.05)), 0.5)
    return s


def options():
    """Alternativas para comparar na prévia; não entram no jogo."""
    return {
        "opcao_boia_bolhas_esq": (bubble_line(620, 0.8), 0.75),     # desce
        "opcao_boia_bolhas_dir": (bubble_line(600, 1.25), 0.75),    # sobe
        "opcao_pedra_frente_simples": (knock(800), 0.8),
    }


def scene(sounds, names, steps=7, start_gap=1.4, end_gap=0.3):
    """Um objeto chegando: o aviso repete cada vez mais alto e mais rápido."""
    out = []
    t = 0.0
    for i in range(steps):
        p = i / (steps - 1)
        clip, _ = sounds[names[min(len(names) - 1, int(p * len(names)))]]
        add_at(out, gain(clip, 0.25 + 0.75 * p), t)
        t += start_gap + (end_gap - start_gap) * p
    return out


def scenes(sounds):
    out = {}
    out["cena_pedras_lados"] = []
    for i, name in enumerate(("pedra_esq", "pedra_frente", "pedra_dir",
                              "pedra_esq", "pedra_dir", "pedra_frente")):
        add_at(out["cena_pedras_lados"], sounds[name][0], i * 0.9)
    out["cena_boias_lados"] = []
    for i, name in enumerate(("boia_esq", "boia_frente", "boia_dir",
                              "boia_dir", "boia_esq", "boia_frente")):
        add_at(out["cena_boias_lados"], sounds[name][0], i * 0.9)
    out["cena_boia_chegando"] = scene(sounds, ("boia_dir", "boia_frente"), steps=9)
    out["cena_pedra_chegando"] = scene(sounds, ("pedra_esq", "pedra_frente"), steps=9)
    stroke_seq = []
    for i in range(6):
        add_at(stroke_seq, sounds["remada_esq" if i % 2 == 0 else "remada_dir"][0], i * 0.7)
    water = sounds["agua"][0]
    piloto = gain(water + water, 0.35)
    add_at(piloto, gain(stroke_seq, 0.9), 0.8)
    add_at(piloto, sounds["raspa"][0], 6.5)
    add_at(piloto, sounds["batida"][0], 9.0)
    out["cena_piloto"] = piloto
    return out


def normalized(sounds):
    out = {}
    for name, (clip, peak) in sounds.items():
        top = max(1e-9, max(abs(s) for s in clip))
        out[name] = ([s / top * peak for s in clip], peak)
    return out


def main():
    sounds = normalized(game_sounds())
    for name, (clip, peak) in sounds.items():
        if name not in RECORDED:
            write(OUT, name, clip, peak, loop=name == "agua")
    print("sons em %s" % os.path.normpath(OUT))
    if "--previa" in sys.argv:
        for name, (clip, peak) in options().items():
            write(PREVIEW, name, clip, peak)
        for name, clip in scenes(sounds).items():
            write(PREVIEW, name, clip, 0.85)
        print("prévia em %s" % os.path.normpath(PREVIEW))


if __name__ == "__main__":
    main()
