import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import yfinance as yf
import pandas as pd
import json
import re
from io import StringIO
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False

UA_HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'}

# Headers de navegador completos — alguns portais (Suno, Money Times) usam
# proteção anti-bot que rejeita requisições com headers mínimos, principalmente
# vindas de datacenters (caso do GitHub Actions).
BROWSER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
    'Cache-Control': 'no-cache',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Upgrade-Insecure-Requests': '1',
}

# ==================== AÇÕES BR (por setor) ====================
ATIVOS_BR = {
    # Petróleo & Gás
    'PETR4': 'PETR4.SA', 'PETR3': 'PETR3.SA', 'PRIO3': 'PRIO3.SA',
    'RECV3': 'RECV3.SA', 'CSAN3': 'CSAN3.SA', 'UGPA3': 'UGPA3.SA',
    'VBBR3': 'VBBR3.SA', 'BRAV3': 'BRAV3.SA', 'BRAP4': 'BRAP4.SA',
    # Mineração & Siderurgia
    'VALE3': 'VALE3.SA', 'CSNA3': 'CSNA3.SA', 'GGBR4': 'GGBR4.SA',
    'USIM5': 'USIM5.SA', 'CMIN3': 'CMIN3.SA', 'GOAU4': 'GOAU4.SA',
    # Bancos
    'ITUB4': 'ITUB4.SA', 'ITUB3': 'ITUB3.SA', 'BBDC4': 'BBDC4.SA',
    'BBDC3': 'BBDC3.SA', 'BBAS3': 'BBAS3.SA', 'SANB11': 'SANB11.SA',
    'BPAC11': 'BPAC11.SA', 'BRSR6': 'BRSR6.SA', 'BMGB4': 'BMGB4.SA',
    # Financeiro & Seguros
    'B3SA3': 'B3SA3.SA', 'IRBR3': 'IRBR3.SA',
    'TRAD3': 'TRAD3.SA', 'BBSE3': 'BBSE3.SA', 'PSSA3': 'PSSA3.SA',
    # Energia Elétrica
    'AXIA3': 'AXIA3.SA', 'AXIA6': 'AXIA6.SA', 'CPFE3': 'CPFE3.SA',
    'ENGI11': 'ENGI11.SA', 'EGIE3': 'EGIE3.SA', 'TAEE11': 'TAEE11.SA',
    'ENEV3': 'ENEV3.SA', 'CMIG4': 'CMIG4.SA', 'AURE3': 'AURE3.SA',
    'NEOE3': 'NEOE3.SA', 'ALUP11': 'ALUP11.SA', 'EQTL3': 'EQTL3.SA',
    # Saneamento
    'SBSP3': 'SBSP3.SA', 'CSMG3': 'CSMG3.SA',
    # Telecom
    'VIVT3': 'VIVT3.SA', 'TIMS3': 'TIMS3.SA',
    # Varejo & Consumo
    'MGLU3': 'MGLU3.SA', 'LREN3': 'LREN3.SA',
    'AZZA3': 'AZZA3.SA', 'NATU3': 'NATU3.SA', 'AMAR3': 'AMAR3.SA',
    'CEAB3': 'CEAB3.SA', 'GMAT3': 'GMAT3.SA',
    'SBFG3': 'SBFG3.SA',
    # Bebidas & Alimentos
    'ABEV3': 'ABEV3.SA',
    # Frigoríficos
    'JBSS32': 'JBSS32.SA', 'MBRF3': 'MBRF3.SA', 'BEEF3': 'BEEF3.SA',
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
    'EMBJ3': 'EMBJ3.SA',
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
    # BDRs
    'SPCX34': 'SPCX34.SA',
}

