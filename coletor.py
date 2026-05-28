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

# ==================== AÇÕES BR (por setor) ====================
ATIVOS_BR = {
    # Petróleo & Gás
    'PETR4': 'PETR4.SA', 'PETR3': 'PETR3.SA', 'PRIO3': 'PRIO3.SA',
    'RECV3': 'RECV3.SA', 'CSAN3': 'CSAN3.SA', 'UGPA3': 'UGPA3.SA',
    'VBBR3': 'VBBR3.SA', 'RRRP3': 'RRRP3.SA', 'BRAP4': 'BRAP4.SA',
    # Mineração & Siderurgia
    'VALE3': 'VALE3.SA', 'CSNA3': 'CSNA3.SA', 'GGBR4': 'GGBR4.SA',
    'USIM5': 'USIM5.SA', 'CMIN3': 'CMIN3.SA', 'GOAU4': 'GOAU4.SA',
    # Bancos
    'ITUB4': 'ITUB4.SA', 'ITUB3': 'ITUB3.SA', 'BBDC4': 'BBDC4.SA',
    'BBDC3': 'BBDC3.SA', 'BBAS3': 'BBAS3.SA', 'SANB11': 'SANB11.SA',
    'BPAC11': 'BPAC11.SA', 'BRSR6': 'BRSR6.SA', 'BMGB4': 'BMGB4.SA',
    # Financeiro & Seguros
    'B3SA3': 'B3SA3.SA', 'CIEL3': 'CIEL3.SA', 'IRBR3': 'IRBR3.SA',
    'TRAD3': 'TRAD3.SA', 'BBSE3': 'BBSE3.SA', 'PSSA3': 'PSSA3.SA',
    # Energia Elétrica
    'ELET3': 'ELET3.SA', 'ELET6': 'ELET6.SA', 'CPFE3': 'CPFE3.SA',
    'ENGI11': 'ENGI11.SA', 'EGIE3': 'EGIE3.SA', 'TAEE11': 'TAEE11.SA',
    'ENEV3': 'ENEV3.SA', 'CMIG4': 'CMIG4.SA', 'AESB3': 'AESB3.SA',
    'NEOE3': 'NEOE3.SA', 'ALUP11': 'ALUP11.SA', 'EQTL3': 'EQTL3.SA',
    # Saneamento
    'SBSP3': 'SBSP3.SA', 'CSMG3': 'CSMG3.SA',
    # Telecom
    'VIVT3': 'VIVT3.SA', 'TIMS3': 'TIMS3.SA',
    # Varejo & Consumo
    'MGLU3': 'MGLU3.SA', 'LREN3': 'LREN3.SA', 'SOMA3': 'SOMA3.SA',
    'ARZZ3': 'ARZZ3.SA', 'NTCO3': 'NTCO3.SA', 'AMAR3': 'AMAR3.SA',
    'CEAB3': 'CEAB3.SA', 'GMAT3': 'GMAT3.SA', 'PETZ3': 'PETZ3.SA',
    'SBFG3': 'SBFG3.SA',
    # Bebidas & Alimentos
    'ABEV3': 'ABEV3.SA',
    # Frigoríficos
    'JBSS3': 'JBSS3.SA', 'MRFG3': 'MRFG3.SA', 'BEEF3': 'BEEF3.SA',
    'BRFS3': 'BRFS3.SA',
    # Agronegócio
    'SLCE3': 'SLCE3.SA', 'AGRO3': 'AGRO3.SA', 'SMTO3': 'SMTO3.SA',
    'TTEN3': 'TTEN3.SA',
    # Saúde
    'RDOR3': 'RDOR3.SA', 'HAPV3': 'HAPV3.SA', 'FLRY3': 'FLRY3.SA',
    'DASA3': 'DASA3.SA', 'RADL3': 'RADL3.SA', 'ODPV3': 'ODPV3.SA',
    # Construção Civil
    'CYRE3': 'CYRE3.SA', 'MRVE3': 'MRVE3.SA', 'EZTC3': 'EZTC3.SA',
    'JHSF3': 'JHSF3.SA', 'MDNE3': 'MDNE3.SA', 'DIRR3': 'DIRR3.SA',
    'TEND3': 'TEND3.SA', 'LAVV3': 'LAVV3.SA',
    # Shopping / Imobiliário
    'MULT3': 'MULT3.SA', 'IGTI11': 'IGTI11.SA',
    # Logística & Transporte
    'RAIL3': 'RAIL3.SA', 'ECOR3': 'ECOR3.SA', 'POMO4': 'POMO4.SA',
    'TGMA3': 'TGMA3.SA', 'LOGN3': 'LOGN3.SA',
    # Aeroespacial
    'EMBR3': 'EMBR3.SA',
    # Locação & Serviços
    'RENT3': 'RENT3.SA', 'MOVI3': 'MOVI3.SA', 'HBSA3': 'HBSA3.SA',
    # Papel & Celulose
    'SUZB3': 'SUZB3.SA', 'KLBN11': 'KLBN11.SA',
    # Tecnologia
    'TOTS3': 'TOTS3.SA', 'LWSA3': 'LWSA3.SA', 'CASH3': 'CASH3.SA',
    'INTB3': 'INTB3.SA', 'MLAS3': 'MLAS3.SA',
    # Educação
    'COGN3': 'COGN3.SA', 'YDUQ3': 'YDUQ3.SA', 'SEER3': 'SEER3.SA',
    # Industrial
    'WEGE3': 'WEGE3.SA', 'RAIZ4': 'RAIZ4.SA',
}

