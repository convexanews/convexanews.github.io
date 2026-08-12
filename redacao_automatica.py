# -*- coding: utf-8 -*-
"""Cria matérias completas a partir de pautas confirmadas, sem extrair artigos de terceiros."""
import json
import os
import re
from datetime import datetime, timezone

from ia_resumo import gerar_artigo

IGNORADAS = {'para', 'com', 'sobre', 'entre', 'após', 'apos', 'como', 'mais', 'menos', 'hoje', 'mercado', 'bolsa', 'ações', 'acoes', 'brasil'}


def palavras(texto):
    return {p for p in re.findall(r'[a-záàâãéêíóôõúç0-9]{4,}', texto.lower()) if p not in IGNORADAS}


def fontes_convergentes(noticia, noticias):
    chaves = palavras(noticia.get('title', '')) | {t.lower() for t in noticia.get('tickers', [])}
    resultado, fontes = [noticia], {noticia.get('source')}
    for candidata in noticias:
        if candidata is noticia or candidata.get('source') in fontes:
            continue
        comuns = chaves & palavras(candidata.get('title', ''))
        ativos = set(noticia.get('tickers', [])) & set(candidata.get('tickers', []))
        if len(comuns) >= 2 or ativos:
            resultado.append(candidata)
            fontes.add(candidata.get('source'))
        if len(resultado) == 3:
            break
    return resultado


def gerar_materias(noticias, caminho='materias.json', limite=2):
    """No máximo duas novas matérias por rodada; sem chave ou confirmação, não publica."""
    tem_ia = any(os.environ.get(f'GEMINI_API_KEY_{n}') for n in range(1, 6)) or os.environ.get('GROQ_API_KEY') or os.environ.get('OPENROUTER_API_KEY')
    if not tem_ia:
        print('Redação IA: nenhuma chave configurada; matérias completas ignoradas.')
        return []
    try:
        with open(caminho, 'r', encoding='utf-8') as arquivo:
            publicadas = json.load(arquivo)
    except (OSError, json.JSONDecodeError):
        publicadas = []
    existentes = {m.get('pauta_url') for m in publicadas}
    novas = []
    for noticia in noticias:
        if noticia.get('url') in existentes:
            continue
        fontes = fontes_convergentes(noticia, noticias)
        if len({f.get('source') for f in fontes}) < 2:
            continue
        try:
            artigo = gerar_artigo(noticia, fontes)
            if not 230 <= len(artigo['corpo'].split()) <= 750:
                raise ValueError('tamanho do texto fora da faixa permitida')
            novas.append({
                'id': f"materia-{abs(hash(noticia['url']))}", 'titulo': artigo['titulo'], 'corpo': artigo['corpo'],
                'categoria': noticia['cat'], 'time': noticia['time'], 'tickers': noticia.get('tickers', []),
                'pauta_url': noticia['url'], 'fontes': [{'nome': f['source'], 'url': f['url']} for f in fontes],
                'gerado_por': artigo['gerado_por'], 'gerado_em': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            })
            if len(novas) >= limite:
                break
        except Exception as erro:
            print(f"Redação IA: matéria bloqueada: {erro}")
    if novas:
        with open(caminho, 'w', encoding='utf-8') as arquivo:
            json.dump((novas + publicadas)[:50], arquivo, ensure_ascii=False, indent=2)
        print(f'Redação IA: {len(novas)} matéria(s) completa(s) criadas.')
    return novas
