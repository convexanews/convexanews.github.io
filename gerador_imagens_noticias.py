# -*- coding: utf-8 -*-
"""Gera capas próprias por pauta, sem baixar ou reutilizar imagens de portais."""
import base64
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

MODELO = 'gemini-3.1-flash-image'
LIMITE_POR_EXECUCAO = 2


def direcao(materia):
    texto = f"{materia.get('titulo', '')} {' '.join(materia.get('tickers', []))}".lower()
    if any(x in texto for x in ('ibovespa', 'b3', 'bolsa', 'pregão', 'pregao')):
        return 'pregão da bolsa brasileira, painéis abstratos de cotações e gráfico luminoso, São Paulo'
    if any(x in texto for x in ('dólar', 'dolar', 'câmbio', 'cambio')):
        return 'câmbio entre real e dólar em composição abstrata, gráfico cambial discreto'
    if any(x in texto for x in ('petrobras', 'petróleo', 'petroleo', 'petr4')):
        return 'plataforma de petróleo marítima ao amanhecer e infraestrutura de energia'
    if any(x in texto for x in ('selic', 'copom', 'juros', 'inflação', 'inflacao')):
        return 'economia brasileira, curvas de juros e edifício institucional abstrato'
    if any(x in texto for x in ('trump', 'eua', 'fed', 'wall street', 'eleição', 'eleicao')):
        return 'geopolítica e mercado global, prédios institucionais e bandeiras desfocadas ao fundo'
    if any(x in texto for x in ('bitcoin', 'cripto', 'ethereum', 'btc')):
        return 'mercado de criptoativos, rede de blocos luminosa e moeda digital abstrata'
    if any(x in texto for x in ('fii', 'imobili', 'ifix')):
        return 'edifícios corporativos e galpões modernos, mercado imobiliário financeiro'
    return 'mercado financeiro brasileiro, gráficos abstratos e São Paulo ao amanhecer'


def gerar(chave, materia, destino):
    prompt = f"""Crie uma capa editorial ORIGINAL para uma notícia financeira brasileira.
Tema: {direcao(materia)}.
Título de contexto: {materia.get('titulo', '')}.
Foto-ilustração premium horizontal 16:9, nas cores azul-marinho, grafite e dourado.
Crie uma cena inédita baseada somente no tema textual. Não copie, reconstrua, imite ou use como referência uma foto, arte ou composição de um portal. Não inclua palavras, números legíveis, logotipos, marcas d'água ou textos. Evite apresentar um evento real como fotografia documental."""
    corpo = {'model': MODELO, 'input': [{'type': 'text', 'text': prompt}]}
    requisicao = urllib.request.Request(
        'https://generativelanguage.googleapis.com/v1beta/interactions',
        data=json.dumps(corpo).encode(),
        method='POST',
        headers={'x-goog-api-key': chave, 'Content-Type': 'application/json'},
    )
    try:
        with urllib.request.urlopen(requisicao, timeout=120) as resposta:
            dados = json.loads(resposta.read().decode())
    except urllib.error.HTTPError as erro:
        detalhe = erro.read().decode('utf-8', errors='replace')[:500]
        raise RuntimeError(f'HTTP {erro.code}: {detalhe}') from erro
    imagem = (dados.get('output_image') or {}).get('data')
    if not imagem:
        raise RuntimeError('API não devolveu imagem')
    destino.write_bytes(base64.b64decode(imagem))


def fonte(tamanho, negrito=False):
    try:
        return ImageFont.truetype('DejaVuSans-Bold.ttf' if negrito else 'DejaVuSans.ttf', tamanho)
    except OSError:
        return ImageFont.load_default()


def aplicar_identidade(destino):
    """Acrescenta marca e transparência editorial à arte que a IA acabou de criar."""
    with Image.open(destino) as original:
        imagem = original.convert('RGB')
        largura, altura = imagem.size
        faixa = max(72, int(altura * 0.105))
        desenho = ImageDraw.Draw(imagem)
        desenho.rectangle((0, altura - faixa, largura, altura), fill=(10, 28, 53))
        margem = max(24, int(largura * 0.032))
        desenho.text(
            (margem, altura - faixa + int(faixa * 0.18)),
            'BOM DIA INVESTIDOR',
            font=fonte(max(20, int(faixa * 0.29)), negrito=True),
            fill=(236, 181, 39),
        )
        desenho.text(
            (margem, altura - faixa + int(faixa * 0.60)),
            'IMAGEM GERADA POR IA',
            font=fonte(max(15, int(faixa * 0.21)), negrito=True),
            fill=(242, 244, 247),
        )
        imagem.save(destino, format='PNG', optimize=True)


def main():
    chave = os.environ.get('GEMINI_IMAGE_API_KEY', '')
    if not chave:
        print('Imagens IA: chave ausente.')
        return
    arquivo = Path('materias.json')
    materias = json.loads(arquivo.read_text(encoding='utf-8'))
    pasta = Path('img/noticias')
    pasta.mkdir(parents=True, exist_ok=True)
    feitas = 0
    for materia in materias:
        if materia.get('image', {}).get('licensed'):
            continue
        destino = pasta / (re.sub(r'[^a-zA-Z0-9_-]', '-', materia['id']) + '.png')
        try:
            gerar(chave, materia, destino)
            aplicar_identidade(destino)
            materia['image'] = {
                'url': f'./{destino.as_posix()}',
                'licensed': True,
                'credit': 'Imagem gerada por IA · Bom Dia Investidor',
                'alt': materia['titulo'],
            }
            feitas += 1
        except Exception as erro:
            print(f'Imagens IA: ignorada: {erro}')
        if feitas >= LIMITE_POR_EXECUCAO:
            break
    if feitas:
        arquivo.write_text(json.dumps(materias, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Imagens IA: {feitas} capa(s).')


if __name__ == '__main__':
    main()