# Setor hardcoded para evitar chamadas lentas de t.info
SETOR_BR = {
    'PETR4': 'Energy', 'PETR3': 'Energy', 'PRIO3': 'Energy', 'RECV3': 'Energy',
    'CSAN3': 'Energy', 'UGPA3': 'Energy', 'VBBR3': 'Energy', 'RRRP3': 'Energy', 'BRAP4': 'Basic Materials',
    'VALE3': 'Basic Materials', 'CSNA3': 'Basic Materials', 'GGBR4': 'Basic Materials',
    'USIM5': 'Basic Materials', 'CMIN3': 'Basic Materials', 'GOAU4': 'Basic Materials',
    'KLBN11': 'Basic Materials', 'SUZB3': 'Basic Materials',
    'ITUB4': 'Financial Services', 'ITUB3': 'Financial Services', 'BBDC4': 'Financial Services',
    'BBDC3': 'Financial Services', 'BBAS3': 'Financial Services', 'SANB11': 'Financial Services',
    'BPAC11': 'Financial Services', 'BRSR6': 'Financial Services', 'BMGB4': 'Financial Services',
    'B3SA3': 'Financial Services', 'CIEL3': 'Financial Services', 'IRBR3': 'Financial Services',
    'TRAD3': 'Financial Services', 'BBSE3': 'Financial Services', 'PSSA3': 'Financial Services',
    'ELET3': 'Utilities', 'ELET6': 'Utilities', 'CPFE3': 'Utilities', 'ENGI11': 'Utilities',
    'EGIE3': 'Utilities', 'TAEE11': 'Utilities', 'ENEV3': 'Utilities', 'CMIG4': 'Utilities',
    'AESB3': 'Utilities', 'NEOE3': 'Utilities', 'ALUP11': 'Utilities', 'EQTL3': 'Utilities',
    'SBSP3': 'Utilities', 'CSMG3': 'Utilities',
    'VIVT3': 'Communication Services', 'TIMS3': 'Communication Services',
    'ABEV3': 'Consumer Defensive', 'BRFS3': 'Consumer Defensive',
    'JBSS3': 'Consumer Defensive', 'MRFG3': 'Consumer Defensive', 'BEEF3': 'Consumer Defensive',
    'SLCE3': 'Consumer Defensive', 'AGRO3': 'Consumer Defensive', 'SMTO3': 'Consumer Defensive', 'TTEN3': 'Consumer Defensive',
    'MGLU3': 'Consumer Cyclical', 'LREN3': 'Consumer Cyclical', 'SOMA3': 'Consumer Cyclical',
    'ARZZ3': 'Consumer Cyclical', 'NTCO3': 'Consumer Cyclical', 'AMAR3': 'Consumer Cyclical',
    'CEAB3': 'Consumer Cyclical', 'GMAT3': 'Consumer Cyclical', 'PETZ3': 'Consumer Cyclical', 'SBFG3': 'Consumer Cyclical',
    'COGN3': 'Consumer Cyclical', 'YDUQ3': 'Consumer Cyclical', 'SEER3': 'Consumer Cyclical',
    'MULT3': 'Real Estate', 'IGTI11': 'Real Estate',
    'CYRE3': 'Real Estate', 'MRVE3': 'Real Estate', 'EZTC3': 'Real Estate',
    'JHSF3': 'Real Estate', 'MDNE3': 'Real Estate', 'DIRR3': 'Real Estate',
    'TEND3': 'Real Estate', 'LAVV3': 'Real Estate',
    'RDOR3': 'Healthcare', 'HAPV3': 'Healthcare', 'FLRY3': 'Healthcare',
    'DASA3': 'Healthcare', 'RADL3': 'Healthcare', 'ODPV3': 'Healthcare',
    'RAIL3': 'Industrials', 'ECOR3': 'Industrials', 'POMO4': 'Industrials',
    'TGMA3': 'Industrials', 'LOGN3': 'Industrials', 'EMBR3': 'Industrials',
    'RENT3': 'Industrials', 'MOVI3': 'Industrials', 'HBSA3': 'Industrials',
    'WEGE3': 'Industrials', 'RAIZ4': 'Industrials',
    'TOTS3': 'Technology', 'LWSA3': 'Technology', 'CASH3': 'Technology',
    'INTB3': 'Technology', 'MLAS3': 'Technology',
}

