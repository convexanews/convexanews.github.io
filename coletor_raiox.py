"""
Coletor Raio-X Bancário — Convexa News
Puxa dados REAIS do IF.data (Banco Central do Brasil)
API REST: https://www3.bcb.gov.br/ifdata/
Gera: raiox.json
"""

import json
import sys
import io
import math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from datetime import datetime

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("ERRO: requests não instalado.")

# IDs dos indicadores no IF.data
IND_BASILEIA = 79664       # Índice de Basileia (decimal, multiplicar por 100)
IND_IMOBILIZACAO = 79662   # Índice de Imobilização (decimal)
IND_PL = 141836            # Patrimônio Líquido (R$ mil)

# Ratings de crédito — VERIFICADOS nas páginas oficiais de RI e agências
# Apenas ratings confirmados em fontes oficiais. Sem rating = não mostrar.
RATINGS = {
    # Verificado: ri.bb.com.br/ratings (Mar/2026)
    'Banco do Brasil':    {'moodys': 'Ba1', 'fitch': 'BB', 'sp': 'BB', 'perspectiva': 'Estável', 'agencia_ref': "Fonte: RI Banco do Brasil (Mar/2026)"},
    # Verificado: Moody's (Jun/2025) + Fitch (Dez/2025)
    'Itaú Unibanco':      {'moodys': 'Ba1', 'fitch': 'BB+', 'sp': '', 'perspectiva': 'Estável', 'agencia_ref': "Moody's (Jun/2025), Fitch (Dez/2025)"},
    # Verificado: Fitch (Dez/2025) BB+ Estável, Moody's Ba1
    'Bradesco':           {'moodys': 'Ba1', 'fitch': 'BB+', 'sp': '', 'perspectiva': 'Estável', 'agencia_ref': "Fitch (Dez/2025), Moody's"},
    # Verificado: Moody's upgrade Out/2025
    'Santander Brasil':   {'moodys': 'Ba1', 'fitch': '', 'sp': '', 'perspectiva': 'Estável', 'agencia_ref': "Moody's (Out/2025)"},
    # Verificado: Moody's upgrade Out/2025
    'Caixa Econômica':    {'moodys': 'Ba1', 'fitch': '', 'sp': '', 'perspectiva': 'Estável', 'agencia_ref': "Moody's (Out/2025)"},
    # Verificado: Moody's + Fitch (Mar/2026 upgrade)
    'BTG Pactual':        {'moodys': 'Ba1', 'fitch': 'BB+', 'sp': '', 'perspectiva': 'Positiva', 'agencia_ref': "Moody's (Out/2025), Fitch (Mar/2026)"},
    # Verificado: Moody's upgrade Out/2025
    'Safra':              {'moodys': 'Ba1', 'fitch': '', 'sp': '', 'perspectiva': 'Estável', 'agencia_ref': "Moody's (Out/2025)"},
    # Verificado: investidores.nu/ratings
    'Nubank':             {'moodys': 'Ba1', 'fitch': '', 'sp': 'BB', 'perspectiva': 'Estável', 'agencia_ref': "Moody's Ba1 + S&P BB (investidores.nu)"},
    # Verificado: investors.inter.co/ratings — Moody's Local AA+ Positiva
    'Inter':              {'moodys': 'AA+.br', 'fitch': '', 'sp': 'AA+ Nacional', 'perspectiva': 'Positiva', 'agencia_ref': "Moody's Local + S&P Nacional (investors.inter.co)"},
    # Verificado: Moody's upgrade Out/2025
    'Sicredi':            {'moodys': 'Ba1', 'fitch': '', 'sp': '', 'perspectiva': 'Positiva', 'agencia_ref': "Moody's (Out/2025)"},
    # Verificado: Moody's upgrade Out/2025
    'ABC Brasil':         {'moodys': 'Ba1', 'fitch': '', 'sp': '', 'perspectiva': 'Positiva', 'agencia_ref': "Moody's (Out/2025)"},
    # Verificado: Moody's upgrade Out/2025
    'Daycoval':           {'moodys': 'Ba1', 'fitch': '', 'sp': '', 'perspectiva': 'Positiva', 'agencia_ref': "Moody's (Out/2025)"},
    # Verificado: Moody's upgrade Out/2025
    'Banco do Nordeste':  {'moodys': 'Ba1', 'fitch': '', 'sp': '', 'perspectiva': 'Positiva', 'agencia_ref': "Moody's (Out/2025)"},
    # Verificado: Moody's upgrade Out/2025
    'Banco da Amazônia':  {'moodys': 'Ba1', 'fitch': '', 'sp': '', 'perspectiva': 'Positiva', 'agencia_ref': "Moody's (Out/2025)"},
    # Verificado: ri.banrisul.com.br/ratings
    'Banrisul':           {'moodys': 'Ba3', 'fitch': 'BB-', 'sp': 'BB-', 'perspectiva': 'Positiva/Estável', 'agencia_ref': "RI Banrisul (Moody's Ba3/Pos, Fitch BB-/Est, S&P BB-/Est)"},
    # Verificado: Fitch B+ Estável
    'BMG':                {'moodys': '', 'fitch': 'B+', 'sp': '', 'perspectiva': 'Estável', 'agencia_ref': "Fitch (B+ Estável)"},
    # Verificado: Moody's upgrade Out/2025
    'Votorantim':         {'moodys': 'Ba1', 'fitch': '', 'sp': '', 'perspectiva': 'Estável', 'agencia_ref': "Moody's (Out/2025)"},
}

