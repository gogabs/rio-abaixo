# Origem e atualização do Mage Core

A cópia de reserva em `r36s_a11y/` vem de
[gogabs/r36s-a11y-sdk](https://github.com/gogabs/r36s-a11y-sdk), no commit
registrado em `sdk-origin.json`, junto com os hashes dos arquivos. A Canoa
precisa do `game.ears` (som num ouvido só), que entrou no Mage Core junto com
este jogo.

O instalador prefere um clone do Mage Core ao lado deste repositório e usa a
cópia incluída como reserva. Para atualizar a cópia de reserva:

```sh
python3 tools/sync_sdk.py --sdk ../r36s-a11y-sdk
python3 -m unittest discover -s tests
git diff -- r36s_a11y sdk-origin.json
```