# Setor hardcoded para evitar chamadas lentas de t.info
SETOR_BR = {
    'PETR4': 'Energy', 'PETR3': 'Energy', 'PRIO3': 'Energy', 'RECV3': 'Energy',
    'CSAN3': 'Energy', 'UGPA3': 'Energy', 'VBBR3': 'Energy', 'BRAV3': 'Energy', 'BRAP4': 'Basic Materials',
    'VALE3': 'Basic Materials', 'CSNA3': 'Basic Materials', 'GGBR4': 'Basic Materials',
    'USIM5': 'Basic Materials', 'CMIN3': 'Basic Materials', 'GOAU4': 'Basic Materials',
    'KLBN11': 'Basic Materials', 'SUZB3': 'Basic Materials',
    'ITUB4': 'Financial Services', 'ITUB3': 'Financial Services', 'BBDC4': 'Financial Services',
    'BBDC3': 'Financial Services', 'BBAS3': 'Financial Services', 'SANB11': 'Financial Services',
    'BPAC11': 'Financial Services', 'BRSR6': 'Financial Services', 'BMGB4': 'Financial Services',
    'B3SA3': 'Financial Services', 'IRBR3': 'Financial Services',
    'TRAD3': 'Financial Services', 'BBSE3': 'Financial Services', 'PSSA3': 'Financial Services',
    'AXIA3': 'Utilities', 'AXIA6': 'Utilities', 'CPFE3': 'Utilities', 'ENGI11': 'Utilities',
    'EGIE3': 'Utilities', 'TAEE11': 'Utilities', 'ENEV3': 'Utilities', 'CMIG4': 'Utilities',
    'AURE3': 'Utilities', 'NEOE3': 'Utilities', 'ALUP11': 'Utilities', 'EQTL3': 'Utilities',
    'SBSP3': 'Utilities', 'CSMG3': 'Utilities',
    'VIVT3': 'Communication Services', 'TIMS3': 'Communication Services',
    'ABEV3': 'Consumer Defensive', 'MBRF3': 'Consumer Defensive',
    'JBSS32': 'Consumer Defensive', 'BEEF3': 'Consumer Defensive',
    'SLCE3': 'Consumer Defensive', 'AGRO3': 'Consumer Defensive', 'SMTO3': 'Consumer Defensive', 'TTEN3': 'Consumer Defensive',
    'MGLU3': 'Consumer Cyclical', 'LREN3': 'Consumer Cyclical',
    'AZZA3': 'Consumer Cyclical', 'NATU3': 'Consumer Cyclical', 'AMAR3': 'Consumer Cyclical',
    'CEAB3': 'Consumer Cyclical', 'GMAT3': 'Consumer Cyclical', 'SBFG3': 'Consumer Cyclical',
    'COGN3': 'Consumer Cyclical', 'YDUQ3': 'Consumer Cyclical', 'SEER3': 'Consumer Cyclical',
    'MULT3': 'Real Estate', 'IGTI11': 'Real Estate',
    'CYRE3': 'Real Estate', 'MRVE3': 'Real Estate', 'EZTC3': 'Real Estate',
    'JHSF3': 'Real Estate', 'MDNE3': 'Real Estate', 'DIRR3': 'Real Estate',
    'TEND3': 'Real Estate', 'LAVV3': 'Real Estate',
    'RDOR3': 'Healthcare', 'HAPV3': 'Healthcare', 'FLRY3': 'Healthcare',
    'DASA3': 'Healthcare', 'RADL3': 'Healthcare', 'ODPV3': 'Healthcare',
    'RAIL3': 'Industrials', 'ECOR3': 'Industrials', 'POMO4': 'Industrials',
    'TGMA3': 'Industrials', 'LOGN3': 'Industrials', 'EMBJ3': 'Industrials',
    'RENT3': 'Industrials', 'MOVI3': 'Industrials', 'HBSA3': 'Industrials',
    'WEGE3': 'Industrials', 'RAIZ4': 'Industrials',
    'SPCX34': 'Industrials',
    'TOTS3': 'Technology', 'LWSA3': 'Technology', 'CASH3': 'Technology',
    'INTB3': 'Technology', 'MLAS3': 'Technology',
}

# ==================== FIIs (por categoria) ====================
FIIS = {
    # Galpões Logísticos
    'HGLG11': 'HGLG11.SA', 'XPLG11': 'XPLG11.SA', 'VILG11': 'VILG11.SA',
    'BRCO11': 'BRCO11.SA', 'GLOG11': 'GLOG11.SA', 'ALZR11': 'ALZR11.SA',
    'LVBI11': 'LVBI11.SA', 'GGRC11': 'GGRC11.SA', 'PATL11': 'PATL11.SA',
    'BTLG11': 'BTLG11.SA', 'VGIP11': 'VGIP11.SA', 'TRXF11': 'TRXF11.SA',
    # Shoppings
    'VISC11': 'VISC11.SA', 'XPML11': 'XPML11.SA', 'HSML11': 'HSML11.SA',
    'BPML11': 'BPML11.SA', 'ATSA11': 'ATSA11.SA', 'FVPQ11': 'FVPQ11.SA',
    # Lajes Corporativas
    'HGRE11': 'HGRE11.SA', 'BRCR11': 'BRCR11.SA', 'RCRB11': 'RCRB11.SA',
    'PATC11': 'PATC11.SA', 'PVBI11': 'PVBI11.SA', 'VINO11': 'VINO11.SA',
    'JSRE11': 'JSRE11.SA', 'TGAR11': 'TGAR11.SA',
    # Papel / CRI
    'MXRF11': 'MXRF11.SA', 'IRDM11': 'IRDM11.SA', 'KNCR11': 'KNCR11.SA',
    'KNHY11': 'KNHY11.SA', 'MCCI11': 'MCCI11.SA', 'VRTA11': 'VRTA11.SA',
    'HABT11': 'HABT11.SA', 'RECR11': 'RECR11.SA', 'VGIR11': 'VGIR11.SA',
    'CPTS11': 'CPTS11.SA', 'KNIP11': 'KNIP11.SA', 'RBRR11': 'RBRR11.SA',
    'OUJP11': 'OUJP11.SA', 'HCTR11': 'HCTR11.SA',
    # Fundo de Fundos
    'BTHF11': 'BTHF11.SA', 'HFOF11': 'HFOF11.SA', 'TFOF11': 'TFOF11.SA',
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
    'ACWI11': 'ACWI11.SA',
    # Temáticos
    'HASH11': 'HASH11.SA', 'GOLD11': 'GOLD11.SA', 'MATB11': 'MATB11.SA',
    'TECK11': 'TECK11.SA', 'AGRI11': 'AGRI11.SA',
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
    # Aeroespacial
    'SPCX': 'SPCX',
}