# Bancos que queremos (filtro por nome parcial)
BANCOS_ALVO = {
    'ITAU': {'nome_display': 'Itaú Unibanco', 'tipo_display': 'Banco Múltiplo'},
    'BRADESCO': {'nome_display': 'Bradesco', 'tipo_display': 'Banco Múltiplo'},
    'BB': {'nome_display': 'Banco do Brasil', 'tipo_display': 'Banco Público', 'exact': True},
    'SANTANDER': {'nome_display': 'Santander Brasil', 'tipo_display': 'Banco Múltiplo'},
    'CAIXA ECON': {'nome_display': 'Caixa Econômica', 'tipo_display': 'Banco Público'},
    'BTG PACTUAL': {'nome_display': 'BTG Pactual', 'tipo_display': 'Banco de Investimento'},
    'SAFRA': {'nome_display': 'Safra', 'tipo_display': 'Banco Múltiplo'},
    'VOTORANTIM': {'nome_display': 'Votorantim', 'tipo_display': 'Banco Múltiplo'},
    'DAYCOVAL': {'nome_display': 'Daycoval', 'tipo_display': 'Banco Múltiplo'},
    'NU PAGAM': {'nome_display': 'Nubank', 'tipo_display': 'Banco Digital'},
    'INTER': {'nome_display': 'Inter', 'tipo_display': 'Banco Digital', 'exclude': ['INTERCAM', 'INTERNATIONAL', 'INTESA']},
    'BANCO C6': {'nome_display': 'C6 Bank', 'tipo_display': 'Banco Digital'},
    'PICPAY': {'nome_display': 'PicPay', 'tipo_display': 'Banco Digital'},
    'ORIGINAL': {'nome_display': 'Original', 'tipo_display': 'Banco Digital'},
    'NEON': {'nome_display': 'Neon', 'tipo_display': 'Banco Digital'},
    'PAGSEGURO': {'nome_display': 'PagBank (PagSeguro)', 'tipo_display': 'Banco Digital'},
    'AGIBANK': {'nome_display': 'Agibank', 'tipo_display': 'Banco Digital'},
    'MASTER': {'nome_display': 'Banco Master', 'tipo_display': 'Banco Múltiplo'},
    'BANRISUL': {'nome_display': 'Banrisul', 'tipo_display': 'Banco Público'},
    'BRB': {'nome_display': 'BRB', 'tipo_display': 'Banco Público', 'exact': True},
    'BANESTES': {'nome_display': 'Banestes', 'tipo_display': 'Banco Público'},
    'BANESE': {'nome_display': 'Banese', 'tipo_display': 'Banco Público'},
    'BMG': {'nome_display': 'BMG', 'tipo_display': 'Banco Múltiplo'},
    'PINE': {'nome_display': 'Pine', 'tipo_display': 'Banco Comercial'},
    'SOFISA': {'nome_display': 'Sofisa', 'tipo_display': 'Banco Múltiplo'},
    'MERCANTIL DO BRASIL': {'nome_display': 'Mercantil do Brasil', 'tipo_display': 'Banco Múltiplo'},
    'ABC-BRASIL': {'nome_display': 'ABC Brasil', 'tipo_display': 'Banco Múltiplo'},
    'MODAL': {'nome_display': 'Modal', 'tipo_display': 'Banco de Investimento'},
    'RODOBENS': {'nome_display': 'Rodobens', 'tipo_display': 'Banco Múltiplo'},
    'BS2': {'nome_display': 'BS2', 'tipo_display': 'Banco Digital'},
    'BCO DO NORDESTE': {'nome_display': 'Banco do Nordeste', 'tipo_display': 'Banco Público'},
    'BCO DA AMAZONIA': {'nome_display': 'Banco da Amazônia', 'tipo_display': 'Banco Público'},
    'BANPAR': {'nome_display': 'Banpará', 'tipo_display': 'Banco Público'},
    'BCO COOPERATIVO SICREDI': {'nome_display': 'Sicredi', 'tipo_display': 'Cooperativa'},
    'BANCO SICOOB': {'nome_display': 'Sicoob', 'tipo_display': 'Cooperativa'},
    'PAN': {'nome_display': 'Pan', 'tipo_display': 'Banco Múltiplo', 'exclude': ['JAPAN', 'PANAMER']},
}


