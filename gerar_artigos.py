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

from redacao_automatica import gerar_materias

sys.stdout.reconfigure(encoding="utf-8")

QUANTIDADE = int(sys.argv[1]) if len(sys.argv) > 1 else 3


def carregar_json(caminho, padrao):
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    return padrao


def main():
    noticias = carregar_json("noticias.json", {"all": []})
    geradas = gerar_materias(noticias.get("all", []), limite=QUANTIDADE)
    print(f"\n{len(geradas)} matéria(s) criada(s) com confirmação em fontes independentes.")


if __name__ == "__main__":
    main()