# ==================== NOMES COMPLETOS EUA ====================
NOMES_US = {
    'AAPL': 'Apple', 'MSFT': 'Microsoft', 'NVDA': 'Nvidia', 'GOOGL': 'Alphabet (Google)',
    'AMZN': 'Amazon', 'META': 'Meta Platforms', 'TSLA': 'Tesla',
    'AMD': 'AMD', 'INTC': 'Intel', 'AVGO': 'Broadcom', 'QCOM': 'Qualcomm',
    'TSM': 'Taiwan Semiconductor', 'MU': 'Micron Technology', 'ARM': 'Arm Holdings',
    'ORCL': 'Oracle', 'CRM': 'Salesforce', 'ADBE': 'Adobe', 'NOW': 'ServiceNow',
    'SNOW': 'Snowflake', 'PLTR': 'Palantir', 'UBER': 'Uber',
    'JPM': 'JPMorgan Chase', 'BAC': 'Bank of America', 'GS': 'Goldman Sachs', 'MS': 'Morgan Stanley',
    'V': 'Visa', 'MA': 'Mastercard', 'AXP': 'American Express', 'BRK-B': 'Berkshire Hathaway',
    'JNJ': 'Johnson & Johnson', 'UNH': 'UnitedHealth', 'PFE': 'Pfizer', 'ABBV': 'AbbVie',
    'MRK': 'Merck', 'LLY': 'Eli Lilly', 'AMGN': 'Amgen',
    'XOM': 'Exxon Mobil', 'CVX': 'Chevron',
    'WMT': 'Walmart', 'COST': 'Costco', 'KO': 'Coca-Cola', 'PEP': 'PepsiCo',
    'MCD': "McDonald's", 'DIS': 'Disney', 'SBUX': 'Starbucks', 'NKE': 'Nike',
    'HD': 'Home Depot', 'NFLX': 'Netflix',
    'CAT': 'Caterpillar', 'BA': 'Boeing', 'GE': 'General Electric', 'RTX': 'RTX Corporation', 'DE': 'Deere & Company',
    'VZ': 'Verizon', 'T': 'AT&T',
    'SPCX': 'SpaceX',
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

# Tickers conhecidos (para vincular notícia <-> ativo)
TICKERS_CONHECIDOS = set(ATIVOS_BR) | set(FIIS) | set(ETFS)
CRIPTO_NO_TITULO = {
    'bitcoin': 'BTC', 'btc': 'BTC', 'ethereum': 'ETH', 'solana': 'SOL',
    'cardano': 'ADA', 'xrp': 'XRP', 'dogecoin': 'DOGE',
}

def extrair_tickers(texto):
    """Extrai tickers B3 (ex.: PETR4, HGLG11) e criptos citados no texto."""
    achados = []
    for m in re.findall(r'\b([A-Z]{4}\d{1,2})\b', texto or ''):
        if m in TICKERS_CONHECIDOS and m not in achados:
            achados.append(m)
    tl = (texto or '').lower()
    for palavra, tk in CRIPTO_NO_TITULO.items():
        if palavra in tl and tk not in achados:
            achados.append(tk)
    return achados[:3]

# Palavras que indicam manchete de alto impacto
PALAVRAS_MANCHETE = [
    'selic', 'copom', 'ibovespa', 'ipca', 'petrobras', 'vale', 'itaú', 'itau',
    'dólar', 'dolar', 'fed', 'juros', 'banco central', 'bitcoin', 'recorde',
    'despenca', 'dispara', 'bilhões', 'bilhoes', 'tombo', 'máxima', 'maxima',
]

def pontuar_noticia(noticia):
    """Score p/ escolher manchete: recência + palavras de impacto + resumo presente."""
    score = 0.0
    try:
        pub = datetime.strptime(noticia['time'], '%Y-%m-%dT%H:%M:%SZ')
        agora = datetime.now(timezone.utc).replace(tzinfo=None)
        horas = max((agora - pub).total_seconds() / 3600, 0)
        score += max(0, 24 - horas)  # até 24 pts por recência
    except Exception:
        pass
    tl = noticia['title'].lower()
    score += sum(6 for p in PALAVRAS_MANCHETE if p in tl)
    if noticia.get('summary'):
        score += 4
    if noticia.get('tickers'):
        score += 2
    return score

def classificar_noticia(title, default_cat='acoes'):
    tl = title.lower()
    for cat, palavras in PALAVRAS_CATEGORIA.items():
        if any(p in tl for p in palavras):
            return cat
    return default_cat

def publicacao_iso(published):
    """Converte published_parsed para ISO 8601 UTC string."""
    try:
        if hasattr(published, 'tm_year'):
            pub_dt = datetime(*published[:6])
            return pub_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        return None
    except Exception:
        return None

IMG_PLACEHOLDER_RE = re.compile(r'default|placeholder|no-image|sem-imagem|avatar|gravatar', re.IGNORECASE)

def extrair_imagem(entry, summary_raw):
    """Tenta extrair uma imagem de capa da noticia a partir de varios formatos de RSS.
    Retorna a URL da imagem ou None se nao encontrar nenhuma valida."""
    candidatos = []

    media_content = entry.get('media_content')
    if media_content:
        candidatos += [m.get('url') for m in media_content if m.get('url')]

    media_thumbnail = entry.get('media_thumbnail')
    if media_thumbnail:
        candidatos += [m.get('url') for m in media_thumbnail if m.get('url')]

    if entry.get('mediaurl'):
        candidatos.append(entry.get('mediaurl'))

    for link in entry.get('links', []):
        if 'image' in link.get('type', ''):
            candidatos.append(link.get('href'))

    for campo in (summary_raw, entry.get('content', [{}])[0].get('value', '') if entry.get('content') else ''):
        if campo:
            m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', campo)
            if m:
                candidatos.append(m.group(1))

    for url in candidatos:
        if url and url.startswith('http') and not IMG_PLACEHOLDER_RE.search(url):
            return url
    return None

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

def buscar_og_image(url):
    """Busca og:image da página da notícia como fallback quando o feed não traz imagem."""
    if not HAS_REQUESTS or not url:
        return None
    try:
        resp = requests.get(url, headers=BROWSER_HEADERS, timeout=10, allow_redirects=True)
        # Lê até 300KB — a Suno, por exemplo, coloca o og:image depois dos 57KB,
        # então o limite antigo de 50KB fazia a busca falhar mesmo com a página OK
        html = resp.text[:300000]
        match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
        if not match:
            match = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html, re.I)
        if match:
            img_url = match.group(1)
            if img_url.startswith('http'):
                return img_url
    except Exception:
        pass
    return None

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
                pub_iso = publicacao_iso(published) if published else datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
                todas.append({
                    'title': title, 'summary': summary,
                    'source': feed_info['source'], 'url': url,
                    'time': pub_iso,
                    'cat': cat, 'tickers': extrair_tickers(title + ' ' + summary),
                    'image': extrair_imagem(entry, summary_raw),
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

# ==================== NOMES COMPLETOS BR ====================
NOMES_BR = {
    'PETR4':'Petrobras PN','PETR3':'Petrobras ON','PRIO3':'PetroRio','BRAV3':'Brava Energia',
    'RECV3':'Recôncavo','CSAN3':'Cosan','UGPA3':'Ultrapar','VBBR3':'Vibra Energia','BRAP4':'Bradespar',
    'VALE3':'Vale','CSNA3':'CSN','GGBR4':'Gerdau PN','USIM5':'Usiminas','CMIN3':'CSN Mineração','GOAU4':'Metalúrgica Gerdau',
    'ITUB4':'Itaú Unibanco PN','ITUB3':'Itaú Unibanco ON','BBDC4':'Bradesco PN','BBDC3':'Bradesco ON',
    'BBAS3':'Banco do Brasil','SANB11':'Santander BR','BPAC11':'BTG Pactual','BRSR6':'Banrisul','BMGB4':'Banco BMG',
    'B3SA3':'B3','IRBR3':'IRB Brasil','TRAD3':'Tradecorp','BBSE3':'BB Seguridade','PSSA3':'Porto Seguro',
    'AXIA3':'Axia Energia ON','AXIA6':'Axia Energia PNB','CPFE3':'CPFL Energia','ENGI11':'Energisa',
    'EGIE3':'Engie Brasil','TAEE11':'Taesa','ENEV3':'Eneva','CMIG4':'Cemig PN',
    'AURE3':'Auren Energia','NEOE3':'Neoenergia','ALUP11':'Alupar','EQTL3':'Equatorial Energia',
    'SBSP3':'Sabesp','CSMG3':'Copasa',
    'VIVT3':'Vivo (Telefônica)','TIMS3':'TIM',
    'MGLU3':'Magazine Luiza','LREN3':'Lojas Renner','AZZA3':'Azzas 2154',
    'NATU3':'Natura','AMAR3':'Marisa','CEAB3':'C&A','GMAT3':'Grupo Mateus','SBFG3':'SBF Group (Centauro)',
    'ABEV3':'Ambev',
    'JBSS32':'JBS (BDR)','MBRF3':'MBRF Global Foods','BEEF3':'Minerva Foods',
    'SLCE3':'SLC Agrícola','AGRO3':'Brasilagro','SMTO3':'São Martinho','TTEN3':'Terra Santa Agro',
    'RDOR3':'Rede D\'Or','HAPV3':'Hapvida','FLRY3':'Fleury','DASA3':'Dasa','RADL3':'Raia Drogasil','ODPV3':'Odontoprev',
    'CYRE3':'Cyrela','MRVE3':'MRV Engenharia','EZTC3':'EZTEC','JHSF3':'JHSF','MDNE3':'Modenese','DIRR3':'Direcional','TEND3':'Tenda','LAVV3':'Lavvi',
    'MULT3':'Multiplan','IGTI11':'Iguatemi',
    'RAIL3':'Rumo','ECOR3':'Ecorodovias','POMO4':'Marcopolo','TGMA3':'Tegma','LOGN3':'Log-In',
    'EMBJ3':'Embraer',
    'RENT3':'Localiza','MOVI3':'Movida','HBSA3':'Hidrovias do Brasil',
    'SUZB3':'Suzano','KLBN11':'Klabin',
    'TOTS3':'Totvs','LWSA3':'Locaweb','CASH3':'Méliuz','INTB3':'Intelbras','MLAS3':'Multilaser',
    'COGN3':'Cogna','YDUQ3':'Yduqs','SEER3':'SER Educacional',
    'WEGE3':'WEG','RAIZ4':'Raízen',
    'SPCX34':'SpaceX (BDR)',
}

NOMES_FII = {
    'HGLG11':'CGHG Logística','XPLG11':'XP Log','VILG11':'Vinci Logística','BRCO11':'Bresco Logística',
    'GLOG11':'Golgi Log','ALZR11':'Alianza Trust','LVBI11':'LivBras','GGRC11':'GGR Covepi','PATL11':'Pátria Logística',
    'BTLG11':'BTG Logística','VGIP11':'Valora CRI','TRXF11':'TRX Real Estate',
    'VISC11':'Vinci Shopping Centers','XPML11':'XP Malls','HSML11':'HSI Malls','BPML11':'BPM Logística','ATSA11':'Ático Shopping','FVPQ11':'Fundo Vale Paraíba',
    'HGRE11':'CSHG Real Estate','BRCR11':'BC Fund','RCRB11':'Rio Bravo Renda Corporativa','PATC11':'Pátria Offices',
    'PVBI11':'VBI Prime Properties','VINO11':'Vinci Offices','JSRE11':'JS Real Estate','TGAR11':'TG Ativo Real',
    'MXRF11':'Maxi Renda','IRDM11':'Iridium Recebíveis','KNCR11':'Kinea Recebíveis','KNHY11':'Kinea High Yield','MCCI11':'Mauá Capital',
    'VRTA11':'Fator Verita','HABT11':'Habitat II','RECR11':'REC Recebíveis','VGIR11':'Valora RE','CPTS11':'Capitânia Securities',
    'KNIP11':'Kinea Índice de Preços','RBRR11':'RBR Rendimento','OUJP11':'Ourinvest JPP','HCTR11':'Hectare CE',
    'BTHF11':'BTG Hedge FoF','HFOF11':'Hedge Top FoF','TFOF11':'Torre Forte FoF',
    'BLMG11':'Bluemacaw Logística','RBVA11':'Rio Bravo Vacâncias','RZAK11':'Riza Akin',
    'KNRI11':'Kinea Renda Imobiliária','HGPO11':'CSHG Prime Offices','BTRA11':'Btg Pactual Terras','RBRP11':'RBR Properties','VVPR11':'VV Properties',
}

# ==================== COLETA EM BATCH (rápido) ====================
def _normaliza_close_vol(raw, tickers):
    """Extrai DataFrames de Close e Volume, sempre com colunas = tickers."""
    if len(tickers) == 1:
        close_df = pd.DataFrame({tickers[0]: raw['Close']})
        vol_df   = pd.DataFrame({tickers[0]: raw.get('Volume', pd.Series(dtype=float))})
    else:
        close_df = raw['Close']  if 'Close'  in raw.columns else pd.DataFrame()
        vol_df   = raw['Volume'] if 'Volume' in raw.columns else pd.DataFrame()
    return close_df, vol_df

def _perf(col, dias):
    """Retorna variação percentual relativa a `dias` pregões atrás."""
    if len(col) > dias:
        p_old = float(col.iloc[-dias-1])
        p_new = float(col.iloc[-1])
        if p_old > 0:
            return round((p_new / p_old - 1) * 100, 2)
    return None

def _sparkline(col, pontos=30):
    """Amostra a série de fechamento em ~`pontos` valores p/ mini-gráfico no site."""
    valores = [float(v) for v in col.tolist()]
    if len(valores) <= pontos:
        return [round(v, 2) for v in valores]
    passo = len(valores) / pontos
    amostra = [valores[int(i * passo)] for i in range(pontos)]
    amostra[-1] = valores[-1]  # garante o preço atual como último ponto
    return [round(v, 2) for v in amostra]

def coletar_batch(ativos_dict, tipo, setor_map=None, nome_map=None, com_dy=False):
    """Baixa 1 ano de dados em batch — preço, variação, períodos, sparkline e DY."""
    if not ativos_dict:
        return {}

    ticker_para_nome = {v: k for k, v in ativos_dict.items()}
    tickers = list(ativos_dict.values())
    resultado = {}

    try:
        raw = yf.download(
            tickers if len(tickers) > 1 else tickers[0],
            period='1y',
            auto_adjust=True,
            actions=com_dy,
            progress=False,
            threads=True,
        )
        close_df, vol_df = _normaliza_close_vol(raw, tickers)

        div_df = pd.DataFrame()
        if com_dy:
            try:
                div_df = raw['Dividends'] if len(tickers) > 1 else pd.DataFrame({tickers[0]: raw['Dividends']})
            except Exception:
                pass

        for ticker_yf in tickers:
            nome = ticker_para_nome.get(ticker_yf, ticker_yf)
            if ticker_yf not in close_df.columns:
                continue
            col = close_df[ticker_yf].dropna()
            if len(col) < 1:
                continue

            preco = round(float(col.iloc[-1]), 2)
            var   = round((float(col.iloc[-1]) / float(col.iloc[-2]) - 1) * 100, 2) if len(col) >= 2 else 0.0

            vol = 0
            if ticker_yf in vol_df.columns:
                try: vol = int(vol_df[ticker_yf].dropna().iloc[-1])
                except Exception: pass

            # DY 12m = soma dos proventos do último ano / preço atual
            dy = None
            if com_dy and ticker_yf in div_df.columns:
                try:
                    soma_div = float(div_df[ticker_yf].fillna(0).sum())
                    if soma_div > 0 and preco > 0:
                        dy = round(soma_div / preco * 100, 2)
                except Exception:
                    pass

            nome_completo = (nome_map or {}).get(nome, nome)
            setor         = (setor_map or {}).get(nome, '')

            resultado[nome] = {
                'stock':    nome,
                'name':     nome_completo,
                'close':    preco,
                'change':   var,
                'volume':   vol,
                'market_cap': 0,
                'sector':   setor,
                'type':     tipo,
                'dy':       dy,
                'pvp':      None,
                'perf_1m':  _perf(col, 21),
                'perf_3m':  _perf(col, 63),
                'perf_6m':  _perf(col, 126),
                'perf_12m': _perf(col, 252),
                'spark':    _sparkline(col),
            }

    except Exception as e:
        print(f"  Batch falhou ({tipo}): {e}")

    return resultado

# ==================== ENRIQUECIMENTO: MARKET CAP (BrAPI) ====================
def enriquecer_market_cap_brapi(dados):
    """Uma única chamada à BrAPI traz market_cap de todos os ativos B3."""
    if not HAS_REQUESTS:
        return
    try:
        resp = requests.get('https://brapi.dev/api/quote/list', headers=UA_HEADERS, timeout=30)
        lista = resp.json().get('stocks', [])
        caps = {s['stock']: s.get('market_cap') for s in lista if s.get('market_cap')}
        atualizados = 0
        for grupo in ('stocks', 'fiis', 'etfs'):
            for tk, ativo in dados.get(grupo, {}).items():
                if tk in caps:
                    ativo['market_cap'] = caps[tk]
                    atualizados += 1
        print(f"  Market cap BrAPI: {atualizados} ativos atualizados")
    except Exception as e:
        print(f"  BrAPI market cap falhou: {e}")

def enriquecer_market_cap_us(dados):
    """Market cap das ações americanas via fast_info (paralelo)."""
    us = dados.get('us_stocks', {})
    if not us:
        return

    def busca(tk):
        try:
            mc = yf.Ticker(tk).fast_info['marketCap']
            return tk, int(mc) if mc else 0
        except Exception:
            return tk, 0

    atualizados = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        for tk, mc in ex.map(busca, list(us.keys())):
            if mc:
                us[tk]['market_cap'] = mc
                atualizados += 1
    print(f"  Market cap EUA: {atualizados} ativos atualizados")

# ==================== ENRIQUECIMENTO: DY / P/VP FIIs (Fundamentus) ====================
def enriquecer_fiis_fundamentus(dados):
    """Tabela única do Fundamentus traz DY e P/VP de todos os FIIs listados."""
    if not HAS_REQUESTS:
        return
    try:
        resp = requests.get('https://www.fundamentus.com.br/fii_resultado.php',
                            headers=UA_HEADERS, timeout=30)
        resp.encoding = 'utf-8'
        tabelas = pd.read_html(StringIO(resp.text), decimal=',', thousands='.')
        if not tabelas:
            return
        df = tabelas[0]
        df.columns = [str(c).strip() for c in df.columns]

        def pct(valor):
            try:
                return round(float(str(valor).replace('%', '').replace('.', '').replace(',', '.')), 2)
            except Exception:
                return None

        def num(valor):
            try:
                v = float(str(valor).replace('.', '').replace(',', '.')) if isinstance(valor, str) else float(valor)
                # P/VP no fundamentus pode vir multiplicado (ex.: 95 = 0,95)
                return round(v / 100, 2) if v > 20 else round(v, 2)
            except Exception:
                return None

        atualizados = 0
        for _, row in df.iterrows():
            tk = str(row.get('Papel', '')).strip()
            if tk in dados.get('fiis', {}):
                dy  = pct(row.get('Dividend Yield'))
                pvp = num(row.get('P/VP'))
                if dy is not None and 0 < dy < 60:
                    dados['fiis'][tk]['dy'] = dy
                if pvp is not None and 0 < pvp < 10:
                    dados['fiis'][tk]['pvp'] = pvp
                atualizados += 1
        print(f"  Fundamentus FIIs: {atualizados} fundos enriquecidos (DY/P-VP)")
    except Exception as e:
        print(f"  Fundamentus falhou (DY via yfinance mantido): {e}")

def coletar_indice(ticker_yf, nome):
    try:
        t = yf.Ticker(ticker_yf)
        hist = t.history(period='5d')
        closes = hist['Close'].dropna() if not hist.empty else None
        if closes is None or closes.empty:
            return None
        preco = round(float(closes.iloc[-1]), 2)
        preco_ant = float(closes.iloc[-2]) if len(closes) >= 2 else preco
        var = round(((preco / preco_ant) - 1) * 100, 2)
        return {'stock': nome, 'close': preco, 'change': var}
    except Exception as e:
        print(f"  Erro indice {nome}: {e}")
        return None

def _sem_nan(obj):
    """Remove NaN/Inf recursivamente — NaN no JSON quebra o JSON.parse do navegador."""
    if isinstance(obj, dict):
        return {k: _sem_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sem_nan(v) for v in obj]
    if isinstance(obj, float) and (obj != obj or obj in (float('inf'), float('-inf'))):
        return None
    return obj

# ==================== MAIN ====================
print("Iniciando coleta Bom Dia Investidor...\n")

dados = {
    'stocks': {}, 'fiis': {}, 'etfs': {},
    'us_stocks': {}, 'crypto': {}, 'indices': {}, 'dolar': {},
    'atualizado_em': '',
}

print(f"Acoes BR ({len(ATIVOS_BR)} tickers)...")
dados['stocks'] = coletar_batch(ATIVOS_BR, 'stock', setor_map=SETOR_BR, nome_map=NOMES_BR)
print(f"  OK: {len(dados['stocks'])} ativos")

print(f"FIIs ({len(FIIS)} tickers)...")
dados['fiis'] = coletar_batch(FIIS, 'fii', nome_map=NOMES_FII, com_dy=True)
print(f"  OK: {len(dados['fiis'])} FIIs")

print(f"ETFs ({len(ETFS)} tickers)...")
dados['etfs'] = coletar_batch(ETFS, 'etf')
print(f"  OK: {len(dados['etfs'])} ETFs")

print(f"Acoes EUA ({len(ATIVOS_US)} tickers)...")
dados['us_stocks'] = coletar_batch(ATIVOS_US, 'us', nome_map=NOMES_US)
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

def coletar_cambio(ticker_yf, label):
    try:
        hist_d = yf.Ticker(ticker_yf).history(period='3d')
        if hist_d.empty:
            return None
        pd_val = round(float(hist_d['Close'].iloc[-1]), 4)
        pd_ant = float(hist_d['Close'].iloc[-2]) if len(hist_d) >= 2 else pd_val
        print(f"  {label}: {pd_val}")
        return {'stock': label, 'close': pd_val, 'change': round(((pd_val / pd_ant) - 1) * 100, 2)}
    except Exception as e:
        print(f"  {label}: {e}")
        return None

dados['dolar'] = coletar_cambio('USDBRL=X', 'USD/BRL') or {}
dados['euro']  = coletar_cambio('EURBRL=X', 'EUR/BRL') or {}

# ==================== DI FUTURO (B3) ====================
def coletar_di_futuro():
    """Contratos DI1 da B3 (curva de juros futura) — endpoint público de market data."""
    if not HAS_REQUESTS:
        return []
    try:
        resp = requests.get('https://cotacao.b3.com.br/mds/api/v1/DerivativeQuotation/DI1',
                            headers=UA_HEADERS, timeout=30)
        contratos = []
        for s in resp.json().get('Scty', []):
            qtn = s.get('SctyQtn', {})
            summ = (s.get('asset') or {}).get('AsstSummry', {})
            taxa = qtn.get('curPrc') or qtn.get('prvsDayAdjstmntPric')
            venc = summ.get('mtrtyCode', '')
            if not taxa or not venc:
                continue
            contratos.append({
                'symb': s.get('symb', ''),
                'venc': venc,
                'taxa': round(float(taxa), 3),
                'ant': round(float(qtn.get('prvsDayAdjstmntPric') or 0), 3) or None,
                'contratos': int(summ.get('opnCtrcts') or 0),
            })
        # Curto prazo: 2 vencimentos mais próximos com alta liquidez (proxy do CDI)
        # Longo prazo: contratos de janeiro (DI1F), benchmarks da curva
        contratos.sort(key=lambda c: c['venc'])
        curtos = [c for c in contratos if not c['symb'].startswith('DI1F') and c['contratos'] >= 1_000_000][:2]
        jans = [c for c in contratos if c['symb'].startswith('DI1F')][:6]
        sel = sorted(curtos + jans, key=lambda c: c['venc'])
        return sel[:8]
    except Exception as e:
        print(f"  DI futuro B3: {e}")
        return []

dados['di_futuro'] = coletar_di_futuro()
print(f"  DI futuro: {len(dados['di_futuro'])} contratos")

# ==================== COMMODITIES (futuros, Yahoo Finance) ====================
COMMODITIES = {
    'OURO':    {'yf': 'GC=F',  'nome': 'Ouro',             'unidade': 'US$/onça'},
    'PRATA':   {'yf': 'SI=F',  'nome': 'Prata',            'unidade': 'US$/onça'},
    'BRENT':   {'yf': 'BZ=F',  'nome': 'Petróleo Brent',   'unidade': 'US$/barril'},
    'WTI':     {'yf': 'CL=F',  'nome': 'Petróleo WTI',     'unidade': 'US$/barril'},
    'GAS':     {'yf': 'NG=F',  'nome': 'Gás Natural',      'unidade': 'US$/MMBtu'},
    'COBRE':   {'yf': 'HG=F',  'nome': 'Cobre',            'unidade': 'US$/libra'},
    'MINERIO': {'yf': 'TIO=F', 'nome': 'Minério de Ferro', 'unidade': 'US$/tonelada'},
    'SOJA':    {'yf': 'ZS=F',  'nome': 'Soja',             'unidade': '¢/bushel'},
    'MILHO':   {'yf': 'ZC=F',  'nome': 'Milho',            'unidade': '¢/bushel'},
    'CAFE':    {'yf': 'KC=F',  'nome': 'Café',             'unidade': '¢/libra'},
    'ACUCAR':  {'yf': 'SB=F',  'nome': 'Açúcar',           'unidade': '¢/libra'},
}

print("Commodities...")
dados['commodities'] = {}
for chave, info in COMMODITIES.items():
    r = coletar_indice(info['yf'], info['nome'])
    if r:
        r['unidade'] = info['unidade']
        dados['commodities'][chave] = r
print(f"  OK: {len(dados['commodities'])} commodities")

print("Enriquecendo dados...")
enriquecer_market_cap_brapi(dados)
enriquecer_market_cap_us(dados)
enriquecer_fiis_fundamentus(dados)

dados['atualizado_em'] = datetime.now().strftime('%d/%m/%Y %H:%M')
dados['atualizado_iso'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

with open('dados.json', 'w', encoding='utf-8') as f:
    json.dump(_sem_nan(dados), f, ensure_ascii=False, indent=2)

total = sum(len(v) for k, v in dados.items() if isinstance(v, dict) and k not in ('indices', 'dolar'))
print(f"\ndados.json salvo — {total} ativos coletados")

# ==================== NOTICIAS ====================
print("\nColetando noticias RSS...")
noticias_raw = coletar_noticias()

if noticias_raw:
    # Manchete escolhida por score (recência + impacto), não pela ordem do feed
    ordenadas = sorted(noticias_raw, key=pontuar_noticia, reverse=True)

    # Reaproveita imagens descobertas em execuções anteriores (cache por URL):
    # se numa rodada o portal respondeu com a og:image, não perde nas próximas
    # mesmo que o site passe a bloquear a requisição.
    try:
        with open('noticias.json', 'r', encoding='utf-8') as f:
            anterior = json.load(f)
        cache_img = {}
        for n in ([anterior.get('headline')] + anterior.get('featured', []) + anterior.get('all', [])):
            if n and n.get('url') and n.get('image'):
                cache_img[n['url']] = n['image']
        for n in ordenadas:
            if not n.get('image') and n['url'] in cache_img:
                n['image'] = cache_img[n['url']]
    except Exception:
        pass

    # Busca og:image para TODAS as notícias sem imagem (não só as top 15)
    print("Buscando imagens og:image para notícias sem thumbnail...")
    sem_img = [n for n in ordenadas if not n.get('image')]
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(buscar_og_image, n['url']): n for n in sem_img}
        for fut in futures:
            n = futures[fut]
            try:
                img = fut.result()
                if img:
                    n['image'] = img
            except Exception:
                pass
    com_img = sum(1 for n in ordenadas if n.get('image'))
    print(f"  {com_img}/{len(ordenadas)} notícias com imagem")

    noticias_json = {
        'headline': ordenadas[0],
        'featured': ordenadas[1:3],
        'all': noticias_raw,
        'atualizado_em': datetime.now().strftime('%d/%m/%Y %H:%M'),
    }
    with open('noticias.json', 'w', encoding='utf-8') as f:
        json.dump(noticias_json, f, ensure_ascii=False, indent=2)
    print(f"noticias.json salvo — {len(noticias_raw)} noticias")
else:
    print("Nenhuma noticia coletada.")

# ==================== SITEMAP ====================
# Atualiza o lastmod da home a cada execução — sinaliza pros buscadores que o
# conteúdo é atualizado com frequência (melhora a taxa de re-crawl do Google).
lastmod = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S+00:00')
paginas_sitemap = [
    ('https://bomdiainvestidor.com.br/', 'hourly', '1.0', lastmod),
    ('https://bomdiainvestidor.com.br/sobre.html', 'monthly', '0.4', None),
    ('https://bomdiainvestidor.com.br/privacidade.html', 'yearly', '0.2', None),
    ('https://bomdiainvestidor.com.br/termos.html', 'yearly', '0.2', None),
    ('https://bomdiainvestidor.com.br/contato.html', 'yearly', '0.2', None),
    ('https://bomdiainvestidor.com.br/cartas-gestores/', 'weekly', '0.5', None),
]
linhas = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for loc, freq, prio, mod in paginas_sitemap:
    linhas.append('  <url>')
    linhas.append(f'    <loc>{loc}</loc>')
    if mod:
        linhas.append(f'    <lastmod>{mod}</lastmod>')
    linhas.append(f'    <changefreq>{freq}</changefreq>')
    linhas.append(f'    <priority>{prio}</priority>')
    linhas.append('  </url>')
linhas.append('</urlset>')
with open('sitemap.xml', 'w', encoding='utf-8') as f:
    f.write('\n'.join(linhas) + '\n')
print("sitemap.xml atualizado")

print("\nConcluido!")
