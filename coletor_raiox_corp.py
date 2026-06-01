"""
Coletor Raio-X Corporativo — Convexa News
Puxa dados financeiros de empresas listadas na B3 via Yahoo Finance.
Calcula score de saúde: Dívida/EBITDA, Liquidez, Cobertura de Juros, Margem, FCF.
Gera: raiox_corp.json
"""

import json
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from datetime import datetime

try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False
    print("ERRO: yfinance não instalado. Rode: pip install yfinance")

# ==================== EMPRESAS B3 ====================
EMPRESAS = {
    # Petróleo & Gás
    'PETR4': {'nome': 'Petrobras', 'setor': 'Petróleo & Gás'},
    'PRIO3': {'nome': 'PetroRio', 'setor': 'Petróleo & Gás'},
    'RECV3': {'nome': 'PetroRecôncavo', 'setor': 'Petróleo & Gás'},
    'CSAN3': {'nome': 'Cosan', 'setor': 'Petróleo & Gás'},
    'UGPA3': {'nome': 'Ultrapar', 'setor': 'Petróleo & Gás'},
    'VBBR3': {'nome': 'Vibra Energia', 'setor': 'Petróleo & Gás'},
    'RAIZ4': {'nome': 'Raízen', 'setor': 'Energia / Agro'},
    # Mineração & Siderurgia
    'VALE3': {'nome': 'Vale', 'setor': 'Mineração'},
    'CSNA3': {'nome': 'CSN', 'setor': 'Siderurgia'},
    'GGBR4': {'nome': 'Gerdau', 'setor': 'Siderurgia'},
    'USIM5': {'nome': 'Usiminas', 'setor': 'Siderurgia'},
    'GOAU4': {'nome': 'Metalúrgica Gerdau', 'setor': 'Siderurgia'},
    # Bancos (já tem no Raio-X Bancário, mas útil pra debêntures)
    'ITUB4': {'nome': 'Itaú Unibanco', 'setor': 'Bancos'},
    'BBDC4': {'nome': 'Bradesco', 'setor': 'Bancos'},
    'BBAS3': {'nome': 'Banco do Brasil', 'setor': 'Bancos'},
    'SANB11': {'nome': 'Santander Brasil', 'setor': 'Bancos'},
    # Energia Elétrica
    'ELET3': {'nome': 'Eletrobras', 'setor': 'Energia Elétrica'},
    'CPFE3': {'nome': 'CPFL Energia', 'setor': 'Energia Elétrica'},
    'ENGI11': {'nome': 'Energisa', 'setor': 'Energia Elétrica'},
    'EGIE3': {'nome': 'Engie Brasil', 'setor': 'Energia Elétrica'},
    'TAEE11': {'nome': 'Taesa', 'setor': 'Energia Elétrica'},
    'ENEV3': {'nome': 'Eneva', 'setor': 'Energia Elétrica'},
    'CMIG4': {'nome': 'Cemig', 'setor': 'Energia Elétrica'},
    'EQTL3': {'nome': 'Equatorial', 'setor': 'Energia Elétrica'},
    'NEOE3': {'nome': 'Neoenergia', 'setor': 'Energia Elétrica'},
    'SBSP3': {'nome': 'Sabesp', 'setor': 'Saneamento'},
    # Varejo & Consumo
    'MGLU3': {'nome': 'Magazine Luiza', 'setor': 'Varejo'},
    'LREN3': {'nome': 'Lojas Renner', 'setor': 'Varejo'},
    'ARZZ3': {'nome': 'Arezzo', 'setor': 'Varejo'},
    'PETZ3': {'nome': 'Petz', 'setor': 'Varejo'},
    'GMAT3': {'nome': 'Grupo Mateus', 'setor': 'Varejo'},
    'ABEV3': {'nome': 'Ambev', 'setor': 'Bebidas'},
    # Frigoríficos
    'JBSS3': {'nome': 'JBS', 'setor': 'Frigoríficos'},
    'MRFG3': {'nome': 'Marfrig', 'setor': 'Frigoríficos'},
    'BEEF3': {'nome': 'Minerva Foods', 'setor': 'Frigoríficos'},
    'BRFS3': {'nome': 'BRF', 'setor': 'Alimentos'},
    # Saúde
    'RDOR3': {'nome': 'Rede D\'Or', 'setor': 'Saúde'},
    'HAPV3': {'nome': 'Hapvida', 'setor': 'Saúde'},
    'FLRY3': {'nome': 'Fleury', 'setor': 'Saúde'},
    'RADL3': {'nome': 'Raia Drogasil', 'setor': 'Saúde'},
    # Construção
    'CYRE3': {'nome': 'Cyrela', 'setor': 'Construção'},
    'MRVE3': {'nome': 'MRV', 'setor': 'Construção'},
    'EZTC3': {'nome': 'EZTEC', 'setor': 'Construção'},
    'DIRR3': {'nome': 'Direcional', 'setor': 'Construção'},
    # Logística & Transporte
    'RAIL3': {'nome': 'Rumo', 'setor': 'Logística'},
    'EMBR3': {'nome': 'Embraer', 'setor': 'Aeroespacial'},
    'RENT3': {'nome': 'Localiza', 'setor': 'Locação'},
    'MOVI3': {'nome': 'Movida', 'setor': 'Locação'},
    # Papel & Celulose
    'SUZB3': {'nome': 'Suzano', 'setor': 'Papel & Celulose'},
    'KLBN11': {'nome': 'Klabin', 'setor': 'Papel & Celulose'},
    # Tecnologia
    'TOTS3': {'nome': 'Totvs', 'setor': 'Tecnologia'},
    'LWSA3': {'nome': 'Locaweb', 'setor': 'Tecnologia'},
    # Telecomunicação
    'VIVT3': {'nome': 'Vivo', 'setor': 'Telecom'},
    'TIMS3': {'nome': 'TIM', 'setor': 'Telecom'},
    # Industrial
    'WEGE3': {'nome': 'WEG', 'setor': 'Industrial'},
    'B3SA3': {'nome': 'B3', 'setor': 'Bolsa'},
    # Agro
    'SLCE3': {'nome': 'SLC Agrícola', 'setor': 'Agro'},
    'SMTO3': {'nome': 'São Martinho', 'setor': 'Agro'},
    # Educação
    'COGN3': {'nome': 'Cogna', 'setor': 'Educação'},
    'YDUQ3': {'nome': 'Yduqs', 'setor': 'Educação'},
    # Shopping
    'MULT3': {'nome': 'Multiplan', 'setor': 'Shopping'},
    'IGTI11': {'nome': 'Iguatemi', 'setor': 'Shopping'},
    # Seguros / Financeiro
    'BBSE3': {'nome': 'BB Seguridade', 'setor': 'Seguros'},
    'PSSA3': {'nome': 'Porto Seguro', 'setor': 'Seguros'},
    'CIEL3': {'nome': 'Cielo', 'setor': 'Meios de Pagamento'},
}


