# Canoa

Jogo de áudio para dois no R36S acessível, no **modo dueto**: um fone, cada
pessoa com um lado. Quem está com o console é o piloto e rema; o outro é o
vigia, não aperta nada e guia pela voz.

- O piloto ouve só a canoa: as remadas, a água no casco e as batidas.
- O vigia ouve só o rio à frente: pedras, boias e margens. Como ele tem um
  ouvido só, o lado vem do próprio som: pedra grave é à esquerda, aguda é à
  direita, e um baque duplo é bem na frente; bolhas que descem são boia à
  esquerda, que sobem são à direita. Mais perto, mais alto e mais rápido.
- O rio tem 3 trechos. No remanso, passem o console. Ninguém troca de fone:
  o jogo troca o que toca em cada lado.

Antes da descida, um teste de fones toca um bip em cada lado e o piloto diz
qual ouviu. Sem fone, no alto-falante, os dois ouvem tudo e o jogo perde a
graça.

Feito em Python com o [Mage Core](https://github.com/gogabs/r36s-a11y-sdk).
O som por ouvido usa o `game.ears` (SDL2_mixer), que toca cada som só num
canal, sem o vazamento do HRTF.

## Controles (piloto)

| Botão | O quê |
|---|---|
| L1 / R1 (ou esquerda / direita) | Rema do lado esquerdo / direito. Alternar vai reto e endireita; repetir um lado vira (L1 L1 vai para a direita) |
| B | Pega a boia logo à frente |
| Y ou Select | Trecho, distância até o remanso, batidas e boias |
| Start | Pausa; dá para refazer o teste de fones |

## Rodar

No PC (Windows, com o Mage Core clonado ao lado ou a cópia em `r36s_a11y/`):

```bat
python main.py
```

No console, com o Mage Core clonado ao lado deste repositório:

```bash
./instalar.sh
```

## Desenvolvimento

```bash
python3 -m unittest discover -s tests   # testes, inclusive um piloto automático
python3 tools/gerar_sons.py             # sons, por síntese (--previa gera amostras)
python3 tools/sync_sdk.py               # atualiza a cópia do Mage Core em r36s_a11y/
```

Números do rio e da canoa em [canoa/config.py](canoa/config.py).
