"""O rio, a canoa e o que cada um ouve. Sem áudio nem fala: tudo passa pela ui.

A ui recebe:
  ui.cue(papel, som, volume)   papel é "pilot", "watch" ou "both"
  ui.water(nível)              volume (0 a 1) da água no casco, só para o piloto
  ui.say(texto, queue=False)   fala para os dois
"""
import math
import random

from . import config as C

ROCK, BUOY = "pedra", "boia"


class Thing:
    def __init__(self, kind, at, x):
        self.kind = kind
        self.at = at        # metros rio abaixo, desde o começo do trecho
        self.x = x          # -3 margem esquerda, 3 margem direita
        self.gone = False   # já passou, bateu ou foi pega
        self.timer = 0.0    # até o próximo aviso do vigia


def build(stretch, rng):
    """As pedras e boias de um trecho (índice em C.STRETCHES)."""
    length, gap_min, gap_max, buoy_chance = C.STRETCHES[stretch]
    things = []
    at = 20.0
    while at < length - 10:
        things.append(Thing(ROCK, at, rng.uniform(-2.2, 2.2)))
        gap = rng.uniform(gap_min, gap_max)
        if rng.random() < buoy_chance:
            things.append(Thing(BUOY, at + gap / 2, rng.uniform(-2.0, 2.0)))
        at += gap
    return length, things


def side_of(rel):
    if rel < -C.SIDE_CENTER:
        return "esq"
    if rel > C.SIDE_CENTER:
        return "dir"
    return "frente"


def cue_interval(distance):
    """Mais perto, avisos mais rápidos: de 1,6 s lá longe a 0,25 s em cima."""
    return 0.25 + 1.35 * max(0.0, min(1.0, distance / C.AHEAD))


def cue_volume(distance):
    return 0.25 + 0.75 * (1.0 - max(0.0, min(1.0, distance / C.AHEAD)))


