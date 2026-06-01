"""
Coletor Raio-X Corporativo — Convexa News
Puxa dados fundamentalistas REAIS do Fundamentus (fonte: balanços CVM).
Gera: raiox_corp.json
"""

import json
import sys
import io
import re
import math
import time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from datetime import datetime

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("ERRO: requests não instalado.")

# ==================== EMPRESAS B3 ====================
# Apenas empresas operacionais (sem bancos, seguradoras — esses estão no Raio-X Bancário)
EMPRESAS = {
    # Petróleo & Gás
    'PETR4': 'Petrobras',
    'PRIO3': 'PetroRio',
    'RECV3': 'PetroRecôncavo',
    'CSAN3': 'Cosan',
    'UGPA3': 'Ultrapar',
    'VBBR3': 'Vibra Energia',
    'RAIZ4': 'Raízen',
    # Mineração & Siderurgia
    'VALE3': 'Vale',
    'CSNA3': 'CSN',
    'GGBR4': 'Gerdau',
    'USIM5': 'Usiminas',
    # Energia Elétrica
    'ELET3': 'Eletrobras',
    'CPFE3': 'CPFL Energia',
    'ENGI11': 'Energisa',
    'EGIE3': 'Engie Brasil',
    'TAEE11': 'Taesa',
    'ENEV3': 'Eneva',
    'CMIG4': 'Cemig',
    'EQTL3': 'Equatorial',
    'NEOE3': 'Neoenergia',
    'SBSP3': 'Sabesp',
    # Varejo & Consumo
    'MGLU3': 'Magazine Luiza',
    'LREN3': 'Lojas Renner',
    'ARZZ3': 'Arezzo',
    'PETZ3': 'Petz',
    'GMAT3': 'Grupo Mateus',
    'ABEV3': 'Ambev',
    # Frigoríficos & Alimentos
    'JBSS3': 'JBS',
    'MRFG3': 'Marfrig',
    'BEEF3': 'Minerva Foods',
    'BRFS3': 'BRF',
    # Saúde
    'RDOR3': 'Rede D\'Or',
    'HAPV3': 'Hapvida',
    'FLRY3': 'Fleury',
    'RADL3': 'Raia Drogasil',
    # Construção
    'CYRE3': 'Cyrela',
    'MRVE3': 'MRV',
    'EZTC3': 'EZTEC',
    'DIRR3': 'Direcional',
    # Logística & Transporte
    'RAIL3': 'Rumo',
    'EMBR3': 'Embraer',
    'RENT3': 'Localiza',
    'MOVI3': 'Movida',
    # Papel & Celulose
    'SUZB3': 'Suzano',
    'KLBN11': 'Klabin',
    # Tecnologia
    'TOTS3': 'Totvs',
    'LWSA3': 'Locaweb',
    # Telecom
    'VIVT3': 'Vivo',
    'TIMS3': 'TIM',
    # Industrial
    'WEGE3': 'WEG',
    # Agro
    'SLCE3': 'SLC Agrícola',
    'SMTO3': 'São Martinho',
    # Educação
    'COGN3': 'Cogna',
    'YDUQ3': 'Yduqs',
    # Shopping
    'MULT3': 'Multiplan',
    'IGTI11': 'Iguatemi',
    # Meios de Pagamento
    'CIEL3': 'Cielo',
}