def match_banco(nome_bcb, keyword, config):
    """Verifica se o nome do BCB corresponde ao banco alvo."""
    nome_up = nome_bcb.upper().strip()
    kw_up = keyword.upper().strip()

    # Match exato: nome deve ser exatamente o keyword
    if config.get('exact'):
        if nome_up != kw_up:
            return False
    else:
        if kw_up not in nome_up:
            return False

    # Checar exclusões
    for ex in config.get('exclude', []):
        if ex.upper() in nome_up:
            return False
    return True


def get_semaforo(basileia):
    if basileia >= 13:
        return 'verde'
    if basileia >= 11:
        return 'amarelo'
    return 'vermelho'


def calc_score(basileia, imobilizacao):
    """Score simplificado baseado nos indicadores oficiais do BCB."""
    score = 0

    # Basileia (60 pontos)
    if basileia >= 17:
        score += 60
    elif basileia >= 15:
        score += 50
    elif basileia >= 13:
        score += 40
    elif basileia >= 11:
        score += 25
    elif basileia >= 8:
        score += 10
    # abaixo de 8 = 0

    # Imobilização (40 pontos) — menor é melhor
    if imobilizacao <= 10:
        score += 40
    elif imobilizacao <= 20:
        score += 30
    elif imobilizacao <= 30:
        score += 20
    elif imobilizacao <= 40:
        score += 10
    # acima de 40 = 0

    return min(score, 100)


