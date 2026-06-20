"""Combina as logos do IAT e do Paraná/SEDEST numa imagem única, lado a lado.

Preserva as proporções de cada logo (sem distorcer) e gera DUAS versões:
  - logos_combinado.png         → cartão branco com cantos (para a sidebar escura)
  - logos_combinado_header.png  → fundo na cor do cabeçalho (#f1f5f9), mesclando
                                   (o branco da logo do Paraná é trocado pela cor de fundo)

Uso:  python dashboard/assets/montar_logos.py
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw

AQUI = Path(__file__).parent
ALTURA = 200      # altura comum das duas logos (px)
PAD = 30          # margem interna
GAP = 70          # espaço entre as duas logos
RAIO = 22         # raio dos cantos (versão cartão)
FUNDO_HEADER = (241, 245, 249)   # #f1f5f9 — cor de fundo do dashboard/cabeçalho


def trim(im):
    im = im.convert("RGBA")
    alpha = im.getchannel("A")
    if alpha.getextrema()[0] < 255:
        bbox = alpha.getbbox()
    else:
        rgb = im.convert("RGB")
        bbox = ImageChops.difference(rgb, Image.new("RGB", im.size, (255, 255, 255))).getbbox()
    return im.crop(bbox) if bbox else im


def escala_altura(im, h):
    return im.resize((max(1, round(im.width * h / im.height)), h), Image.LANCZOS)


def _compor(bg):
    iat = escala_altura(trim(Image.open(AQUI / "logo_iat.png")), ALTURA)
    pr = escala_altura(trim(Image.open(AQUI / "logo_parana_sedest.png")), ALTURA)
    larg = PAD + iat.width + GAP + pr.width + PAD
    alt = PAD + ALTURA + PAD
    card = Image.new("RGBA", (larg, alt), bg + (255,))
    card.paste(iat, (PAD, PAD), iat)
    card.paste(pr, (PAD + iat.width + GAP, PAD), pr)
    return card


def versao_cartao_branco():
    card = _compor((255, 255, 255))
    larg, alt = card.size
    mask = Image.new("L", (larg, alt), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, larg - 1, alt - 1], radius=RAIO, fill=255)
    card.putalpha(mask)
    card.save(AQUI / "logos_combinado.png")
    return card.size


def versao_mesclada(bg=FUNDO_HEADER):
    card = _compor(bg)
    arr = np.array(card)
    # troca branco (e quase-branco) pela cor de fundo, para mesclar a logo do Paraná
    branco = (arr[:, :, 0] >= 245) & (arr[:, :, 1] >= 245) & (arr[:, :, 2] >= 245)
    arr[branco] = [bg[0], bg[1], bg[2], 255]
    Image.fromarray(arr).save(AQUI / "logos_combinado_header.png")
    return card.size


def main():
    s1 = versao_cartao_branco()
    s2 = versao_mesclada()
    print(f"[OK] logos_combinado.png {s1}  |  logos_combinado_header.png {s2}")


if __name__ == "__main__":
    main()
