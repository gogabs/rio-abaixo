"""Números do rio e da canoa. Distâncias em metros, tempos em segundos."""

HALF_WIDTH = 3.0          # o rio vai de -3 (margem esquerda) a 3 (margem direita)
BANK_TOUCH = 2.6          # a partir daqui a canoa raspa na margem
BANK_WARN = 1.8           # a partir daqui o vigia ouve a margem

CURRENT = 0.6             # a correnteza leva a canoa mesmo sem remar
MAX_SPEED = 2.8
STROKE_SPEED = 0.45       # quanto cada remada acelera
DRAG = 0.35               # quanto a velocidade cai por segundo, proporcional
STROKE_TURN = 0.2         # radianos por remada; remar à esquerda vira para a direita
MAX_HEADING = 0.7
STRAIGHTEN = 0.15         # a correnteza endireita a canoa aos poucos (radianos/s)
STROKE_COOLDOWN = 0.18    # remadas mais rápidas que isso não contam

ROCK_RADIUS = 0.75        # a canoa bate se passar mais perto que isso do centro da pedra
BUOY_REACH = 1.0          # lateral, para pegar a boia com B
BUOY_WINDOW = 2.0         # à frente, para pegar a boia com B
AHEAD = 25.0              # o vigia ouve até aqui
SIDE_CENTER = 0.8         # mais perto que isso do eixo da canoa é "bem na frente"
CUES = 2                  # o vigia ouve os 2 objetos mais próximos de cada vez

HIT_SLOW = 0.15           # a velocidade cai para isso depois de uma batida
HIT_BOUNCE = 0.9          # e a canoa é empurrada para o lado

# Trechos: (comprimento, intervalo mínimo e máximo entre pedras, chance de boia)
STRETCHES = (
    (110, 16, 22, 0.35),
    (140, 12, 18, 0.35),
    (170, 9, 15, 0.30),
)