def safe_get(series, key, default=None):
    """Extrai valor de um pandas Series/dict de forma segura."""
    try:
        val = series.get(key, default)
        if val is None:
            return default
        return float(val)
    except Exception:
        return default


def analisar_empresa(ticker):
    """Analisa saúde financeira de uma empresa via Yahoo Finance."""
    yf_ticker = ticker + '.SA'
    info = EMPRESAS[ticker]

    try:
        t = yf.Ticker(yf_ticker)

        # Dados financeiros
        bs = t.balance_sheet
        inc = t.income_stmt
        cf = t.cashflow

        if bs is None or bs.empty or inc is None or inc.empty:
            return None

        # Último período disponível
        bs_last = bs.iloc[:, 0]
        inc_last = inc.iloc[:, 0]
        cf_last = cf.iloc[:, 0] if cf is not None and not cf.empty else {}

        # === INDICADORES ===

        # Dívida total
        divida_curto = safe_get(bs_last, 'Current Debt', 0) or safe_get(bs_last, 'Current Debt And Capital Lease Obligation', 0)
        divida_longo = safe_get(bs_last, 'Long Term Debt', 0) or safe_get(bs_last, 'Long Term Debt And Capital Lease Obligation', 0)
        divida_total = (divida_curto or 0) + (divida_longo or 0)

        # Caixa
        caixa = safe_get(bs_last, 'Cash And Cash Equivalents', 0) or safe_get(bs_last, 'Cash Cash Equivalents And Short Term Investments', 0)

        # Dívida Líquida
        divida_liquida = divida_total - (caixa or 0)

        # EBITDA
        ebitda = safe_get(inc_last, 'EBITDA', 0) or safe_get(inc_last, 'Normalized EBITDA', 0)

        # Receita
        receita = safe_get(inc_last, 'Total Revenue', 0)

        # Lucro Operacional (EBIT)
        ebit = safe_get(inc_last, 'EBIT', 0) or safe_get(inc_last, 'Operating Income', 0)

        # Despesa com juros
        juros = abs(safe_get(inc_last, 'Interest Expense', 0) or safe_get(inc_last, 'Net Interest Income', 0) or 1)

        # Ativo Circulante / Passivo Circulante
        ativo_circ = safe_get(bs_last, 'Current Assets', 0)
        passivo_circ = safe_get(bs_last, 'Current Liabilities', 0)

        # Patrimônio Líquido
        pl = safe_get(bs_last, 'Stockholders Equity', 0) or safe_get(bs_last, 'Total Equity Gross Minority Interest', 0)

        # Free Cash Flow
        fcf = safe_get(cf_last, 'Free Cash Flow', 0)

        # Lucro Líquido
        lucro = safe_get(inc_last, 'Net Income', 0)

        # === CÁLCULOS ===

        # Dívida Líquida / EBITDA
        div_ebitda = round(divida_liquida / ebitda, 2) if ebitda and ebitda > 0 else None

        # Liquidez Corrente
        liq_corrente = round(ativo_circ / passivo_circ, 2) if passivo_circ and passivo_circ > 0 else None

        # Cobertura de Juros (EBIT / Juros)
        cob_juros = round(ebit / juros, 2) if juros and juros > 0 and ebit else None

        # Margem EBITDA
        margem_ebitda = round((ebitda / receita) * 100, 1) if receita and receita > 0 and ebitda else None

        # ROE
        roe = round((lucro / pl) * 100, 1) if pl and pl > 0 and lucro else None

        # Endividamento (Dívida / PL)
        endividamento = round(divida_total / pl, 2) if pl and pl > 0 else None

        # Market Cap
        try:
            mkt_cap = t.fast_info.market_cap or 0
        except Exception:
            mkt_cap = 0

        return {
            'ticker': ticker,
            'nome': info['nome'],
            'setor': info['setor'],
            'div_ebitda': div_ebitda,
            'liq_corrente': liq_corrente,
            'cob_juros': cob_juros,
            'margem_ebitda': margem_ebitda,
            'roe': roe,
            'endividamento': endividamento,
            'divida_liquida': divida_liquida,
            'caixa': caixa or 0,
            'ebitda': ebitda or 0,
            'fcf': fcf or 0,
            'patrimonio_liquido': pl or 0,
            'market_cap': mkt_cap,
        }

    except Exception as e:
        print(f"    Erro {ticker}: {e}")
        return None


