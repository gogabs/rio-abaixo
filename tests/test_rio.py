import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from rio_abaixo import config as C  # noqa: E402
from rio_abaixo import textos as T  # noqa: E402
from rio_abaixo.rio import BUOY, ROCK, Stretch, Thing, side_of  # noqa: E402


class FakeUI:
    def __init__(self):
        self.cues, self.level = [], 0.0

    def cue(self, role, name, volume):
        self.cues.append((role, name))

    def water(self, level):
        self.level = level

    def say(self, text, queue=False):
        pass


def empty(ui=None, things=()):
    s = Stretch(ui or FakeUI(), 0, seed=1)
    s.things = list(things)
    return s


def run(s, seconds, dt=0.05, every=None):
    for i in range(int(seconds / dt)):
        if every:
            every(s, i)
        s.update(dt)


class RioTest(unittest.TestCase):
    def test_current_alone_reaches_the_end(self):
        done = []
        s = Stretch(FakeUI(), 0, seed=1, on_done=done.append)
        s.things = []
        run(s, s.length / C.CURRENT + 5)
        self.assertTrue(s.done)
        self.assertEqual(done, [s])

    def test_alternating_goes_straight_and_faster(self):
        s = empty()
        run(s, 20, every=lambda s, i: i % 8 == 0 and s.stroke("left" if i % 16 else "right"))
        self.assertLess(abs(s.x), 0.05)
        self.assertGreater(s.pos, 20 * C.CURRENT * 1.5)

    def test_repeating_left_moves_right_and_right_straightens(self):
        s = empty()
        for _ in range(3):
            s.stroke("left")
            run(s, 0.25)
        self.assertGreater(s.heading, 0.3)
        run(s, 1.5)
        self.assertGreater(s.x, 0.4)
        s.stroke("right")
        self.assertLess(s.heading, 0.3)

    def test_strokes_too_fast_do_not_count(self):
        s = empty()
        self.assertTrue(s.stroke("left"))
        self.assertFalse(s.stroke("left"))

    def test_bank_scrapes(self):
        ui = FakeUI()
        s = empty(ui)
        s.x, s.heading = 2.5, 0.6
        run(s, 1)
        self.assertLessEqual(s.x, C.BANK_TOUCH)
        self.assertEqual(s.scrapes, 1)
        self.assertIn(("pilot", "raspa"), ui.cues)

    def test_rock_in_the_way_hits_both_hear(self):
        ui = FakeUI()
        s = empty(ui, [Thing(ROCK, 3.0, 0.2)])
        run(s, 8)
        self.assertEqual(s.hits, 1)
        self.assertIn(("both", "batida"), ui.cues)
        self.assertGreater(abs(s.x - 0.2), C.ROCK_RADIUS - 0.01)

    def test_rock_to_the_side_passes(self):
        s = empty(things=[Thing(ROCK, 3.0, 1.5)])
        run(s, 8)
        self.assertEqual(s.hits, 0)

    def test_watch_hears_side_by_timbre(self):
        ui = FakeUI()
        empty(ui, [Thing(ROCK, 10, -2.0), Thing(ROCK, 12, 2.0), Thing(BUOY, 14, 0.0)]).update(0.05)
        heard = [name for role, name in ui.cues if role == "watch"]
        self.assertEqual(heard, ["pedra_esq", "pedra_dir"])   # só os 2 mais perto
        self.assertEqual([side_of(v) for v in (-1, 0, 1)], ["esq", "frente", "dir"])

    def test_pilot_never_hears_the_river(self):
        ui = FakeUI()
        s = Stretch(ui, 2, seed=3)
        run(s, 60, every=lambda s, i: i % 10 == 0 and s.stroke("left" if i % 20 else "right"))
        pilot = {name for role, name in ui.cues if role == "pilot"}
        self.assertFalse({n for n in pilot if n.startswith(("pedra", "boia", "margem"))})

    def test_grab_buoy_close_ahead(self):
        ui = FakeUI()
        s = empty(ui, [Thing(BUOY, 1.5, 0.5)])
        self.assertTrue(s.grab())
        self.assertEqual(s.buoys, 1)
        self.assertFalse(s.grab())
        self.assertIn(("pilot", "errou"), ui.cues)

    def test_missed_buoy(self):
        s = empty(things=[Thing(BUOY, 3.0, 2.0)])
        run(s, 8)
        self.assertEqual((s.buoys, s.missed), (0, 1))

    def test_good_team_can_dodge_every_rock(self):
        """Um vigia perfeito e um piloto obediente descem todos os trechos sem batida:
        o rio sempre tem passagem."""
        for index in range(len(C.STRETCHES)):
            for seed in range(5):
                s = Stretch(FakeUI(), index, seed=seed)

                def steer(s, i):
                    rocks = [t for t in s.visible() if t.kind == ROCK]
                    target = 0.0
                    if rocks and rocks[0].at - s.pos < 12:
                        r = rocks[0]
                        target = r.x - 1.6 if r.x > 0 else r.x + 1.6
                    want = max(-0.6, min(0.6, (target - s.x) * 0.8))
                    if i % 6 == 0:
                        s.stroke("left" if want > s.heading else "right")
                run(s, 400, every=steer)
                self.assertTrue(s.done, (index, seed))
                self.assertEqual(s.hits, 0, (index, seed))

    def test_texts(self):
        s = empty()
        self.assertIn("nenhuma batida", s.status_text())
        s.hits = 2
        self.assertIn("2 batidas", T.stretch_end(s, 20, last=False))
        self.assertIn("Recorde novo", T.final(50, 40))
        self.assertIn("O recorde é 60", T.final(50, 60))


if __name__ == "__main__":
    unittest.main()