# Mapeamento de setores
SETORES = {
    'PETR4':'Petróleo & Gás','PRIO3':'Petróleo & Gás','RECV3':'Petróleo & Gás',
    'CSAN3':'Petróleo & Gás','UGPA3':'Petróleo & Gás','VBBR3':'Petróleo & Gás','RAIZ4':'Energia / Agro',
    'VALE3':'Mineração','CSNA3':'Siderurgia','GGBR4':'Siderurgia','USIM5':'Siderurgia',
    'ELET3':'Energia Elétrica','CPFE3':'Energia Elétrica','ENGI11':'Energia Elétrica',
    'EGIE3':'Energia Elétrica','TAEE11':'Energia Elétrica','ENEV3':'Energia Elétrica',
    'CMIG4':'Energia Elétrica','EQTL3':'Energia Elétrica','NEOE3':'Energia Elétrica','SBSP3':'Saneamento',
    'MGLU3':'Varejo','LREN3':'Varejo','ARZZ3':'Varejo','PETZ3':'Varejo','GMAT3':'Varejo','ABEV3':'Bebidas',
    'JBSS3':'Frigoríficos','MRFG3':'Frigoríficos','BEEF3':'Frigoríficos','BRFS3':'Alimentos',
    'RDOR3':'Saúde','HAPV3':'Saúde','FLRY3':'Saúde','RADL3':'Saúde',
    'CYRE3':'Construção','MRVE3':'Construção','EZTC3':'Construção','DIRR3':'Construção',
    'RAIL3':'Logística','EMBR3':'Aeroespacial','RENT3':'Locação','MOVI3':'Locação',
    'SUZB3':'Papel & Celulose','KLBN11':'Papel & Celulose',
    'TOTS3':'Tecnologia','LWSA3':'Tecnologia',
    'VIVT3':'Telecom','TIMS3':'Telecom',
    'WEGE3':'Industrial',
    'SLCE3':'Agro','SMTO3':'Agro',
    'COGN3':'Educação','YDUQ3':'Educação',
    'MULT3':'Shopping','IGTI11':'Shopping',
    'CIEL3':'Meios de Pagamento',
}


def parse_number(text):
    """Converte texto brasileiro pra número: '1.234.567' -> 1234567, '24,2%' -> 24.2"""
    if not text or text == '-':
        return None
    text = text.strip().replace('%', '').replace('.', '').replace(',', '.')
    try:
        return float(text)
    except ValueError:
        return None


def fetch_fundamentus(ticker):
    """Busca dados fundamentalistas de um ticker no Fundamentus."""
    url = f'https://www.fundamentus.com.br/detalhes.php?papel={ticker}'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.encoding = 'latin1'
        html = resp.text

        # Extrair todos os pares label/valor
        cells = re.findall(
            r'<td[^>]*class="label[^"]*"[^>]*>(.*?)</td>\s*<td[^>]*class="data[^"]*"[^>]*>(.*?)</td>',
            html, re.DOTALL
        )

        dados = {}
        for label, val in cells:
            label = re.sub(r'<[^>]+>', '', label).strip()
            val = re.sub(r'<[^>]+>', '', val).strip()
            # Remover caracteres invisíveis (BOM, ?, etc) do início
            label = re.sub(r'^[?\x00-\x1f﻿]+', '', label).strip()
            dados[label] = val

        return dados

    except Exception as e:
        print(f"    Erro HTTP: {e}")
        return None


