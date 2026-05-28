import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import yfinance as yf
import pandas as pd
import json
import re
from datetime import datetime

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False
    print("⚠️  feedparser não instalado. Execute: pip install feedparser")

# ==================== ATIVOS ====================
ATIVOS_BR = {
    'PETR4': 'PETR4.SA', 'VALE3': 'VALE3.SA', 'ITUB4': 'ITUB4.SA',
    'BBDC4': 'BBDC4.SA', 'ABEV3': 'ABEV3.SA', 'WEGE3': 'WEGE3.SA',
    'RENT3': 'RENT3.SA', 'BBAS3': 'BBAS3.SA', 'MGLU3': 'MGLU3.SA',
    'SUZB3': 'SUZB3.SA', 'B3SA3': 'B3SA3.SA', 'RADL3': 'RADL3.SA',
    'LREN3': 'LREN3.SA', 'JBSS3': 'JBSS3.SA', 'ELET3': 'ELET3.SA',
}
FIIS = {
    'HGLG11': 'HGLG11.SA', 'XPLG11': 'XPLG11.SA', 'KNRI11': 'KNRI11.SA',
    'MXRF11': 'MXRF11.SA', 'VISC11': 'VISC11.SA', 'HGRE11': 'HGRE11.SA',
    'BCFF11': 'BCFF11.SA', 'IRDM11': 'IRDM11.SA', 'XPML11': 'XPML11.SA',
    'VILG11': 'VILG11.SA',
}
ETFS = {
    'BOVA11': 'BOVA11.SA', 'SMAL11': 'SMAL11.SA', 'IVVB11': 'IVVB11.SA',
    'HASH11': 'HASH11.SA', 'GOLD11': 'GOLD11.SA', 'DIVO11': 'DIVO11.SA',
    'XFIX11': 'XFIX11.SA', 'BOVV11': 'BOVV11.SA', 'NASD11': 'NASD11.SA',
    'SPXI11': 'SPXI11.SA', 'MATB11': 'MATB11.SA', 'TECK11': 'TECK11.SA',
}
ATIVOS_US = {
    'AAPL': 'AAPL', 'MSFT': 'MSFT', 'NVDA': 'NVDA',
    'GOOGL': 'GOOGL', 'AMZN': 'AMZN', 'META': 'META', 'TSLA': 'TSLA',
}
CRYPTOS = {
    'BTC': 'BTC-USD', 'ETH': 'ETH-USD', 'SOL': 'SOL-USD',
    'ADA': 'ADA-USD', 'XRP': 'XRP-USD',
}
INDICES = {
    'IBOV': '^BVSP',
    'SP500': '^GSPC',
    'NASDAQ': '^IXIC',
}

# ==================== RSS FEEDS ====================
RSS_FEEDS = [
    {'url': 'https://www.infomoney.com.br/feed/', 'source': 'InfoMoney', 'default_cat': 'acoes'},
    {'url': 'https://www.moneytimes.com.br/feed/', 'source': 'Money Times', 'default_cat': 'acoes'},
    {'url': 'https://www.suno.com.br/noticias/feed/', 'source': 'Suno', 'default_cat': 'acoes'},
    {'url': 'https://fiis.com.br/feed/', 'source': 'FIIs.com', 'default_cat': 'fundos'},
    {'url': 'https://exame.com/feed/', 'source': 'Exame', 'default_cat': 'economia'},
    {'url': 'https://www.cnnbrasil.com.br/economia/feed/', 'source': 'CNN Brasil', 'default_cat': 'economia'},
    {'url': 'https://br.investing.com/rss/news_25.rss', 'source': 'Investing.com', 'default_cat': 'internacional'},
]

PALAVRAS_CATEGORIA = {
    'fundos': ['fii', 'fundo imobiliário', 'fundo imobiliario', 'dividendo', 'dy ', 'cota', 'ifix', 'tijolo', 'papel cri', 'lci', 'lca', 'cri ', 'cra '],
    'cripto': ['bitcoin', 'btc', 'ethereum', 'eth', 'cripto', 'crypto', 'blockchain', 'solana', 'xrp', 'cardano', 'binance', 'altcoin'],
    'economia': ['selic', 'ipca', 'inflação', 'inflacao', 'dólar', 'dolar', 'juros', 'pib', 'banco central', 'copom', 'câmbio', 'cambio', 'fiscal', 'déficit', 'deficit', 'focus', 'ata ', 'ata do copom', 'tesouro direto', 'renda fixa', 'cdi ', 'cdi,', 'super-quarta', 'boletim'],
    'internacional': ['eua', 'wall street', 'fed ', 'nasdaq', 's&p 500', 'trump', 'china', 'europa', 'petróleo', 'petroleo', 'bolsas globais', 'dow jones', 'mercados externos', 'bolsa americana', 'banco central europeu'],
    'analise': ['carteira', 'recomendação', 'recomendacao', 'top picks', 'análise fundamentalista', 'relatório', 'relatorio', 'btg pactual', 'xp investimentos', 'morning call', 'genial', 'ágora investimentos', 'agora investimentos', 'price target', 'preço-alvo', 'rebaixamento', 'upgrade', 'downgrade'],
}

