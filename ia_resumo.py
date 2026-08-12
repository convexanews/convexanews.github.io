# -*- coding: utf-8 -*-
"""Geração editorial com múltiplos provedores e regras contra cópia ou invenção de fatos."""
import json
import os
import time
import urllib.error
import urllib.request
import re

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
        "temperature": 0.2, "maxOutputTokens": 8192, "responseMimeType": "text/plain",
        "thinkingConfig": {"thinkingBudget": 0}
    }}, {})
    return resposta["candidates"][0]["content"]["parts"][0]["text"]


def _chamar_groq(prompt, chave, modelo):
    resposta = _post_json("https://api.groq.com/openai/v1/chat/completions", {
        "model": modelo, "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2, "max_tokens": 4096
    }, {"Authorization": f"Bearer {chave}"})
    return resposta["choices"][0]["message"]["content"]


def _chamar_openrouter(prompt, chave, modelo):
    resposta = _post_json("https://openrouter.ai/api/v1/chat/completions", {
        "model": modelo, "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2, "max_tokens": 4096
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
com base nos fatos disponíveis nas fontes abaixo.

Regras obrigatórias: não copie frases, estrutura ou detalhes exclusivos de uma fonte; não invente números,
declarações, datas ou causalidades; se houver mais de uma fonte, use somente os pontos convergentes;
não faça recomendação
de investimento. Diferencie fatos de contexto educativo e não mencione que recebeu textos de terceiros.

Escreva uma reportagem aprofundada de 700 a 1.100 palavras. Explique a abertura factual, o contexto doméstico,
o cenário externo, os ativos/setores afetados, os riscos e os próximos gatilhos. Use somente fatos presentes
nas fontes; quando faltar um dado, explique o mecanismo de mercado sem criar informação específica.

Tema: {noticia['title']}
Categoria: {noticia['cat']}
Ativos relacionados: {', '.join(noticia.get('tickers', [])) or 'não identificado'}

{texto_fontes}

Responda em TEXTO PURO e siga exatamente esta estrutura, sem markdown de código:
TÍTULO: título próprio
ABERTURA: parágrafo de abertura
## Contexto
parágrafo aprofundado
## Mercado e ativos afetados
parágrafo aprofundado
## Riscos e próximos gatilhos
parágrafo aprofundado
## Fechamento
parágrafo final."""


def _ler_resposta_editorial(bruto):
    """Lê um protocolo simples de texto, mais resistente que JSON em respostas longas."""
    limpo = re.sub(r'^```(?:text)?\s*|\s*```$', '', bruto.strip(), flags=re.IGNORECASE)
    linhas = limpo.splitlines()
    titulo, abertura, secoes, atual, partes = '', '', [], None, []
    for linha in linhas:
        texto = linha.strip()
        if (not titulo) and ':' in texto and not texto.startswith('#'):
            titulo = texto.split(':', 1)[1].strip()
        elif (not abertura) and ':' in texto and not texto.startswith('#'):
            abertura = texto.split(':', 1)[1].strip()
        elif texto.startswith('##'):
            if atual and partes:
                secoes.append({'titulo': atual, 'texto': '\n'.join(partes).strip()})
            atual, partes = texto.lstrip('#').strip(), []
        elif atual and texto:
            partes.append(texto)
    if atual and partes:
        secoes.append({'titulo': atual, 'texto': '\n'.join(partes).strip()})
    if not titulo or not abertura or len(secoes) < 3:
        raise ValueError('resposta da IA fora do formato editorial')
    fechamento = ''
    if secoes and secoes[-1]['titulo'].lower() == 'fechamento':
        fechamento = secoes.pop()['texto']
    return {"titulo": titulo, "abertura": abertura, "secoes": secoes, "fechamento": fechamento}


def gerar_artigo(noticia, fontes):
    """Produz reportagem própria inclusive quando só houver uma fonte confiável disponível."""
    prompt = montar_prompt(noticia, fontes)
    bruto, provedor = gerar_com_fallback(prompt)
    try:
        resultado = _ler_resposta_editorial(bruto)
    except Exception:
        bruto, provedor = gerar_com_fallback(prompt + '\nIMPORTANTE: responda no protocolo de texto completo solicitado, sem JSON e sem markdown de código.')
        resultado = _ler_resposta_editorial(bruto)
    secoes = [{"titulo": str(s.get("titulo", "")).strip(), "texto": str(s.get("texto", "")).strip()}
              for s in resultado["secoes"] if isinstance(s, dict) and s.get("titulo") and s.get("texto")]
    if len(secoes) < 3:
        raise ValueError('resposta da IA com seções vazias')
    return {"titulo": resultado["titulo"].strip(), "abertura": resultado["abertura"].strip(),
            "secoes": secoes, "fechamento": str(resultado.get("fechamento", "")).strip(), "gerado_por": provedor}
