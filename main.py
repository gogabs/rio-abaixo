#!/usr/bin/env python3
"""Canoa: dois jogadores, um fone. Quem está com o console rema, o outro guia."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
# Durante o desenvolvimento, usa a biblioteca do repositório vizinho se não houver cópia aqui.
if not os.path.isdir(os.path.join(HERE, "r36s_a11y")):
    sys.path.insert(1, os.path.join(HERE, "..", "r36s-a11y-sdk", "python"))

import r36s_a11y as a11y

from canoa import config as C
from canoa import textos as T
from canoa.rio import Stretch

game = a11y.Game(repeat=False)
ears = game.ears
RECORD_FILE = os.path.join(game.save_dir, "recordes.json")

sounds = {}
for f in sorted(os.listdir(os.path.join(game.dir, "sounds"))):
    base, ext = os.path.splitext(f)
    if ext.lower() in (".wav", ".ogg"):
        sounds[base] = ears.load(base, os.path.join("sounds", f))
menu_sounds = {"move": game.sound.load("menu_mover", "sounds/menu_mover.wav"),
               "select": game.sound.load("menu_confirmar", "sounds/menu_confirmar.wav")}

# fase: "menu", "teste", "rio" (descendo), "remanso" (esperando o B) ou "fim"
state = {"phase": "menu", "stretch": None, "total": 0, "index": 0, "water": None,
         "after_test": None}

# Papel -> ouvido. O piloto é sempre "left" e o vigia "right"; quando o piloto
# está com o fone da direita, ears.swap troca os dois de lugar.
ROLE_EAR = {"pilot": "left", "watch": "right", "both": "both"}


class UI:
    def cue(self, role, name, volume):
        sound = sounds.get(name)
        if sound is not None:
            sound.play(ear=ROLE_EAR[role], volume=volume)

    def water(self, level):
        voice = state["water"]
        if voice is not None:
            voice.set_volume(0.15 + 0.6 * level if level > 0 else 0.0)

    def say(self, text, queue=False):
        game.say(text, queue=queue)


ui = UI()


# --- recordes ------------------------------------------------------------------
def load_record():
    try:
        with open(RECORD_FILE, encoding="utf-8") as f:
            return json.load(f).get("melhor")
    except (OSError, ValueError):
        return None


def save_record(points):
    with open(RECORD_FILE, "w", encoding="utf-8") as f:
        json.dump({"melhor": points}, f)


# --- teste de fones --------------------------------------------------------------
def ear_test(then):
    """Toca um bip só no canal esquerdo e outro só no direito, e pergunta ao piloto
    qual ele ouviu. then() segue o jogo depois da resposta."""
    state["phase"] = "teste"
    state["after_test"] = then
    ears.swap = False
    game.say(T.EAR_TEST, on_done=lambda done: play_test_bips())


def play_test_bips():
    if state["phase"] != "teste":
        return
    game.after(0.3, lambda: sounds["bip_teste"].play(ear="left"))
    game.after(1.3, lambda: sounds["bip_teste"].play(ear="right"))
    game.after(2.2, lambda: game.say(T.EAR_ASK) if state["phase"] == "teste" else None)


def answer_test(button):
    ears.swap = button == "r1"   # o piloto ouviu o bip da direita
    then = state["after_test"]
    state["after_test"] = None
    game.say(T.EAR_OK, on_done=lambda done: then())


# --- descida -------------------------------------------------------------------
def new_game():
    main_menu.close()
    state["total"] = 0
    state["index"] = 0
    ear_test(lambda: start_stretch(0))


def start_stretch(index):
    state["index"] = index
    state["phase"] = "rio"
    stretch = Stretch(ui, index, on_done=end_stretch)
    stretch.paused = True     # espera a fala de início
    state["stretch"] = stretch
    state["water"] = sounds["agua"].play(ear="left", loop=True, volume=0.2)

    def go(done):
        if state["stretch"] is stretch:
            stretch.paused = False
    game.say(T.stretch_start(index), on_done=go)


def end_stretch(stretch):
    stop_water()
    state["total"] += T.points(stretch)
    last = stretch.index + 1 >= len(C.STRETCHES)
    ui.cue("both", "remanso", 1.0)
    text = T.stretch_end(stretch, state["total"], last)
    if last:
        state["phase"] = "fim"
        best = load_record()
        if best is None or state["total"] > best:
            save_record(state["total"])
        text += " " + T.final(state["total"], best)
        game.after(0.8, lambda: game.say(text, on_done=lambda done: back_to_menu()))
    else:
        state["phase"] = "remanso"
        game.after(0.8, lambda: game.say(text))


def next_stretch():
    ears.swap = not ears.swap      # quem era vigia agora rema, sem trocar de fone
    start_stretch(state["index"] + 1)


def stop_water():
    if state["water"] is not None:
        state["water"].stop(fade=0.4)
        state["water"] = None


def back_to_menu():
    stop_water()
    state["phase"] = "menu"
    state["stretch"] = None
    open_main()


@game.on_update
def update(dt):
    stretch = state["stretch"]
    if state["phase"] == "rio" and stretch is not None:
        stretch.update(dt)


# --- menus ------------------------------------------------------------------------
MAIN_ITEMS = ["Jogar", "Teste de fones", "Como jogar", "Recorde", "Sair"]


def open_main(item=None, announce_help=False):
    index = MAIN_ITEMS.index(item) if item in MAIN_ITEMS else 0
    main_menu.open(index=index, announce_help=announce_help)


def on_main(index, item):
    if item == "Jogar":
        new_game()
    elif item == "Teste de fones":
        main_menu.close()
        ear_test(lambda: open_main("Teste de fones"))
    elif item == "Como jogar":
        main_menu.close()
        help_menu.open()
    elif item == "Recorde":
        best = load_record()
        game.say("Recorde da dupla: %d pontos." % best if best is not None
                 else "Ainda não há recorde. Desçam o rio!")
    else:
        game.quit()


main_menu = a11y.Menu(game, "Canoa", MAIN_ITEMS, on_select=on_main, on_back=game.quit,
                      sounds=menu_sounds)


def close_help():
    help_menu.close()
    open_main("Como jogar")


help_menu = a11y.Menu(
    game, "Como jogar", [t for t, _ in T.HELP] + ["Voltar"],
    on_select=lambda i, item: close_help() if item == "Voltar" else game.say(T.HELP[i][1]),
    on_back=close_help, sounds=menu_sounds)


def pause():
    stretch = state["stretch"]
    if stretch is not None:
        stretch.paused = True
    ears.pause_all()
    pause_menu.open()


def resume():
    pause_menu.close()
    ears.resume_all()
    stretch = state["stretch"]
    if stretch is None or state["phase"] != "rio":
        return
    game.say("Continuando. " + stretch.status_text(),
             on_done=lambda done: setattr(stretch, "paused", False))


def on_pause(index, item):
    if item == "Continuar":
        resume()
    elif item == "Refazer o teste de fones":
        pause_menu.close()
        ears.stop_all()
        state["water"] = None
        phase, stretch = state["phase"], state["stretch"]

        def back():
            # o teste diz de novo de que lado está o piloto; a descida segue de onde parou
            state["phase"] = phase
            if phase == "remanso":
                game.say("Quem está com o console aperta B para descer o próximo trecho.")
                return
            state["water"] = sounds["agua"].play(ear="left", loop=True, volume=0.2)
            game.say("Continuando. " + stretch.status_text(),
                     on_done=lambda done: setattr(stretch, "paused", False))
        ear_test(back)
    else:
        pause_menu.close()
        ears.stop_all()
        back_to_menu()


pause_menu = a11y.Menu(game, "Pausa", ["Continuar", "Refazer o teste de fones",
                                       "Sair para o menu"],
                       on_select=on_pause, on_back=resume, sounds=menu_sounds)


# --- controles ----------------------------------------------------------------------
STROKES = {"l1": "left", "left": "left", "r1": "right", "right": "right"}


@game.on_button
def button(b, st, ms):
    if st != a11y.DOWN:
        return
    phase = state["phase"]
    if phase == "teste":
        if b in ("l1", "r1"):
            state["phase"] = "menu"   # para de aceitar respostas
            answer_test(b)
        elif b == "select":
            play_test_bips()
        return
    if phase == "remanso":
        if b == "b" or a11y.is_confirm(b):
            next_stretch()
        elif b == "start":
            pause()
        return
    if phase != "rio":
        return
    stretch = state["stretch"]
    if b in STROKES:
        stretch.stroke(STROKES[b])
    elif b == "b":
        stretch.grab()
    elif b in ("y", "select"):
        game.say(stretch.status_text())
    elif b == "start":
        pause()


@game.on_start
def start():
    game.say(T.INTRO, on_done=lambda done: open_main(announce_help=True))


game.run()
