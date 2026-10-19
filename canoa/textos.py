"""Falas mais longas: ajuda, trocas e fim de descida. Toda fala sai para os dois."""
from . import config as C
from .rio import plural

INTRO = ("Canoa. Um jogo para dois, com um fone só: cada pessoa fica com um lado. "
         "Quem está com o console rema; o outro é o vigia e guia pela voz.")

EAR_TEST = ("Teste de fones. Vão tocar dois bips, um em cada lado do fone. "
            "Cada pessoa deve ouvir um bip só.")
EAR_ASK = ("Quem está com o console: aperte L1 se ouviu o primeiro bip, "
           "R1 se ouviu o segundo. Select toca de novo.")
EAR_OK = "Combinado. Quem está com o console é o piloto. O outro é o vigia."

HELP = (
    ("Os papéis",
     "Quem está com o console é o piloto e rema. O outro é o vigia: não aperta nada, "
     "só fala. Cada um fica com um lado do fone, e cada lado toca uma coisa diferente. "
     "O piloto ouve só a canoa: as remadas, a água no casco e as batidas. O vigia ouve só "
     "o rio à frente. A fala do jogo sai para os dois."),
    ("Remar",
     "L1 rema do lado esquerdo da canoa e R1 do lado direito. As setas esquerda e direita "
     "fazem o mesmo. Alternar L1 e R1 vai reto, mais rápido, e endireita a canoa. Repetir "
     "o mesmo lado vira: L1 duas vezes leva a canoa para a direita, R1 duas vezes para a "
     "esquerda. A correnteza leva a canoa mesmo sem remar e endireita a proa aos poucos. "
     "Encostar na margem raspa e freia."),
    ("O que o vigia ouve",
     "Pedra à esquerda da canoa é um toque grave de madeira. Pedra à direita é um sino "
     "agudo. Pedra bem na frente é um alarme duplo: hora de desviar. Quanto mais perto, "
     "mais alto e mais rápido. Boia é um borbulhar: grave à esquerda, agudo à direita, "
     "médio na frente. Margem perto é um farfalhar de folhas, grave na esquerda e agudo "
     "na direita."),
    ("Boias",
     "Quando o vigia ouvir a boia bem na frente e bem rápido, ele avisa, e o piloto "
     "aperta B para pegar. Boia vale pontos; pedra e margem tiram."),
    ("Remanso e troca",
     "O rio tem %d trechos. No fim de cada um vem um remanso: passem o console para o "
     "vigia. Ninguém troca de fone: o jogo troca o que toca em cada lado. Quem pegar o "
     "console aperta B para descer o próximo trecho." % len(C.STRETCHES)),
    ("Botões",
     "L1 e R1: remar. B: pegar boia. Y ou Select: onde estão e como vão. "
     "Start: pausa. Na pausa dá para refazer o teste de fones."),
)

PILOT_KEYS = "L1 e R1 remam: alternar vai reto, repetir um lado vira. B pega boia."


def stretch_start(index):
    if index == 0:
        return "Trecho 1 de %d. Remem! %s" % (len(C.STRETCHES), PILOT_KEYS)
    return "Trecho %d de %d. Remem!" % (index + 1, len(C.STRETCHES))


def points(stretch):
    return max(0, 30 + 10 * stretch.buoys - 5 * stretch.hits - 2 * stretch.scrapes
               - int(stretch.time // 15))


def stretch_end(stretch, total, last):
    text = ("Remanso. Trecho %d em %d segundos: %s, %s, %s. %d pontos, %d no total."
            % (stretch.index + 1, int(round(stretch.time)),
               plural(stretch.hits, "batida", "batidas"),
               plural(stretch.scrapes, "raspada na margem", "raspadas na margem"),
               plural(stretch.buoys, "boia", "boias"), points(stretch), total))
    if not last:
        text += (" Passem o console para o vigia. Agora quem estava guiando rema. "
                 "Quem pegou o console aperta B quando estiver pronto.")
    return text


def final(total, best):
    if best is None or total > best:
        record = "Recorde novo!" if best is not None else "Primeiro recorde da dupla."
    else:
        record = "O recorde é %d." % best
    return "Chegaram ao fim do rio! %d pontos. %s" % (total, record)