# ==================== FIIs (por categoria) ====================
FIIS = {
    # Galpões Logísticos
    'HGLG11': 'HGLG11.SA', 'XPLG11': 'XPLG11.SA', 'VILG11': 'VILG11.SA',
    'BRCO11': 'BRCO11.SA', 'GLOG11': 'GLOG11.SA', 'ALZR11': 'ALZR11.SA',
    'LVBI11': 'LVBI11.SA', 'GGRC11': 'GGRC11.SA', 'PATL11': 'PATL11.SA',
    'BTLG11': 'BTLG11.SA', 'VGIP11': 'VGIP11.SA', 'SDIL11': 'SDIL11.SA',
    'TRXF11': 'TRXF11.SA', 'JRDM11': 'JRDM11.SA',
    # Shoppings
    'VISC11': 'VISC11.SA', 'XPML11': 'XPML11.SA', 'HSML11': 'HSML11.SA',
    'MALL11': 'MALL11.SA', 'BPML11': 'BPML11.SA', 'ATSA11': 'ATSA11.SA',
    'FVPQ11': 'FVPQ11.SA',
    # Lajes Corporativas
    'HGRE11': 'HGRE11.SA', 'BRCR11': 'BRCR11.SA', 'RCRB11': 'RCRB11.SA',
    'PATC11': 'PATC11.SA', 'PVBI11': 'PVBI11.SA', 'VINO11': 'VINO11.SA',
    'JSRE11': 'JSRE11.SA', 'TGAR11': 'TGAR11.SA', 'BBPO11': 'BBPO11.SA',
    # Papel / CRI
    'MXRF11': 'MXRF11.SA', 'IRDM11': 'IRDM11.SA', 'KNCR11': 'KNCR11.SA',
    'KNHY11': 'KNHY11.SA', 'MCCI11': 'MCCI11.SA', 'VRTA11': 'VRTA11.SA',
    'HABT11': 'HABT11.SA', 'RECR11': 'RECR11.SA', 'VGIR11': 'VGIR11.SA',
    'CPTS11': 'CPTS11.SA', 'KNIP11': 'KNIP11.SA', 'RBRR11': 'RBRR11.SA',
    'OUJP11': 'OUJP11.SA', 'HCTR11': 'HCTR11.SA',
    # Fundo de Fundos
    'BCFF11': 'BCFF11.SA', 'RBFF11': 'RBFF11.SA', 'HFOF11': 'HFOF11.SA',
    'TFOF11': 'TFOF11.SA', 'FUND11': 'FUND11.SA',
    # Residencial
    'BLMG11': 'BLMG11.SA', 'RBVA11': 'RBVA11.SA', 'RZAK11': 'RZAK11.SA',
    # Híbrido / Diversificado
    'KNRI11': 'KNRI11.SA', 'HGPO11': 'HGPO11.SA', 'BTRA11': 'BTRA11.SA',
    'RBRP11': 'RBRP11.SA', 'VVPR11': 'VVPR11.SA',
}

