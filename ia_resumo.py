# -*- coding: utf-8 -*-
"""Geração editorial com múltiplos provedores e regras contra cópia ou invenção de fatos."""
import json
import os
import time
import urllib.error
import urllib.request

USER_AGENT = "Mozilla/5.0 (compatible; BomDiaInvestidor/1.0)"


def _post_json(url, body, headers, max_tentativas=3):
    data = json.dumps(body).encode("utf-8")
    headers = {**headers, "Content-Type": "application/json", "User-Agent": USER_AGENT}
    for tentativa in range(1, max_tentativas + 1):
        try:
            req = urllib.request.Request(url, data=data, method="POST", headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as erro:
            if erro.code != 429 and erro.code < 500:
                raise
            print(f"    tentativa {tentativa}: HTTP {erro.code}")
        except (urllib.error.URLError, TimeoutError) as erro:
            print(f"    tentativa {tentativa}: {erro}")
        time.sleep(2 ** tentativa)
    raise RuntimeError("provedor indisponível após várias tentativas")


def _chamar_gemini(prompt, chave, modelo):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={chave}"
    resposta = _post_json(url, {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {
        "temperature": 0.3, "maxOutputTokens": 3000, "responseMimeType": "application/json"
    }}, {})
    return resposta["candidates"][0]["content"]["parts"][0]["text"]


def _chamar_groq(prompt, chave, modelo):
    resposta = _post_json("https://api.groq.com/openai/v1/chat/completions", {
        "model": modelo, "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3, "max_tokens": 3000, "response_format": {"type": "json_object"}
    }, {"Authorization": f"Bearer {chave}"})
    return resposta["choices"][0]["message"]["content"]


def _chamar_openrouter(prompt, chave, modelo):
    resposta = _post_json("https://openrouter.ai/api/v1/chat/completions", {
        "model": modelo, "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3, "max_tokens": 3000, "response_format": {"type": "json_object"}
    }, {"Authorization": f"Bearer {chave}"})
    return resposta["choices"][0]["message"]["content"]


# Cinco chaves Gemini independentes; a próxima só é usada se a anterior falhar ou atingir o limite.
PROVEDORES = [
    *[{"nome": f"Gemini Flash (chave {n})", "env": f"GEMINI_API_KEY_{n}", "fn": _chamar_gemini,
       "model": "gemini-2.5-flash"} for n in range(1, 6)],
    {"nome": "Groq", "env": "GROQ_API_KEY", "fn": _chamar_groq, "model": "llama-3.3-70b-versatile"},
    {"nome": "OpenRouter", "env": "OPENROUTER_API_KEY", "fn": _chamar_openrouter,
     "model": "meta-llama/llama-3.3-70b-instruct:free"},
]


def gerar_com_fallback(prompt):
    erros = []
    for provedor in PROVEDORES:
        chave = os.environ.get(provedor["env"], "")
        if not chave:
            continue
        try:
            print(f"  -> tentando {provedor['nome']}...")
            return provedor["fn"](prompt, chave, provedor["model"]), provedor["nome"]
        except Exception as erro:
            erros.append(f"{provedor['nome']}: {erro}")
    raise RuntimeError("Nenhum provedor de IA disponível. " + " | ".join(erros))


def montar_prompt(noticia, fontes):
    texto_fontes = "\n\n".join(
        f"FONTE {i + 1} ({fonte['source']}): {fonte['title']}\nFatos disponíveis: {fonte['summary']}"
        for i, fonte in enumerate(fontes)
    )
    return f"""Você é editor do Bom Dia Investidor. Produza uma matéria financeira original, em português do Brasil,
com base apenas nos fatos convergentes das fontes abaixo.

Regras obrigatórias: não copie frases, estrutura ou detalhes exclusivos de uma fonte; não invente números,
declarações, datas ou causalidades; descarte qualquer ponto em que as fontes divirjam; não faça recomendação
de investimento. Diferencie fatos de contexto educativo e não mencione que recebeu textos de terceiros.

Estrutura: título próprio; abertura factual; contexto; impacto para o investidor; o que acompanhar; fechamento.
Escreva 4 a 6 parágrafos, entre 280 e 650 palavras, sem markdown.

Tema: {noticia['title']}
Categoria: {noticia['cat']}
Ativos relacionados: {', '.join(noticia.get('tickers', [])) or 'não identificado'}

{texto_fontes}

Responda em JSON com as chaves "titulo" e "corpo"."""


def gerar_artigo(noticia, fontes):
    """Só produz texto quando houver pelo menos duas fontes independentes."""
    if len({fonte.get('source') for fonte in fontes if fonte.get('source')}) < 2:
        raise ValueError("Matéria bloqueada: são necessárias duas fontes independentes.")
    bruto, provedor = gerar_com_fallback(montar_prompt(noticia, fontes))
    resultado = json.loads(bruto)
    return {"titulo": resultado["titulo"].strip(), "corpo": resultado["corpo"].strip(), "gerado_por": provedor}