def main():
    if not HAS_REQUESTS:
        return

    print("=" * 60)
    print("  RAIO-X BANCÁRIO — Convexa News")
    print("  Fonte: IF.data — Banco Central do Brasil")
    print("=" * 60)

    # 1. Descobrir último período disponível
    print("\n  Buscando dados do BC...")
    resp = requests.get(
        'https://www3.bcb.gov.br/ifdata/rest/relatorios2025a2030',
        headers={'User-Agent': 'Mozilla/5.0'}, timeout=30
    )
    periodos = resp.json()
    ultimo = periodos[-1]['dt']  # pegar o mais recente (último da lista)
    ano = str(ultimo)[:4]
    mes = str(ultimo)[4:]
    print(f"  Período: {mes}/{ano}")

    # 2. Cadastro de instituições
    print("  Baixando cadastro...")
    resp1 = requests.get(
        f'https://www3.bcb.gov.br/ifdata/rest/arquivos?nomeArquivo=ifdata_2025_2030//{ultimo}/cadastro{ultimo}_1009.json',
        headers={'User-Agent': 'Mozilla/5.0'}, timeout=30
    )
    cadastro = resp1.json()
    info = {}
    for item in cadastro:
        eid = int(item['c0'])
        info[eid] = item['c2'].replace(' - PRUDENCIAL', '').strip()

    # 3. Dados do relatório 1 (Resumo)
    print("  Baixando indicadores...")
    resp2 = requests.get(
        f'https://www3.bcb.gov.br/ifdata/rest/arquivos?nomeArquivo=ifdata_2025_2030//{ultimo}/dados{ultimo}_1.json',
        headers={'User-Agent': 'Mozilla/5.0'}, timeout=120
    )
    data = resp2.json()

    # Extrair indicadores
    bancos_raw = {}
    for row in data['values']:
        e = row.get('e')
        for v in row.get('v', []):
            ind = v.get('i')
            val = v.get('v')
            if e not in bancos_raw:
                bancos_raw[e] = {'nome_bcb': info.get(e, '')}
            if ind == IND_BASILEIA and val:
                bancos_raw[e]['basileia'] = round(val * 100, 2)
            elif ind == IND_IMOBILIZACAO and val:
                bancos_raw[e]['imobilizacao'] = round(val * 100, 2)
            elif ind == IND_PL and val:
                bancos_raw[e]['pl'] = val * 1000  # R$ mil -> R$

    # 4. Mapear para bancos alvo (iterar por alvo, buscar nos dados)
    print(f"  Processando {len(BANCOS_ALVO)} bancos...\n")
    resultados = []
    matched = set()

    for keyword, config in BANCOS_ALVO.items():
        # Procurar este banco nos dados do BCB
        found = False
        for e, d in bancos_raw.items():
            nome_bcb = d.get('nome_bcb', '')
            bas = d.get('basileia')
            if not bas:
                continue
            if match_banco(nome_bcb, keyword, config):
                imob = d.get('imobilizacao', 0)
                pl = d.get('pl', 0)
                score = calc_score(bas, imob)
                situacao = get_semaforo(bas)

                # Rating de crédito
                rating_data = RATINGS.get(config['nome_display'], {})

                banco = {
                    'nome': config['nome_display'],
                    'nome_bcb': nome_bcb,
                    'tipo': config['tipo_display'],
                    'basileia': bas,
                    'imobilizacao': imob,
                    'patrimonio_liquido': pl,
                    'score': score,
                    'situacao': situacao,
                    'rating_moodys': rating_data.get('moodys', ''),
                    'rating_fitch': rating_data.get('fitch', ''),
                    'rating_sp': rating_data.get('sp', ''),
                    'rating_perspectiva': rating_data.get('perspectiva', ''),
                    'rating_fonte': rating_data.get('agencia_ref', ''),
                }
                resultados.append(banco)
                matched.add(keyword)
                found = True

                sit_emoji = {'verde': '🟢', 'amarelo': '🟡', 'vermelho': '🔴'}[situacao]
                print(f"  {sit_emoji} {config['nome_display']:<25} Bas={bas:>6.2f}%  Imob={imob:>6.2f}%  Score={score}")
                break
        if not found:
            print(f"  ⚠️  {config['nome_display']:<25} NÃO ENCONTRADO")

    # Ordenar por score
    resultados.sort(key=lambda x: x['score'], reverse=True)

    # Limpar NaN
    def limpar(obj):
        if isinstance(obj, dict):
            return {k: limpar(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [limpar(v) for v in obj]
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return None
        return obj

    dados = limpar({
        'atualizado_em': f'{mes}/{ano} (IF.data BCB)',
        'fonte': 'Banco Central do Brasil — IF.data',
        'periodo': str(ultimo),
        'total': len(resultados),
        'bancos': resultados,
    })

    with open('raiox.json', 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

    verdes = sum(1 for b in resultados if b['situacao'] == 'verde')
    amarelos = sum(1 for b in resultados if b['situacao'] == 'amarelo')
    vermelhos = sum(1 for b in resultados if b['situacao'] == 'vermelho')

    print(f"\n  raiox.json salvo — {len(resultados)} bancos")
    print(f"  Saudável: {verdes} | Atenção: {amarelos} | Risco: {vermelhos}")

    not_found = set(BANCOS_ALVO.keys()) - matched
    if not_found:
        print(f"\n  ⚠️  Não encontrados no BCB: {', '.join(BANCOS_ALVO[k]['nome_display'] for k in not_found)}")

    print("\n  Concluído!")


if __name__ == '__main__':
    main()
