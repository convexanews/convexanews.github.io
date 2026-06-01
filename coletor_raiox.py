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

# Ratings: carregados do ratings.json (gerado pelo coletor_ratings.py)
def load_ratings():
    """Carrega ratings do arquivo gerado pelo coletor_ratings.py"""
    try:
        with open('ratings.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('ratings', {})
    except FileNotFoundError:
        print("  ⚠️  ratings.json não encontrado. Rode primeiro: python coletor_ratings.py")
        return {}

RATINGS = load_ratings()

# Bancos por ID fixo no cadastro 1009 (Conglomerado Prudencial)
# IDs verificados no BCB IF.data período 202512
# IDs podem mudar entre períodos — usar busca por nome como principal
BANCOS_ALVO_IDS = {}

# Bancos por nome (match parcial no nome do BCB) — para os que não temos ID fixo
BANCOS_ALVO_NOME = {
    # Grandes bancos
    'ITAU': {'nome': 'Itaú Unibanco', 'tipo': 'Banco Múltiplo', 'exclude': ['ITAU CORPBANCA','ITAU COLOMBIA']},
    'BRADESCO': {'nome': 'Bradesco', 'tipo': 'Banco Múltiplo'},
    'BB': {'nome': 'Banco do Brasil', 'tipo': 'Banco Público', 'exact': True},
    'SANTANDER': {'nome': 'Santander Brasil', 'tipo': 'Banco Múltiplo', 'exclude': ['CONSUMER']},
    'CAIXA ECON': {'nome': 'Caixa Econômica', 'tipo': 'Banco Público'},
    'BTG PACTUAL': {'nome': 'BTG Pactual', 'tipo': 'Banco de Investimento'},
    'SAFRA': {'nome': 'Safra', 'tipo': 'Banco Múltiplo', 'exclude': ['GERAL']},
    'VOTORANTIM': {'nome': 'Votorantim', 'tipo': 'Banco Múltiplo', 'exact': True},
    'DAYCOVAL': {'nome': 'Daycoval', 'tipo': 'Banco Múltiplo'},
    'BANRISUL': {'nome': 'Banrisul', 'tipo': 'Banco Público', 'exclude': ['COOPERATIVA']},
    'MERCANTIL DO BRASIL': {'nome': 'Mercantil do Brasil', 'tipo': 'Banco Múltiplo'},
    'ABC-BRASIL': {'nome': 'ABC Brasil', 'tipo': 'Banco Múltiplo'},
    'BRB': {'nome': 'BRB', 'tipo': 'Banco Público', 'exact': True},
    # Digitais
    'NU PAGAM': {'nome': 'Nubank', 'tipo': 'Banco Digital'},
    'INTER': {'nome': 'Inter', 'tipo': 'Banco Digital', 'exclude': ['INTERCAM', 'INTERNATIONAL', 'INTESA', 'INTERESTADOS']},
    'BANCO C6': {'nome': 'C6 Bank', 'tipo': 'Banco Digital'},
    'PICPAY': {'nome': 'PicPay', 'tipo': 'Banco Digital'},
    'ORIGINAL': {'nome': 'Original', 'tipo': 'Banco Digital'},
    'NEON': {'nome': 'Neon', 'tipo': 'Banco Digital'},
    'PAGSEGURO': {'nome': 'PagBank (PagSeguro)', 'tipo': 'Banco Digital'},
    'AGIBANK': {'nome': 'Agibank', 'tipo': 'Banco Digital'},
    'MASTER': {'nome': 'Banco Master', 'tipo': 'Banco Múltiplo'},
    # Públicos
    'BANESTES': {'nome': 'Banestes', 'tipo': 'Banco Público'},
    'BMG': {'nome': 'BMG', 'tipo': 'Banco Múltiplo'},
    'PINE': {'nome': 'Pine', 'tipo': 'Banco Comercial'},
    'SOFISA': {'nome': 'Sofisa', 'tipo': 'Banco Múltiplo'},
    'RODOBENS': {'nome': 'Rodobens', 'tipo': 'Banco Múltiplo'},
    'BS2': {'nome': 'BS2', 'tipo': 'Banco Digital'},
    'BCO DO NORDESTE': {'nome': 'Banco do Nordeste', 'tipo': 'Banco Público'},
    'BCO DA AMAZONIA': {'nome': 'Banco da Amazônia', 'tipo': 'Banco Público'},
    'BANCO PAN': {'nome': 'Pan', 'tipo': 'Banco Múltiplo'},
    # Cooperativas
    'BCO COOPERATIVO SICREDI': {'nome': 'Sicredi', 'tipo': 'Cooperativa'},
    'BANCO SICOOB': {'nome': 'Sicoob', 'tipo': 'Cooperativa'},
}


def match_banco(nome_bcb, keyword, config):
    """Verifica se o nome do BCB corresponde ao banco alvo."""
    nome_up = nome_bcb.upper().strip()
    kw_up = keyword.upper().strip()

    # Match exato no início (ex: "BB -" deve ser o início do nome)
    if config.get('exact_start'):
        if not nome_up.startswith(kw_up):
            return False
    elif config.get('exact'):
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

    # 4. Mapear por nome
    print(f"  Processando {len(BANCOS_ALVO_NOME)} bancos...\n")
    resultados = []

    for keyword, config in BANCOS_ALVO_NOME.items():
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
                rating_data = RATINGS.get(config['nome'], {})

                banco = {
                    'nome': config['nome'],
                    'nome_bcb': nome_bcb,
                    'tipo': config['tipo'],
                    'basileia': bas,
                    'imobilizacao': imob,
                    'patrimonio_liquido': pl,
                    'score': score,
                    'situacao': situacao,
                    'rating_moodys': rating_data.get('moodys', ''),
                    'rating_fitch': rating_data.get('fitch', ''),
                    'rating_sp': rating_data.get('sp', ''),
                    'rating_perspectiva': rating_data.get('perspectiva', ''),
                    'rating_fonte': rating_data.get('fonte', ''),
                }
                resultados.append(banco)
                found = True
                sit_emoji = {'verde': '🟢', 'amarelo': '🟡', 'vermelho': '🔴'}[situacao]
                print(f"  {sit_emoji} {config['nome']:<25} Bas={bas:>6.2f}%  Imob={imob:>6.2f}%  Score={score}")
                break
        if not found:
            print(f"  ⚠️  {config['nome']:<25} NÃO ENCONTRADO")

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

    all_names = {c['nome'] for c in BANCOS_ALVO_IDS.values()} | {c['nome'] for c in BANCOS_ALVO_NOME.values()}
    found_names = {b['nome'] for b in resultados}
    not_found = all_names - found_names
    if not_found:
        print(f"\n  ⚠️  Não encontrados no BCB: {', '.join(not_found)}")

    print("\n  Concluído!")


if __name__ == '__main__':
    main()
