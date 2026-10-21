#!/usr/bin/env python3
"""Prepara os sons gravados (de terceiros, CC0) que o Rio Abaixo usa, só com a biblioteca padrão.

Os originais ficam em sons-originais/, como vieram (já recortados), e os
créditos em CREDITOS.md. Daqui saem os arquivos de sounds/: no mesmo nível de
volume dos sons sintetizados, a 44,1 kHz, e com o tom mudado onde o lado vem
do tom (grave à esquerda, agudo à direita, para o vigia que tem um ouvido só).

Os sons que não estão aqui saem de tools/gerar_sons.py, que pula estes.

    python3 tools/preparar_sons.py
"""
import math
import os
import struct
import wave

RATE = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "sons-originais")
OUT = os.path.join(HERE, "..", "sounds")

# nome no jogo: (original, tom, volume, duração máxima em segundos, loop)
# volume é o pico do RMS em janelas de 50 ms, igual ao dos sons sintetizados
SOUNDS = {
    "remada_esq": ("remada_1_bigsoundbank.wav", 1.0, 0.21, None, False),
    "remada_dir": ("remada_1_bigsoundbank.wav", 1.08, 0.24, None, False),
    "agua": ("agua_1_bigsoundbank.wav", 1.0, 0.19, None, True),
    "raspa": ("raspa_1_oga-antumdeluge.wav", 1.0, 0.21, None, False),
    "batida": ("batida_1_kenney.wav", 1.0, 0.41, None, False),
    "errou": ("errou_2_bigsoundbank.wav", 1.0, 0.18, None, False),
    "margem_esq": ("margem_1_oga-qubodup.wav", 0.75, 0.2, None, False),
    "margem_dir": ("margem_1_oga-qubodup.wav", 1.4, 0.16, None, False),
    "pedra_esq": ("pedra_1_bigsoundbank.wav", 0.7, 0.28, None, False),
    "pedra_dir": ("pedra_1_bigsoundbank.wav", 1.5, 0.26, None, False),
    "pedra_frente": ("pedra_2_bigsoundbank.wav", 1.0, 0.32, None, False),
    # o sino toca de novo a cada 0,25 s quando a boia está perto: 1,6 s basta
    "boia_esq": ("boia_1_bigsoundbank.wav", 0.7, 0.3, 1.6, False),
    "boia_dir": ("boia_1_bigsoundbank.wav", 1.5, 0.28, 1.6, False),
}


def read(path):
    with wave.open(path, "rb") as w:
        assert w.getsampwidth() == 2, path
        rate, chans = w.getframerate(), w.getnchannels()
        raw = w.readframes(w.getnframes())
    data = struct.unpack("<%dh" % (len(raw) // 2), raw)
    mono = [sum(data[i:i + chans]) / chans / 32768 for i in range(0, len(data), chans)]
    return mono, rate


def resample(x, rate, pitch):
    """Muda o tom e a taxa juntos, por interpolação linear (o som fica mais curto se sobe)."""
    step = pitch * rate / RATE
    out, pos = [], 0.0
    while pos < len(x) - 1:
        i = int(pos)
        f = pos - i
        out.append(x[i] * (1 - f) + x[i + 1] * f)
        pos += step
    return out


def loudness(x):
    win = int(RATE * 0.05)
    top = 0.0
    for i in range(0, max(1, len(x) - win), win // 2):
        part = x[i:i + win]
        top = max(top, math.sqrt(sum(s * s for s in part) / len(part)))
    return top


def trim(x, max_sec):
    """Corta o silêncio do fim (e o que passar de max_sec) com uma saída suave."""
    end = len(x)
    floor = 0.003 * max(abs(s) for s in x)
    while end > 0 and abs(x[end - 1]) < floor:
        end -= 1
    if max_sec:
        end = min(end, int(RATE * max_sec))
    x = x[:end]
    fade = min(len(x), int(RATE * (0.3 if max_sec else 0.02)))
    for k in range(fade):
        x[-1 - k] *= k / fade
    return x


def write(name, x):
    data = b"".join(struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32767)) for s in x)
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data)


def main():
    for name, (src, pitch, level, max_sec, loop) in SOUNDS.items():
        x, rate = read(os.path.join(SRC, src))
        x = resample(x, rate, pitch)
        if not loop:   # o loop da água já vem com as pontas casadas
            x = trim(x, max_sec)
        g = level / max(1e-9, loudness(x))
        g = min(g, 0.95 / max(1e-9, max(abs(s) for s in x)))   # sem estourar
        write(name, [s * g for s in x])
    print("%d sons em %s" % (len(SOUNDS), os.path.normpath(OUT)))


if __name__ == "__main__":
    main()