# Palavras que PRECISAM estar no título para ser considerada notícia financeira
PALAVRAS_FINANCEIRAS = [
    'ação', 'ações', 'acoes', 'acao', 'bolsa', 'ibovespa', 'b3', 'mercado', 'investimento',
    'fii', 'fundo', 'etf', 'bova11', 'dividendo', 'selic', 'ipca', 'inflação', 'inflacao',
    'dólar', 'dolar', 'juros', 'banco', 'carteira', 'recomendação', 'recomendacao',
    'bitcoin', 'cripto', 'crypto', 'btc', 'petrobras', 'vale3', 'itub', 'petr4',
    'resultado', 'lucro', 'receita', 'prejuízo', 'prejuizo', 'receita líquida',
    'cdi', 'tesouro', 'renda fixa', 'multimercado', 'gestora', 'corretora',
    'wall street', 'fed ', 'nasdaq', 'dow jones', 'sp500', 's&p',
    'petróleo', 'petroleo', 'minério', 'minerio', 'commodities', 'commodity',
    'copom', 'câmbio', 'cambio', 'pib ', 'fiscal', 'déficit', 'deficit',
    'pregão', 'pregao', 'abertura', 'fechamento', 'alta', 'queda', 'variação',
    'morning call', 'análise', 'analise', 'relatório', 'relatorio', 'preço-alvo',
    'ipo', 'oferta', 'follow-on', 'debenture', 'debênture', 'cra', 'cri',
]

def eh_noticia_financeira(title):
    tl = title.lower()
    return any(p in tl for p in PALAVRAS_FINANCEIRAS)

def classificar_noticia(title, default_cat='acoes'):
    tl = title.lower()
    for cat, palavras in PALAVRAS_CATEGORIA.items():
        if any(p in tl for p in palavras):
            return cat
    return default_cat

def tempo_relativo(published):
    try:
        if hasattr(published, 'tm_year'):
            pub_dt = datetime(*published[:6])
            diff = datetime.utcnow() - pub_dt
        else:
            return '1h'
        mins = int(diff.total_seconds() / 60)
        if mins < 1:
            return 'agora'
        if mins < 60:
            return f'{mins} min'
        if mins < 1440:
            h = mins // 60
            return f'{h}h'
        return f'{mins // 1440}d'
    except Exception:
        return '1h'