def analisar_empresa(ticker):
    """Analisa saúde financeira com dados do Fundamentus."""
    nome = EMPRESAS.get(ticker, ticker)
    setor = SETORES.get(ticker, '')

    dados = fetch_fundamentus(ticker)
    if not dados:
        return None

    # Buscar indicadores por chave parcial (evita problemas de encoding)
    def buscar(chave_parcial):
        for k, v in dados.items():
            if chave_parcial.lower() in k.lower():
                return v
        return None

    ev_ebitda = parse_number(buscar('EV / EBITDA'))
    liq_corrente = parse_number(buscar('Liquidez Corr'))
    roe = parse_number(buscar('ROE'))
    margem_ebit = parse_number(buscar('Marg. EBIT'))
    # Margem Líquida: procurar label que contenha "Marg" E "quida"
    margem_liq = None
    for k, v in dados.items():
        if 'Marg' in k and 'quida' in k:
            margem_liq = parse_number(v)
            break
    div_liq_patrim = parse_number(buscar('q / Patrim'))
    roic = parse_number(buscar('ROIC'))
    div_yield = parse_number(buscar('Div. Yield'))
    pl_ratio = parse_number(buscar('P/L'))
    pvp = parse_number(buscar('P/VP'))

    # Valores absolutos
    div_bruta = parse_number(buscar('v. Bruta'))
    div_liquida = parse_number(buscar('v. L'))  # Dív. Líquida
    # Patrimônio Líquido: buscar label que começa com "Patrim"
    patrim_liq = None
    for k, v in dados.items():
        if k.startswith('Patrim') or (len(k) > 3 and 'Patrim' in k and '/' not in k):
            patrim_liq = parse_number(v)
            break
    valor_mercado = parse_number(buscar('Valor de mercado'))
    ebit_val = buscar('EBIT')
    ebit = parse_number(ebit_val) if ebit_val and 'EBITDA' not in str(ebit_val) else None
    # EBIT aparece 2x (anual e trimestral), pegar o primeiro
    for k, v in dados.items():
        if 'EBIT' in k and 'EBITDA' not in k and 'Ativo' not in k:
            ebit = parse_number(v)
            break
    lucro = parse_number(buscar('Lucro'))
    receita = parse_number(buscar('Receita'))
    disponibilidades = parse_number(buscar('Disponibilidades'))
    ult_balanco = buscar('lt balan') or ''

    # Limitar EV/EBITDA absurdo
    if ev_ebitda is not None and (ev_ebitda > 50 or ev_ebitda < -10):
        ev_ebitda = None

    # Calcular EBITDA real a partir de EV e EV/EBITDA
    # EV = Valor de Mercado + Dívida Líquida (Valor da Firma no Fundamentus)
    valor_firma = parse_number(buscar('Valor da firma'))
    ebitda = None
    if valor_firma and ev_ebitda and ev_ebitda > 0:
        ebitda = round(valor_firma / ev_ebitda)

    # Calcular Dív.Líquida / EBITDA (o indicador CORRETO de endividamento)
    div_liq_ebitda = None
    if ebitda and ebitda > 0 and div_liquida is not None:
        div_liq_ebitda = round(div_liquida / ebitda, 2)
        if div_liq_ebitda > 50 or div_liq_ebitda < -10:
            div_liq_ebitda = None

    # Calcular cobertura de juros aproximada
    cob_juros = None
    if ebit and div_bruta and div_bruta > 0:
        juros_estimados = div_bruta * 0.12
        if juros_estimados > 0:
            cob_juros = round(ebit / juros_estimados, 2)
            if cob_juros > 100 or cob_juros < -100:
                cob_juros = None

    return {
        'ticker': ticker,
        'nome': nome,
        'setor': setor,
        'ev_ebitda': round(ev_ebitda, 2) if ev_ebitda else None,
        'div_ebitda': div_liq_ebitda,  # Dív.Líq/EBITDA — o indicador certo
        'ebitda': ebitda,
        'liq_corrente': round(liq_corrente, 2) if liq_corrente else None,
        'cob_juros': cob_juros,
        'margem_ebit': round(margem_ebit, 1) if margem_ebit else None,
        'margem_liquida': round(margem_liq, 1) if margem_liq else None,
        'roe': round(roe, 1) if roe else None,
        'roic': round(roic, 1) if roic else None,
        'div_liq_patrim': round(div_liq_patrim, 2) if div_liq_patrim else None,
        'div_yield': round(div_yield, 1) if div_yield else None,
        'div_bruta': div_bruta,
        'div_liquida': div_liquida,
        'disponibilidades': disponibilidades,
        'patrimonio_liquido': patrim_liq,
        'valor_mercado': valor_mercado,
        'ult_balanco': ult_balanco,
    }