# ==================== ETFs ====================
ETFS = {
    # Renda Variável BR
    'BOVA11': 'BOVA11.SA', 'SMAL11': 'SMAL11.SA', 'BOVV11': 'BOVV11.SA',
    'DIVO11': 'DIVO11.SA', 'FIND11': 'FIND11.SA', 'FNAM11': 'FNAM11.SA',
    'BBSD11': 'BBSD11.SA', 'ISUS11': 'ISUS11.SA', 'ECOO11': 'ECOO11.SA',
    # Internacional
    'IVVB11': 'IVVB11.SA', 'NASD11': 'NASD11.SA', 'SPXI11': 'SPXI11.SA',
    'ACWI11': 'ACWI11.SA', 'EURP11': 'EURP11.SA', 'USAI11': 'USAI11.SA',
    # Temáticos
    'HASH11': 'HASH11.SA', 'GOLD11': 'GOLD11.SA', 'MATB11': 'MATB11.SA',
    'TECK11': 'TECK11.SA', 'AGRI11': 'AGRI11.SA', 'NFNX11': 'NFNX11.SA',
    # Renda Fixa
    'IMAB11': 'IMAB11.SA', 'IRFM11': 'IRFM11.SA', 'B5P211': 'B5P211.SA',
    'FIXA11': 'FIXA11.SA', 'XFIX11': 'XFIX11.SA',
}

# ==================== Ações EUA ====================
ATIVOS_US = {
    # Mega Cap Tech
    'AAPL': 'AAPL', 'MSFT': 'MSFT', 'NVDA': 'NVDA', 'GOOGL': 'GOOGL',
    'AMZN': 'AMZN', 'META': 'META', 'TSLA': 'TSLA',
    # Semicondutores
    'AMD': 'AMD', 'INTC': 'INTC', 'AVGO': 'AVGO', 'QCOM': 'QCOM',
    'TSM': 'TSM', 'MU': 'MU', 'ARM': 'ARM',
    # Software / Cloud
    'ORCL': 'ORCL', 'CRM': 'CRM', 'ADBE': 'ADBE', 'NOW': 'NOW',
    'SNOW': 'SNOW', 'PLTR': 'PLTR', 'UBER': 'UBER',
    # Finanças
    'JPM': 'JPM', 'BAC': 'BAC', 'GS': 'GS', 'MS': 'MS',
    'V': 'V', 'MA': 'MA', 'AXP': 'AXP', 'BRK-B': 'BRK-B',
    # Saúde
    'JNJ': 'JNJ', 'UNH': 'UNH', 'PFE': 'PFE', 'ABBV': 'ABBV',
    'MRK': 'MRK', 'LLY': 'LLY', 'AMGN': 'AMGN',
    # Energia
    'XOM': 'XOM', 'CVX': 'CVX',
    # Consumo
    'WMT': 'WMT', 'COST': 'COST', 'KO': 'KO', 'PEP': 'PEP',
    'MCD': 'MCD', 'DIS': 'DIS', 'SBUX': 'SBUX', 'NKE': 'NKE',
    'HD': 'HD', 'NFLX': 'NFLX',
    # Industrial
    'CAT': 'CAT', 'BA': 'BA', 'GE': 'GE', 'RTX': 'RTX', 'DE': 'DE',
    # Telecom
    'VZ': 'VZ', 'T': 'T',
}