class Stretch:
    """Um trecho do rio, do começo ao remanso."""

    def __init__(self, ui, stretch, seed=None, on_done=None):
        self.ui = ui
        self.index = stretch
        self.length, self.things = build(stretch, random.Random(seed))
        self.on_done = on_done
        self.pos = 0.0          # metros andados
        self.x = 0.0
        self.heading = 0.0      # radianos; positivo aponta para a margem direita
        self.speed = C.CURRENT
        self.time = 0.0
        self.hits = 0
        self.scrapes = 0
        self.buoys = 0
        self.missed = 0
        self.done = False
        self.paused = False
        self._cooldown = 0.0
        self._last_side = None
        self._scrape_cd = 0.0
        self._bank_timer = 0.0

    # --- piloto -----------------------------------------------------------
    def stroke(self, side):
        """Remada: "left" (L1) ou "right" (R1). Alternar os lados vai reto e endireita;
        repetir L1 vira a proa para a direita, repetir R1 para a esquerda."""
        if self.done or self.paused or self._cooldown > 0:
            return False
        self._cooldown = C.STROKE_COOLDOWN
        if side == self._last_side:
            # o mesmo lado de novo vira a canoa
            turn = C.STROKE_TURN if side == "left" else -C.STROKE_TURN
            self.heading = max(-C.MAX_HEADING, min(C.MAX_HEADING, self.heading + turn))
        else:
            # trocar de lado endireita: é o que deixa "alternar" ir reto
            self.heading = (max(0.0, self.heading - C.STROKE_TURN) if self.heading > 0
                            else min(0.0, self.heading + C.STROKE_TURN))
        self._last_side = side
        self.speed = min(C.MAX_SPEED, max(self.speed, C.CURRENT) + C.STROKE_SPEED)
        self.ui.cue("pilot", "remada_" + ("esq" if side == "left" else "dir"), 1.0)
        return True

    def grab(self):
        """B: pega a boia que estiver logo à frente e perto do lado da canoa."""
        if self.done or self.paused:
            return False
        for t in self.visible():
            d = t.at - self.pos
            if t.kind == BUOY and d <= C.BUOY_WINDOW and abs(t.x - self.x) <= C.BUOY_REACH:
                t.gone = True
                self.buoys += 1
                self.ui.cue("both", "pegou", 1.0)
                return True
        self.ui.cue("pilot", "errou", 0.8)
        return False

    # --- tempo --------------------------------------------------------------
    def visible(self):
        """Pedras e boias à frente, até onde o vigia ouve, da mais perto à mais longe."""
        ahead = [t for t in self.things
                 if not t.gone and 0.0 < t.at - self.pos <= C.AHEAD]
        return sorted(ahead, key=lambda t: t.at)

    def update(self, dt):
        if self.done or self.paused:
            return
        self.time += dt
        self._cooldown = max(0.0, self._cooldown - dt)
        self._scrape_cd = max(0.0, self._scrape_cd - dt)

        # a correnteza endireita a proa e puxa a velocidade para a dela
        if self.heading > 0:
            self.heading = max(0.0, self.heading - C.STRAIGHTEN * dt)
        else:
            self.heading = min(0.0, self.heading + C.STRAIGHTEN * dt)
        self.speed += (C.CURRENT - self.speed) * min(1.0, C.DRAG * dt)

        before = self.pos
        self.pos += self.speed * math.cos(self.heading) * dt
        self.x += self.speed * math.sin(self.heading) * dt
        self._banks()
        self._passing(before)
        self.ui.water(min(1.0, self.speed / C.MAX_SPEED))
        self._warn(dt)

        if self.pos >= self.length:
            self.done = True
            self.ui.water(0.0)
            if self.on_done:
                self.on_done(self)

    def _banks(self):
        if abs(self.x) <= C.BANK_TOUCH:
            return
        sign = 1 if self.x > 0 else -1
        self.x = sign * C.BANK_TOUCH
        self.heading = -sign * 0.1          # a margem empurra a proa para o meio
        self.speed = min(self.speed, C.CURRENT)
        if self._scrape_cd <= 0:
            self._scrape_cd = 0.8
            self.scrapes += 1
            self.ui.cue("pilot", "raspa", 1.0)

    def _passing(self, before):
        """Confere o que a canoa acabou de alcançar."""
        for t in self.things:
            if t.gone or not (before < t.at <= self.pos):
                continue
            t.gone = True
            rel = t.x - self.x
            if t.kind == BUOY:
                self.missed += 1
            elif abs(rel) < C.ROCK_RADIUS:
                self.hits += 1
                self.speed = C.HIT_SLOW
                self.heading = 0.0
                push = -1 if rel > 0 else 1
                self.x = max(-C.BANK_TOUCH, min(C.BANK_TOUCH, self.x + push * C.HIT_BOUNCE))
                self.ui.cue("both", "batida", 1.0)

    def _warn(self, dt):
        """O que o vigia ouve: as pedras e boias mais perto e a margem."""
        for i, t in enumerate(self.visible()):
            if i >= C.CUES:
                t.timer = 0.0   # quando ficar entre as mais perto, avisa na hora
                continue
            t.timer -= dt
            if t.timer <= 0:
                d = t.at - self.pos
                self.ui.cue("watch", "%s_%s" % (t.kind, side_of(t.x - self.x)), cue_volume(d))
                t.timer = cue_interval(d)
        if abs(self.x) > C.BANK_WARN:
            self._bank_timer -= dt
            if self._bank_timer <= 0:
                near = (abs(self.x) - C.BANK_WARN) / (C.BANK_TOUCH - C.BANK_WARN)
                self.ui.cue("watch", "margem_" + ("dir" if self.x > 0 else "esq"),
                            0.4 + 0.6 * min(1.0, near))
                self._bank_timer = 1.0 - 0.6 * min(1.0, near)
        else:
            self._bank_timer = 0.0

    # --- falas ------------------------------------------------------------
    def left(self):
        return max(0, int(round(self.length - self.pos)))

    def status_text(self):
        return ("Trecho %d de %d. Faltam %d metros para o remanso. %s, %s, %s."
                % (self.index + 1, len(C.STRETCHES), self.left(),
                   plural(self.hits, "batida", "batidas"),
                   plural(self.scrapes, "raspada na margem", "raspadas na margem"),
                   plural(self.buoys, "boia", "boias")))


def plural(n, one, many):
    if n == 0:
        return "nenhuma " + one   # todas as contagens do jogo são femininas
    return "%d %s" % (n, one if n == 1 else many)