def calcular_score(emp):
    """Calcula score de saúde corporativa (0-100)."""
    score = 0

    # Dívida/EBITDA (30 pontos) — menor é melhor
    de = emp.get('div_ebitda')
    if de is not None:
        if de < 0:
            score += 30  # dívida negativa = mais caixa que dívida
        elif de <= 1:
            score += 28
        elif de <= 2:
            score += 22
        elif de <= 3:
            score += 15
        elif de <= 4:
            score += 8
        elif de <= 5:
            score += 3
        # acima de 5 = 0 pontos

    # Liquidez Corrente (20 pontos)
    lc = emp.get('liq_corrente')
    if lc is not None:
        if lc >= 2.0:
            score += 20
        elif lc >= 1.5:
            score += 16
        elif lc >= 1.0:
            score += 10
        elif lc >= 0.8:
            score += 5
        # abaixo de 0.8 = 0

    # Cobertura de Juros (20 pontos)
    cj = emp.get('cob_juros')
    if cj is not None:
        if cj >= 5:
            score += 20
        elif cj >= 3:
            score += 15
        elif cj >= 1.5:
            score += 10
        elif cj >= 1:
            score += 5
        # abaixo de 1 = 0

    # Margem EBITDA (15 pontos)
    me = emp.get('margem_ebitda')
    if me is not None:
        if me >= 30:
            score += 15
        elif me >= 20:
            score += 12
        elif me >= 10:
            score += 8
        elif me >= 5:
            score += 4
        # abaixo de 5% = 0

    # Free Cash Flow positivo (15 pontos)
    fcf = emp.get('fcf', 0)
    if fcf and fcf > 0:
        score += 15
    elif fcf and fcf > -1e8:
        score += 5

    return min(score, 100)


def semaforo(score):
    if score >= 65:
        return 'verde'
    if score >= 40:
        return 'amarelo'
    return 'vermelho'


# ==================== MAIN ====================
def main():
    if not HAS_YF:
        return

    print("=" * 60)
    print("  RAIO-X CORPORATIVO — Convexa News")
    print("=" * 60)
    print(f"\n  Analisando {len(EMPRESAS)} empresas...\n")

    resultados = []
    erros = 0

    for ticker, info in EMPRESAS.items():
        print(f"  {ticker} ({info['nome']})...", end=' ')
        emp = analisar_empresa(ticker)
        if emp:
            emp['score'] = calcular_score(emp)
            emp['situacao'] = semaforo(emp['score'])
            resultados.append(emp)
            de_str = f"{emp['div_ebitda']:.1f}x" if emp['div_ebitda'] is not None else '—'
            print(f"Score: {emp['score']} | Dív/EBITDA: {de_str} | {emp['situacao'].upper()}")
        else:
            erros += 1
            print("FALHOU")

    # Ordenar por score (pior primeiro pra chamar atenção)
    resultados.sort(key=lambda x: x['score'])

    dados = {
        'atualizado_em': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'fonte': 'Yahoo Finance (Balanços CVM)',
        'total': len(resultados),
        'empresas': resultados,
    }

    with open('raiox_corp.json', 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

    print(f"\n  raiox_corp.json salvo — {len(resultados)} empresas ({erros} erros)")

    # Alertas
    vermelhos = [e for e in resultados if e['situacao'] == 'vermelho']
    if vermelhos:
        print(f"\n  ⚠️  ALERTAS DE RISCO ({len(vermelhos)} empresas):")
        for e in vermelhos:
            de_str = f"{e['div_ebitda']:.1f}x" if e['div_ebitda'] is not None else '—'
            print(f"     🔴 {e['ticker']} ({e['nome']}) — Score {e['score']} | Dív/EBITDA: {de_str}")

    print("\n  Concluído!")


if __name__ == '__main__':
    main()
