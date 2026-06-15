# -*- coding: utf-8 -*-
"""Gera materias proprias (via IA) a partir das noticias coletadas em noticias.json
e salva em artigos_pendentes.json para REVISAO MANUAL antes de publicar no site.

Nao altera noticias.json nem o site — apenas cria/atualiza artigos_pendentes.json.

Uso: GROQ_API_KEY=... GEMINI_API_KEY=... GEMINI_API_KEY_2=... python gerar_artigos.py [quantidade]
"""
import sys
import json
import os
from datetime import datetime, timezone

from ia_resumo import gerar_artigo

sys.stdout.reconfigure(encoding="utf-8")

QUANTIDADE = int(sys.argv[1]) if len(sys.argv) > 1 else 3


def carregar_json(caminho, padrao):
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    return padrao


def main():
    noticias = carregar_json("noticias.json", {"all": []})
    pendentes = carregar_json("artigos_pendentes.json", {})
    aprovados = carregar_json("artigos.json", {})

    candidatos = [n for n in noticias.get("all", []) if n["url"] not in pendentes and n["url"] not in aprovados]
    candidatos = candidatos[:QUANTIDADE]

    if not candidatos:
        print("Nenhuma noticia nova para gerar (todas ja tem artigo pendente ou aprovado).")
        return

    gerados = 0
    for n in candidatos:
        print(f"\nGerando artigo: {n['title']}")
        try:
            artigo = gerar_artigo(n)
        except Exception as e:
            print(f"  ERRO: {e}")
            continue

        pendentes[n["url"]] = {
            "titulo": artigo["titulo"],
            "corpo": artigo["corpo"],
            "fonte": n["source"],
            "fonte_url": n["url"],
            "title_original": n["title"],
            "time": n["time"],
            "cat": n["cat"],
            "tickers": n.get("tickers", []),
            "image": n.get("image"),
            "gerado_por": artigo["gerado_por"],
            "gerado_em": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        gerados += 1
        print(f"  OK ({artigo['gerado_por']}) -> {artigo['titulo']}")

    with open("artigos_pendentes.json", "w", encoding="utf-8") as f:
        json.dump(pendentes, f, ensure_ascii=False, indent=2)

    print(f"\n{gerados} artigo(s) novo(s) gerado(s). Total pendente: {len(pendentes)}")
    print("Revise artigos_pendentes.json e aprove os que estiverem bons.")


if __name__ == "__main__":
    main()