CRYPTOS = {
    'BTC': 'BTC-USD', 'ETH': 'ETH-USD', 'SOL': 'SOL-USD',
    'ADA': 'ADA-USD', 'XRP': 'XRP-USD', 'BNB': 'BNB-USD', 'DOGE': 'DOGE-USD',
}

INDICES = {
    'IBOV': '^BVSP',
    'SP500': '^GSPC',
    'NASDAQ': '^IXIC',
    'DOW': '^DJI',
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
    'economia': ['selic', 'ipca', 'inflação', 'inflacao', 'dólar', 'dolar', 'juros', 'pib', 'banco central', 'copom', 'câmbio', 'cambio', 'fiscal', 'déficit', 'deficit', 'focus', 'tesouro direto', 'renda fixa', 'cdi', 'super-quarta', 'boletim'],
    'internacional': ['eua', 'wall street', 'fed ', 'nasdaq', 's&p 500', 'trump', 'china', 'europa', 'petróleo', 'petroleo', 'bolsas globais', 'dow jones', 'mercados externos', 'bolsa americana'],
    'analise': ['carteira', 'recomendação', 'recomendacao', 'top picks', 'análise fundamentalista', 'relatório', 'relatorio', 'btg pactual', 'xp investimentos', 'morning call', 'price target', 'preço-alvo', 'rebaixamento', 'upgrade', 'downgrade'],
}

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
        if mins < 1: return 'agora'
        if mins < 60: return f'{mins} min'
        if mins < 1440: return f'{mins // 60}h'
        return f'{mins // 1440}d'
    except Exception:
        return '1h'

def limpar_html(texto):
    if not texto: return ''
    texto = re.sub(r'<[^>]+>', '', texto)
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
            print(f"  RSS {feed_info['source']}...")
            feed = feedparser.parse(feed_info['url'])
            for entry in feed.entries[:10]:
                title = entry.get('title', '').strip()
                if not title or not eh_noticia_financeira(title):
                    continue
                url = entry.get('link', '')
                summary_raw = entry.get('summary', entry.get('description', ''))
                summary = limpar_html(summary_raw)
                published = entry.get('published_parsed', entry.get('updated_parsed'))
                cat = classificar_noticia(title, feed_info['default_cat'])
                todas.append({
                    'title': title, 'summary': summary,
                    'source': feed_info['source'], 'url': url,
                    'time': tempo_relativo(published) if published else '1h',
                    'cat': cat, 'tickers': [],
                })
        except Exception as e:
            print(f"    Erro {feed_info['source']}: {e}")
    seen = set()
    unicas = []
    for n in todas:
        key = n['title'][:60]
        if key not in seen:
            seen.add(key)
            unicas.append(n)
    return unicas