def limpar_html(texto):
    if not texto:
        return ''
    texto = re.sub(r'<[^>]+>', '', texto)
    # Remove artefatos comuns de RSS (ex: "The post ... appeared first on InfoMoney.")
    texto = re.sub(r'The post .{0,120} appeared first on .+?\.?$', '', texto, flags=re.IGNORECASE)
    texto = re.sub(r'&#\d+;', '', texto)
    texto = re.sub(r'&amp;', '&', texto)
    texto = re.sub(r'&lt;', '<', texto)
    texto = re.sub(r'&gt;', '>', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto[:220]

def coletar_noticias():
    if not HAS_FEEDPARSER:
        return []
    todas = []
    for feed_info in RSS_FEEDS:
        try:
            print(f"  📡 {feed_info['source']}...")
            feed = feedparser.parse(feed_info['url'])
            for entry in feed.entries[:10]:
                title = entry.get('title', '').strip()
                if not title:
                    continue
                url = entry.get('link', '')
                summary_raw = entry.get('summary', entry.get('description', entry.get('content', [{}])[0].get('value', '')))
                summary = limpar_html(summary_raw)
                published = entry.get('published_parsed', entry.get('updated_parsed'))
                # Descarta notícias fora do tema financeiro
                if not eh_noticia_financeira(title):
                    continue
                cat = classificar_noticia(title, feed_info['default_cat'])
                todas.append({
                    'title': title,
                    'summary': summary,
                    'source': feed_info['source'],
                    'url': url,
                    'time': tempo_relativo(published) if published else '1h',
                    'cat': cat,
                    'tickers': [],
                })
        except Exception as e:
            print(f"    ⚠️  Erro no feed {feed_info['source']}: {e}")

    # Remove duplicatas por título
    seen = set()
    unicas = []
    for n in todas:
        key = n['title'][:60]
        if key not in seen:
            seen.add(key)
            unicas.append(n)
    return unicas

def coletar_ativo(ticker_yf, nome_limpo, tipo='stock'):
    try:
        t = yf.Ticker(ticker_yf)
        hist = t.history(period='5d')
        if hist.empty:
            return None
        preco = round(float(hist['Close'].iloc[-1]), 2)
        preco_ant = float(hist['Close'].iloc[-2]) if len(hist) >= 2 else preco
        var_dia = round(((preco / preco_ant) - 1) * 100, 2) if preco_ant else 0.0
        volume = int(hist['Volume'].iloc[-1]) if 'Volume' in hist.columns else 0

        info = {}
        try:
            info = t.info or {}
        except Exception:
            pass

        return {
            'stock': nome_limpo,
            'name': info.get('longName', info.get('shortName', nome_limpo)),
            'close': preco,
            'change': var_dia,
            'volume': volume,
            'market_cap': info.get('marketCap', 0) or 0,
            'sector': info.get('sector', info.get('category', tipo.upper())),
            'type': tipo,
        }
    except Exception as e:
        print(f"    ⚠️  Erro em {ticker_yf}: {e}")
        return None

def coletar_indice(ticker_yf, nome):
    try:
        t = yf.Ticker(ticker_yf)
        hist = t.history(period='3d')
        if hist.empty:
            return None
        preco = round(float(hist['Close'].iloc[-1]), 2)
        preco_ant = float(hist['Close'].iloc[-2]) if len(hist) >= 2 else preco
        var = round(((preco / preco_ant) - 1) * 100, 2) if preco_ant else 0.0
        return {'stock': nome, 'close': preco, 'change': var}
    except Exception as e:
        print(f"    ⚠️  Erro no índice {nome}: {e}")
        return None

# ==================== MAIN ====================
print("🚀 Iniciando coleta de dados Convexa News...\n")

dados = {
    'stocks': {},
    'fiis': {},
    'etfs': {},
    'us_stocks': {},
    'crypto': {},
    'indices': {},
    'dolar': {},
    'atualizado_em': '',
}

print("📈 Coletando ações BR...")
for nome, ticker in ATIVOS_BR.items():
    print(f"  {nome}...", end=' ')
    r = coletar_ativo(ticker, nome, 'stock')
    if r:
        dados['stocks'][nome] = r
        print(f"R$ {r['close']} ({r['change']:+.2f}%)")
    else:
        print("falhou")

print("\n🏢 Coletando FIIs...")
for nome, ticker in FIIS.items():
    print(f"  {nome}...", end=' ')
    r = coletar_ativo(ticker, nome, 'fii')
    if r:
        dados['fiis'][nome] = r
        print(f"R$ {r['close']} ({r['change']:+.2f}%)")
    else:
        print("falhou")

print("\n📊 Coletando ETFs...")
for nome, ticker in ETFS.items():
    print(f"  {nome}...", end=' ')
    r = coletar_ativo(ticker, nome, 'etf')
    if r:
        dados['etfs'][nome] = r
        print(f"R$ {r['close']} ({r['change']:+.2f}%)")
    else:
        print("falhou")

print("\n🌎 Coletando ações EUA...")
for nome, ticker in ATIVOS_US.items():
    print(f"  {nome}...", end=' ')
    r = coletar_ativo(ticker, nome, 'us')
    if r:
        dados['us_stocks'][nome] = r
        print(f"US$ {r['close']} ({r['change']:+.2f}%)")
    else:
        print("falhou")

print("\n🪙 Coletando criptos...")
for nome, ticker in CRYPTOS.items():
    print(f"  {nome}...", end=' ')
    r = coletar_ativo(ticker, nome, 'crypto')
    if r:
        dados['crypto'][nome] = r
        print(f"US$ {r['close']} ({r['change']:+.2f}%)")
    else:
        print("falhou")

print("\n📉 Coletando índices e dólar...")
for nome, ticker in INDICES.items():
    r = coletar_indice(ticker, nome)
    if r:
        dados['indices'][nome] = r
        print(f"  {nome}: {r['close']} ({r['change']:+.2f}%)")

try:
    d = yf.Ticker('USDBRL=X')
    hist_d = d.history(period='3d')
    if not hist_d.empty:
        pd_val = round(float(hist_d['Close'].iloc[-1]), 4)
        pd_ant = float(hist_d['Close'].iloc[-2]) if len(hist_d) >= 2 else pd_val
        dados['dolar'] = {
            'stock': 'USD/BRL',
            'close': pd_val,
            'change': round(((pd_val / pd_ant) - 1) * 100, 2),
        }
        print(f"  USD/BRL: {pd_val}")
except Exception as e:
    print(f"  ⚠️  Dólar: {e}")

dados['atualizado_em'] = datetime.now().strftime('%d/%m/%Y %H:%M')

with open('dados.json', 'w', encoding='utf-8') as f:
    json.dump(dados, f, ensure_ascii=False, indent=2)

total = sum(len(v) for k, v in dados.items() if isinstance(v, dict) and k not in ('indices', 'dolar'))
print(f"\n✅ dados.json salvo — {total} ativos + índices")

# ==================== NOTÍCIAS ====================
print("\n📰 Coletando notícias via RSS...")
noticias_raw = coletar_noticias()

if noticias_raw:
    noticias_json = {
        'headline': noticias_raw[0],
        'featured': noticias_raw[1:3],
        'all': noticias_raw,
        'atualizado_em': datetime.now().strftime('%d/%m/%Y %H:%M'),
    }
    with open('noticias.json', 'w', encoding='utf-8') as f:
        json.dump(noticias_json, f, ensure_ascii=False, indent=2)
    print(f"✅ noticias.json salvo — {len(noticias_raw)} notícias")
else:
    print("⚠️  Nenhuma notícia coletada. Mantendo noticias.json anterior (se existir).")

print("\n🎉 Atualização concluída com sucesso!")
