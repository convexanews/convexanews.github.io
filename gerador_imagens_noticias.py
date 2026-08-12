# -*- coding: utf-8 -*-
"""Capas próprias por pauta; não baixa imagens de portais."""
import base64, json, os, re, urllib.error, urllib.request
from pathlib import Path

MODELO = 'gemini-3.1-flash-image'

def direcao(materia):
    t = f"{materia.get('titulo', '')} {' '.join(materia.get('tickers', []))}".lower()
    if any(x in t for x in ('ibovespa', 'b3', 'bolsa', 'pregão', 'pregao')): return 'pregão da bolsa brasileira, painéis abstratos de cotações e gráfico luminoso, São Paulo'
    if any(x in t for x in ('dólar', 'dolar', 'câmbio', 'cambio')): return 'câmbio: real e dólar em composição abstrata, gráfico cambial discreto'
    if any(x in t for x in ('petrobras', 'petróleo', 'petroleo', 'petr4')): return 'plataforma de petróleo marítima ao amanhecer e energia'
    if any(x in t for x in ('selic', 'copom', 'juros', 'inflação', 'inflacao')): return 'economia brasileira, curvas de juros e edifício institucional abstrato'
    if any(x in t for x in ('trump', 'eua', 'fed', 'wall street', 'eleição', 'eleicao')): return 'geopolítica e mercado global, Capitólio e bandeiras ao fundo, sem pessoas identificáveis'
    if any(x in t for x in ('bitcoin', 'cripto', 'ethereum', 'btc')): return 'mercado de criptoativos, rede de blocos luminosa e moeda digital abstrata'
    if any(x in t for x in ('fii', 'imobili', 'ifix')): return 'edifícios corporativos e galpões modernos, mercado imobiliário financeiro'
    return 'mercado financeiro brasileiro, gráficos abstratos e São Paulo ao amanhecer'

def gerar(chave, materia, destino):
    prompt = f"Capa editorial premium para notícia financeira brasileira. Tema: {direcao(materia)}. Foto-ilustração jornalística realista, horizontal 16:9, azul-marinho, grafite e dourado. Sem palavras, números legíveis, logotipos, marcas d'água ou pessoas identificáveis. Ilustração editorial original criada por IA, não uma foto de evento real."
    # A criação inicial aceita somente modelo e prompt. Formato/resolução são
    # opções de uma edição posterior e causavam HTTP 400 nesta chamada.
    corpo = {'model': MODELO, 'input': [{'type':'text','text':prompt}]}
    req = urllib.request.Request('https://generativelanguage.googleapis.com/v1beta/interactions', data=json.dumps(corpo).encode(), method='POST', headers={'x-goog-api-key':chave,'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=120) as r: dados = json.loads(r.read().decode())
    except urllib.error.HTTPError as erro:
        detalhe = erro.read().decode('utf-8', errors='replace')[:500]
        raise RuntimeError(f'HTTP {erro.code}: {detalhe}') from erro
    imagem = (dados.get('output_image') or {}).get('data')
    if not imagem: raise RuntimeError('API não devolveu imagem')
    destino.write_bytes(base64.b64decode(imagem))

def main():
    chave = os.environ.get('GEMINI_IMAGE_API_KEY', '')
    if not chave: print('Imagens IA: chave ausente.'); return
    arquivo = Path('materias.json'); materias = json.loads(arquivo.read_text(encoding='utf-8')); pasta = Path('img/noticias'); pasta.mkdir(parents=True, exist_ok=True)
    feitas = 0
    for m in materias:
        if m.get('image', {}).get('licensed'): continue
        destino = pasta / (re.sub(r'[^a-zA-Z0-9_-]', '-', m['id']) + '.png')
        try:
            gerar(chave, m, destino)
            m['image'] = {'url': f'./{destino.as_posix()}', 'licensed': True, 'credit':'Ilustração editorial gerada por IA · Bom Dia Investidor', 'alt':m['titulo']}; feitas += 1
        except Exception as e: print(f'Imagens IA: ignorada: {e}')
        if feitas >= 2: break
    if feitas: arquivo.write_text(json.dumps(materias, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Imagens IA: {feitas} capa(s).')

if __name__ == '__main__': main()
