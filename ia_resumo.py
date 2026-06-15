# -*- coding: utf-8 -*-
"""Modulo compartilhado: gera materias proprias a partir de noticias do coletor,
usando uma cadeia de provedores de IA gratuitos (com fallback automatico)."""
import os
import json
import time
import urllib.request
import urllib.error

USER_AGENT = "Mozilla/5.0 (compatible; BomDiaInvestidorBot/1.0)"


def _post_json(url, body, headers, max_tentativas=3):
    """POST generico com retry/backoff para erros 429/5xx ou falha de rede."""
    data = json.dumps(body).encode("utf-8")
    headers = {**headers, "Content-Type": "application/json", "User-Agent": USER_AGENT}
    for tentativa in range(1, max_tentativas + 1):
        req = urllib.request.Request(url, data=data, method="POST", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            corpo = e.read().decode("utf-8", errors="ignore")
            print(f"    tentativa {tentativa}/{max_tentativas} -> HTTP {e.code}: {corpo[:150]}")
            if e.code == 429 or e.code >= 500:
                time.sleep(2 ** tentativa)
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"    tentativa {tentativa}/{max_tentativas} -> erro de rede: {e}")
            time.sleep(2 ** tentativa)
            continue
    raise RuntimeError("provedor indisponivel apos varias tentativas")


def _chamar_groq(prompt, api_key, model):
    resp = _post_json(
        "https://api.groq.com/openai/v1/chat/completions",
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.6,
            "max_tokens": 2048,
            "response_format": {"type": "json_object"},
        },
        {"Authorization": f"Bearer {api_key}"},
    )
    return resp["choices"][0]["message"]["content"]


def _chamar_gemini(prompt, api_key, model):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    resp = _post_json(
        url,
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.6,
                "maxOutputTokens": 4096,
                "responseMimeType": "application/json",
                "thinkingConfig": {"thinkingBudget": 0},
            },
        },
        {},
    )
    return resp["candidates"][0]["content"]["parts"][0]["text"]


def _chamar_openrouter(prompt, api_key, model):
    resp = _post_json(
        "https://openrouter.ai/api/v1/chat/completions",
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.6,
            "max_tokens": 2048,
            "response_format": {"type": "json_object"},
        },
        {"Authorization": f"Bearer {api_key}"},
    )
    return resp["choices"][0]["message"]["content"]


# Cadeia de provedores: ordem = prioridade. Cada um so entra se a env var existir.
PROVEDORES = [
    {"nome": "Groq (Llama 3.3 70B)", "env": "GROQ_API_KEY", "fn": _chamar_groq, "model": "llama-3.3-70b-versatile"},
    {"nome": "Groq (Llama 3.1 8B)", "env": "GROQ_API_KEY", "fn": _chamar_groq, "model": "llama-3.1-8b-instant"},
    {"nome": "Gemini 2.5 Flash (chave 1)", "env": "GEMINI_API_KEY", "fn": _chamar_gemini, "model": "gemini-2.5-flash"},
    {"nome": "Gemini 2.5 Flash (chave 2)", "env": "GEMINI_API_KEY_2", "fn": _chamar_gemini, "model": "gemini-2.5-flash"},
    {"nome": "Gemini 2.0 Flash (chave 1)", "env": "GEMINI_API_KEY", "fn": _chamar_gemini, "model": "gemini-2.0-flash"},
    {"nome": "OpenRouter (Llama 3.3 70B free)", "env": "OPENROUTER_API_KEY", "fn": _chamar_openrouter, "model": "meta-llama/llama-3.3-70b-instruct:free"},
]


def gerar_com_fallback(prompt):
    erros = []
    for prov in PROVEDORES:
        api_key = os.environ.get(prov["env"], "")
        if not api_key:
            continue
        print(f"  -> tentando {prov['nome']}...")
        try:
            return prov["fn"](prompt, api_key, prov["model"]), prov["nome"]
        except Exception as e:
            print(f"     falhou: {e}")
            erros.append(f"{prov['nome']}: {e}")
    raise RuntimeError("Nenhum provedor de IA disponivel/funcionou.\n" + "\n".join(erros))


def montar_prompt(noticia):
    return f"""Voce e um redator senior do portal financeiro "Bom Dia Investidor", especializado em
mercado financeiro brasileiro. A partir da noticia abaixo, escreva uma MATERIA COMPLETA e ORIGINAL
(nao copie frases literais da fonte), em portugues do Brasil, tom jornalistico, claro e analitico.

Estrutura esperada (use os dados da noticia original como base, e complemente com contexto/explicacoes
geral de mercado que voce ja conhece — sem inventar numeros/dados especificos que nao estejam na
noticia original):

1. Lide: paragrafo de abertura respondendo o que aconteceu, com os principais numeros/fatos.
2. Contexto: o que motivou esse movimento (cenario macroeconomico, externo, politico etc.).
3. Detalhamento: desdobramentos, setores/ativos mais afetados, comparacoes com periodos recentes.
4. O que isso significa para o investidor: implicacoes praticas, pontos de atencao, o que observar
   nos proximos dias.
5. Fechamento: paragrafo de conclusao (NAO inclua a linha "Fonte" no corpo, isso e adicionado
   automaticamente pelo site).

Escreva pelo menos 6 paragrafos bem desenvolvidos (nao paragrafos de uma linha so). Nao use markdown,
apenas texto corrido separado por paragrafos.

Titulo original: {noticia['title']}
Resumo original: {noticia['summary']}

Responda em JSON com as chaves "titulo" (titulo novo e atrativo, pode ser parecido com o original) e
"corpo" (o texto completo reescrito, com os paragrafos separados por \\n\\n)."""


def gerar_artigo(noticia):
    """Recebe uma noticia (dict do coletor: title, summary, source, url, time, cat, tickers)
    e retorna {'titulo':..., 'corpo':...} ou levanta exception se todos os provedores falharem."""
    prompt = montar_prompt(noticia)
    raw, provedor = gerar_com_fallback(prompt)
    resultado = json.loads(raw)
    return {
        "titulo": resultado["titulo"].strip(),
        "corpo": resultado["corpo"].strip(),
        "gerado_por": provedor,
    }