def calcular_score(emp):
    """Calcula score de saúde corporativa (0-100) com dados do Fundamentus."""
    score = 0

    # Dív.Líq/EBITDA (30 pontos) — menor é melhor (indicador real de dívida)
    de = emp.get('div_ebitda')
    if de is not None:
        if de < 0:
            score += 5   # negativo = empresa com prejuízo operacional ou dívida líq negativa
        elif de <= 3:
            score += 30
        elif de <= 5:
            score += 24
        elif de <= 7:
            score += 18
        elif de <= 10:
            score += 10
        elif de <= 15:
            score += 5
        # acima de 15 = 0
    else:
        score += 12  # dado ausente = neutro

    # Liquidez Corrente (20 pontos)
    lc = emp.get('liq_corrente')
    if lc is not None:
        if lc >= 2.0:
            score += 20
        elif lc >= 1.5:
            score += 16
        elif lc >= 1.2:
            score += 12
        elif lc >= 1.0:
            score += 8
        elif lc >= 0.8:
            score += 4
        # abaixo de 0.8 = 0
    else:
        score += 8

    # Cobertura de Juros estimada (15 pontos)
    cj = emp.get('cob_juros')
    if cj is not None:
        if cj >= 5:
            score += 15
        elif cj >= 3:
            score += 12
        elif cj >= 1.5:
            score += 8
        elif cj >= 1:
            score += 4
    else:
        score += 6

    # Margem EBIT (15 pontos)
    me = emp.get('margem_ebit')
    if me is not None:
        if me >= 25:
            score += 15
        elif me >= 15:
            score += 12
        elif me >= 8:
            score += 8
        elif me >= 3:
            score += 4
        elif me < 0:
            score += 0  # margem negativa = prejuízo operacional
    else:
        score += 6

    # ROE (10 pontos)
    roe = emp.get('roe')
    if roe is not None:
        if roe >= 20:
            score += 10
        elif roe >= 12:
            score += 8
        elif roe >= 5:
            score += 5
        elif roe >= 0:
            score += 2
        # negativo = 0
    else:
        score += 4

    # Endividamento Dív Líq / Patrimônio (10 pontos) — menor é melhor
    dlp = emp.get('div_liq_patrim')
    if dlp is not None:
        if dlp < 0:
            score += 10  # dívida líquida negativa = mais caixa que dívida
        elif dlp <= 0.5:
            score += 8
        elif dlp <= 1.0:
            score += 6
        elif dlp <= 2.0:
            score += 3
        # acima de 2 = 0
    else:
        score += 4

    return min(score, 100)


def semaforo(score):
    if score >= 65:
        return 'verde'
    if score >= 40:
        return 'amarelo'
    return 'vermelho'


# ==================== MAIN ====================
def main():
    if not HAS_REQUESTS:
        return

    print("=" * 60)
    print("  RAIO-X CORPORATIVO — Convexa News")
    print("  Fonte: Fundamentus (Balanços CVM)")
    print("=" * 60)
    print(f"\n  Analisando {len(EMPRESAS)} empresas...\n")

    resultados = []
    erros = 0

    for ticker, nome in EMPRESAS.items():
        print(f"  {ticker} ({nome})...", end=' ', flush=True)
        emp = analisar_empresa(ticker)
        if emp:
            emp['score'] = calcular_score(emp)
            emp['situacao'] = semaforo(emp['score'])
            resultados.append(emp)
            ev_str = f"{emp['ev_ebitda']:.1f}x" if emp.get('ev_ebitda') is not None else '—'
            lc_str = f"{emp['liq_corrente']:.2f}" if emp.get('liq_corrente') is not None else '—'
            print(f"Score: {emp['score']} | EV/EBITDA: {ev_str} | Liq: {lc_str} | {emp['situacao'].upper()}")
        else:
            erros += 1
            print("FALHOU")

        time.sleep(0.5)  # Respeitar o servidor

    # Ordenar por score (pior primeiro)
    resultados.sort(key=lambda x: x['score'])

    # Limpar NaN/Infinity
    def limpar_nan(obj):
        if isinstance(obj, dict):
            return {k: limpar_nan(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [limpar_nan(v) for v in obj]
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return None
        return obj

    dados = limpar_nan({
        'atualizado_em': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'fonte': 'Fundamentus (Balanços CVM)',
        'total': len(resultados),
        'empresas': resultados,
    })

    with open('raiox_corp.json', 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

    print(f"\n  raiox_corp.json salvo — {len(resultados)} empresas ({erros} erros)")

    # Resumo
    verdes = [e for e in resultados if e['situacao'] == 'verde']
    amarelos = [e for e in resultados if e['situacao'] == 'amarelo']
    vermelhos = [e for e in resultados if e['situacao'] == 'vermelho']
    print(f"\n  Saudável: {len(verdes)} | Atenção: {len(amarelos)} | Risco: {len(vermelhos)}")

    if vermelhos:
        print(f"\n  ALERTAS DE RISCO:")
        for e in vermelhos:
            ev_str = f"{e['ev_ebitda']:.1f}x" if e.get('ev_ebitda') is not None else '—'
            print(f"     {e['ticker']} ({e['nome']}) — Score {e['score']} | EV/EBITDA: {ev_str}")

    print("\n  Concluído!")


if __name__ == '__main__':
    main()