# ==================== COLETA EM BATCH (rápido) ====================
def coletar_batch(ativos_dict, tipo, setor_map=None):
    """Baixa preços de todos os tickers de uma vez com yf.download()."""
    if not ativos_dict:
        return {}

    nomes_map = {v: k for k, v in ativos_dict.items()}
    tickers = list(ativos_dict.values())
    resultado = {}

    try:
        raw = yf.download(
            tickers if len(tickers) > 1 else tickers[0],
            period='5d',
            auto_adjust=True,
            progress=False,
            threads=True,
        )

        # Normaliza para DataFrame com colunas = tickers
        if len(tickers) == 1:
            close_df = pd.DataFrame({tickers[0]: raw['Close']})
            vol_df = pd.DataFrame({tickers[0]: raw.get('Volume', pd.Series(dtype=float))})
        else:
            close_df = raw['Close'] if 'Close' in raw.columns else raw
            vol_df = raw['Volume'] if 'Volume' in raw.columns else pd.DataFrame()

        for ticker_yf in tickers:
            nome = nomes_map.get(ticker_yf, ticker_yf)
            if ticker_yf not in close_df.columns:
                continue
            col = close_df[ticker_yf].dropna()
            if len(col) < 1:
                continue
            preco = round(float(col.iloc[-1]), 2)
            preco_ant = float(col.iloc[-2]) if len(col) >= 2 else preco
            var = round(((preco / preco_ant) - 1) * 100, 2)
            vol = 0
            if ticker_yf in vol_df.columns:
                try:
                    vol = int(vol_df[ticker_yf].dropna().iloc[-1])
                except Exception:
                    pass
            setor = (setor_map or {}).get(nome, '')
            resultado[nome] = {
                'stock': nome,
                'name': nome,
                'close': preco,
                'change': var,
                'volume': vol,
                'market_cap': 0,
                'sector': setor,
                'type': tipo,
            }
    except Exception as e:
        print(f"  Batch falhou ({tipo}): {e}. Tentando individual...")
        for nome, ticker in ativos_dict.items():
            try:
                t = yf.Ticker(ticker)
                hist = t.history(period='5d')
                if hist.empty:
                    continue
                preco = round(float(hist['Close'].iloc[-1]), 2)
                preco_ant = float(hist['Close'].iloc[-2]) if len(hist) >= 2 else preco
                var = round(((preco / preco_ant) - 1) * 100, 2)
                resultado[nome] = {
                    'stock': nome, 'name': nome, 'close': preco, 'change': var,
                    'volume': int(hist['Volume'].iloc[-1]) if 'Volume' in hist.columns else 0,
                    'market_cap': 0,
                    'sector': (setor_map or {}).get(nome, ''),
                    'type': tipo,
                }
            except Exception:
                pass

    return resultado

def coletar_indice(ticker_yf, nome):
    try:
        t = yf.Ticker(ticker_yf)
        hist = t.history(period='3d')
        if hist.empty:
            return None
        preco = round(float(hist['Close'].iloc[-1]), 2)
        preco_ant = float(hist['Close'].iloc[-2]) if len(hist) >= 2 else preco
        var = round(((preco / preco_ant) - 1) * 100, 2)
        return {'stock': nome, 'close': preco, 'change': var}
    except Exception as e:
        print(f"  Erro indice {nome}: {e}")
        return None

# ==================== MAIN ====================
print("Iniciando coleta Convexa News...\n")

dados = {
    'stocks': {}, 'fiis': {}, 'etfs': {},
    'us_stocks': {}, 'crypto': {}, 'indices': {}, 'dolar': {},
    'atualizado_em': '',
}

print(f"Acoes BR ({len(ATIVOS_BR)} tickers)...")
dados['stocks'] = coletar_batch(ATIVOS_BR, 'stock', SETOR_BR)
print(f"  OK: {len(dados['stocks'])} ativos")

print(f"FIIs ({len(FIIS)} tickers)...")
dados['fiis'] = coletar_batch(FIIS, 'fii')
print(f"  OK: {len(dados['fiis'])} FIIs")

print(f"ETFs ({len(ETFS)} tickers)...")
dados['etfs'] = coletar_batch(ETFS, 'etf')
print(f"  OK: {len(dados['etfs'])} ETFs")

print(f"Acoes EUA ({len(ATIVOS_US)} tickers)...")
dados['us_stocks'] = coletar_batch(ATIVOS_US, 'us')
print(f"  OK: {len(dados['us_stocks'])} ativos")

print(f"Criptos ({len(CRYPTOS)} tickers)...")
dados['crypto'] = coletar_batch(CRYPTOS, 'crypto')
print(f"  OK: {len(dados['crypto'])} criptos")

print("Indices e dolar...")
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
    print(f"  Dolar: {e}")

dados['atualizado_em'] = datetime.now().strftime('%d/%m/%Y %H:%M')

with open('dados.json', 'w', encoding='utf-8') as f:
    json.dump(dados, f, ensure_ascii=False, indent=2)

total = sum(len(v) for k, v in dados.items() if isinstance(v, dict) and k not in ('indices', 'dolar'))
print(f"\ndados.json salvo — {total} ativos coletados")

# ==================== NOTICIAS ====================
print("\nColetando noticias RSS...")
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
    print(f"noticias.json salvo — {len(noticias_raw)} noticias")
else:
    print("Nenhuma noticia coletada.")

print("\nConcluido!")
