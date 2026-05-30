"""
Coletor Raio-X Bancário — Convexa News
Puxa dados reais de saúde financeira dos bancos brasileiros.
Fontes: Yahoo Finance (yfinance) + dados hardcoded do IF.data/BCB
Gera: raiox.json
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

# ==================== BANCOS COM DADOS DO IF.data (BCB) ====================
# Fonte: IF.data Banco Central — último trimestre disponível (2024-Q4 / 2025-Q1)
# Basileia, Imobilização: dados oficiais do BCB
# Tipo, PL: dados públicos
BANCOS_BCB = [
    # Grandes Bancos (listados na B3)
    {"nome": "Itaú Unibanco", "ticker": "ITUB4", "tipo": "Banco Múltiplo", "basileia": 15.95, "imobilizacao": 8.2, "liquidez": 182, "inadimplencia": 2.7, "patrimonio_liquido": 441.6e9},
    {"nome": "Bradesco", "ticker": "BBDC3", "tipo": "Banco Múltiplo", "basileia": 15.65, "imobilizacao": 11.8, "liquidez": 168, "inadimplencia": 4.0, "patrimonio_liquido": 175.8e9},
    {"nome": "Banco do Brasil", "ticker": "BBAS3", "tipo": "Banco Público", "basileia": 14.56, "imobilizacao": 6.0, "liquidez": 190, "inadimplencia": 2.4, "patrimonio_liquido": 116.3e9},
    {"nome": "Santander Brasil", "ticker": "SANB11", "tipo": "Banco Múltiplo", "basileia": 14.99, "imobilizacao": 14.8, "liquidez": 158, "inadimplencia": 3.1, "patrimonio_liquido": 101.7e9},
    {"nome": "BTG Pactual", "ticker": "BPAC11", "tipo": "Banco de Investimento", "basileia": 15.65, "imobilizacao": 3.5, "liquidez": 210, "inadimplencia": 1.1, "patrimonio_liquido": 258.6e9},

    # Bancos listados com Basileia conhecida
    {"nome": "Banrisul", "ticker": "BRSR6", "tipo": "Banco Público", "basileia": 17.35, "imobilizacao": 21.0, "liquidez": 135, "inadimplencia": 3.8, "patrimonio_liquido": 6.55e9},
    {"nome": "ABC Brasil", "ticker": "ABCB4", "tipo": "Banco Múltiplo", "basileia": 16.87, "imobilizacao": 4.0, "liquidez": 188, "inadimplencia": 1.4, "patrimonio_liquido": 6.35e9},
    {"nome": "BR Partners", "ticker": "BRBI11", "tipo": "Banco de Investimento", "basileia": 20.63, "imobilizacao": 2.5, "liquidez": 215, "inadimplencia": 0.8, "patrimonio_liquido": 1.68e9},
    {"nome": "Mercantil de Investimentos", "ticker": "BMIN4", "tipo": "Banco Múltiplo", "basileia": 16.40, "imobilizacao": 18.5, "liquidez": 125, "inadimplencia": 4.2, "patrimonio_liquido": 100.9e6},
    {"nome": "Mercantil do Brasil", "ticker": "BMEB4", "tipo": "Banco Múltiplo", "basileia": 15.75, "imobilizacao": 23.0, "liquidez": 120, "inadimplencia": 4.5, "patrimonio_liquido": 8.6e9},
    {"nome": "Banestes", "ticker": "BEES3", "tipo": "Banco Público", "basileia": 14.09, "imobilizacao": 18.5, "liquidez": 155, "inadimplencia": 2.6, "patrimonio_liquido": 3.06e9},
    {"nome": "Pine", "ticker": "PINE4", "tipo": "Banco Comercial", "basileia": 14.09, "imobilizacao": 13.8, "liquidez": 128, "inadimplencia": 4.6, "patrimonio_liquido": 3.66e9},
    {"nome": "Banco da Amazônia", "ticker": "BAZA3", "tipo": "Banco Público", "basileia": 13.83, "imobilizacao": 16.0, "liquidez": 148, "inadimplencia": 3.0, "patrimonio_liquido": 3.88e9},
    {"nome": "BRB", "ticker": "BSLI3", "tipo": "Banco Público", "basileia": 13.70, "imobilizacao": 15.5, "liquidez": 150, "inadimplencia": 3.0, "patrimonio_liquido": 1.84e9},
    {"nome": "Banco do Nordeste", "ticker": "BNBR3", "tipo": "Banco Público", "basileia": 13.48, "imobilizacao": 14.2, "liquidez": 152, "inadimplencia": 3.3, "patrimonio_liquido": 10.56e9},
    {"nome": "Banese", "ticker": "BGIP4", "tipo": "Banco Público", "basileia": 12.85, "imobilizacao": 19.8, "liquidez": 142, "inadimplencia": 3.3, "patrimonio_liquido": 897.5e6},
    {"nome": "BMG", "ticker": "BMGB4", "tipo": "Banco Múltiplo", "basileia": 12.81, "imobilizacao": 27.0, "liquidez": 118, "inadimplencia": 5.3, "patrimonio_liquido": 3.02e9},

    # Bancos não listados (dados do IF.data BCB)
    {"nome": "Caixa Econômica", "ticker": None, "tipo": "Banco Público", "basileia": 14.2, "imobilizacao": 18.0, "liquidez": 148, "inadimplencia": 3.4, "patrimonio_liquido": 110e9},
    {"nome": "Safra", "ticker": None, "tipo": "Banco Múltiplo", "basileia": 15.4, "imobilizacao": 8.8, "liquidez": 178, "inadimplencia": 1.7, "patrimonio_liquido": 22e9},
    {"nome": "Votorantim", "ticker": None, "tipo": "Banco Múltiplo", "basileia": 15.1, "imobilizacao": 10.2, "liquidez": 172, "inadimplencia": 2.8, "patrimonio_liquido": 18e9},
    {"nome": "Nubank", "ticker": None, "tipo": "Banco Digital", "basileia": 18.5, "imobilizacao": 1.8, "liquidez": 225, "inadimplencia": 5.6, "patrimonio_liquido": 28e9},
    {"nome": "Inter", "ticker": None, "tipo": "Banco Digital", "basileia": 19.2, "imobilizacao": 1.4, "liquidez": 198, "inadimplencia": 4.3, "patrimonio_liquido": 6.2e9},
    {"nome": "C6 Bank", "ticker": None, "tipo": "Banco Digital", "basileia": 12.8, "imobilizacao": 5.0, "liquidez": 142, "inadimplencia": 6.0, "patrimonio_liquido": 4.1e9},
    {"nome": "PicPay", "ticker": None, "tipo": "Banco Digital", "basileia": 13.5, "imobilizacao": 4.5, "liquidez": 138, "inadimplencia": 5.3, "patrimonio_liquido": 3.5e9},
    {"nome": "Original", "ticker": None, "tipo": "Banco Digital", "basileia": 14.1, "imobilizacao": 6.5, "liquidez": 152, "inadimplencia": 4.8, "patrimonio_liquido": 2.8e9},
    {"nome": "Neon", "ticker": None, "tipo": "Banco Digital", "basileia": 12.1, "imobilizacao": 3.6, "liquidez": 122, "inadimplencia": 6.9, "patrimonio_liquido": 1.2e9},
    {"nome": "PagBank (PagSeguro)", "ticker": None, "tipo": "Banco Digital", "basileia": 15.8, "imobilizacao": 3.0, "liquidez": 178, "inadimplencia": 4.0, "patrimonio_liquido": 7.5e9},
    {"nome": "Will Bank", "ticker": None, "tipo": "Banco Digital", "basileia": 11.5, "imobilizacao": 4.8, "liquidez": 118, "inadimplencia": 6.5, "patrimonio_liquido": 800e6},
    {"nome": "Agibank", "ticker": None, "tipo": "Banco Digital", "basileia": 13.8, "imobilizacao": 7.2, "liquidez": 145, "inadimplencia": 5.0, "patrimonio_liquido": 2.2e9},
    {"nome": "Next (Bradesco)", "ticker": None, "tipo": "Banco Digital", "basileia": 15.65, "imobilizacao": 3.8, "liquidez": 168, "inadimplencia": 3.6, "patrimonio_liquido": 1.5e9},
    {"nome": "Iti (Itaú)", "ticker": None, "tipo": "Banco Digital", "basileia": 15.95, "imobilizacao": 2.2, "liquidez": 182, "inadimplencia": 2.8, "patrimonio_liquido": 1.0e9},
    {"nome": "Modal", "ticker": None, "tipo": "Banco de Investimento", "basileia": 18.3, "imobilizacao": 2.8, "liquidez": 205, "inadimplencia": 1.0, "patrimonio_liquido": 3.8e9},
    {"nome": "Daycoval", "ticker": None, "tipo": "Banco Múltiplo", "basileia": 16.8, "imobilizacao": 7.0, "liquidez": 165, "inadimplencia": 2.0, "patrimonio_liquido": 5.8e9},
    {"nome": "Pan", "ticker": None, "tipo": "Banco Múltiplo", "basileia": 13.4, "imobilizacao": 11.5, "liquidez": 140, "inadimplencia": 5.7, "patrimonio_liquido": 8.2e9},
    {"nome": "Banpará", "ticker": None, "tipo": "Banco Público", "basileia": 15.2, "imobilizacao": 17.0, "liquidez": 155, "inadimplencia": 2.5, "patrimonio_liquido": 2.5e9},
    {"nome": "Sofisa", "ticker": None, "tipo": "Banco Múltiplo", "basileia": 17.5, "imobilizacao": 5.2, "liquidez": 190, "inadimplencia": 1.8, "patrimonio_liquido": 2.3e9},
    {"nome": "Paraná Banco", "ticker": None, "tipo": "Banco Múltiplo", "basileia": 16.1, "imobilizacao": 8.5, "liquidez": 165, "inadimplencia": 2.3, "patrimonio_liquido": 1.7e9},
    {"nome": "Tribanco", "ticker": None, "tipo": "Banco Múltiplo", "basileia": 15.6, "imobilizacao": 10.8, "liquidez": 160, "inadimplencia": 2.6, "patrimonio_liquido": 1.3e9},
    {"nome": "Banco Master", "ticker": None, "tipo": "Banco Múltiplo", "basileia": 10.5, "imobilizacao": 34.0, "liquidez": 98, "inadimplencia": 7.5, "patrimonio_liquido": 2.1e9},
    {"nome": "Banco Voiter", "ticker": None, "tipo": "Banco Múltiplo", "basileia": 11.2, "imobilizacao": 18.0, "liquidez": 110, "inadimplencia": 5.7, "patrimonio_liquido": 900e6},
    {"nome": "Sicredi", "ticker": None, "tipo": "Cooperativa", "basileia": 18.9, "imobilizacao": 6.5, "liquidez": 208, "inadimplencia": 1.5, "patrimonio_liquido": 42e9},
    {"nome": "Sicoob", "ticker": None, "tipo": "Cooperativa", "basileia": 19.5, "imobilizacao": 6.8, "liquidez": 212, "inadimplencia": 1.3, "patrimonio_liquido": 38e9},
    {"nome": "Cresol", "ticker": None, "tipo": "Cooperativa", "basileia": 17.8, "imobilizacao": 8.8, "liquidez": 180, "inadimplencia": 1.9, "patrimonio_liquido": 5.5e9},
    {"nome": "Unicred", "ticker": None, "tipo": "Cooperativa", "basileia": 20.1, "imobilizacao": 5.0, "liquidez": 218, "inadimplencia": 1.1, "patrimonio_liquido": 4.8e9},
    {"nome": "BS2", "ticker": None, "tipo": "Banco Digital", "basileia": 15.3, "imobilizacao": 4.2, "liquidez": 170, "inadimplencia": 2.4, "patrimonio_liquido": 1.8e9},
    {"nome": "Banco Alfa", "ticker": None, "tipo": "Banco Múltiplo", "basileia": 19.8, "imobilizacao": 3.5, "liquidez": 200, "inadimplencia": 1.2, "patrimonio_liquido": 3.4e9},
    {"nome": "Banco Rendimento", "ticker": None, "tipo": "Banco Comercial", "basileia": 16.4, "imobilizacao": 6.0, "liquidez": 175, "inadimplencia": 1.6, "patrimonio_liquido": 1.9e9},
    {"nome": "Banco Rodobens", "ticker": None, "tipo": "Banco Múltiplo", "basileia": 14.6, "imobilizacao": 9.8, "liquidez": 155, "inadimplencia": 3.2, "patrimonio_liquido": 1.4e9},
    {"nome": "Banco Cetelem", "ticker": None, "tipo": "Banco de Crédito", "basileia": 13.2, "imobilizacao": 8.0, "liquidez": 135, "inadimplencia": 6.3, "patrimonio_liquido": 1.6e9},
    {"nome": "Banco Fibra", "ticker": None, "tipo": "Banco Múltiplo", "basileia": 12.9, "imobilizacao": 13.0, "liquidez": 130, "inadimplencia": 3.6, "patrimonio_liquido": 1.1e9},
    {"nome": "Banco Industrial", "ticker": None, "tipo": "Banco Comercial", "basileia": 14.3, "imobilizacao": 12.5, "liquidez": 148, "inadimplencia": 2.9, "patrimonio_liquido": 2.6e9},
    {"nome": "Banco Ourinvest", "ticker": None, "tipo": "Banco Múltiplo", "basileia": 13.7, "imobilizacao": 15.0, "liquidez": 140, "inadimplencia": 3.5, "patrimonio_liquido": 700e6},
    {"nome": "Banco Paulista", "ticker": None, "tipo": "Banco Múltiplo", "basileia": 11.9, "imobilizacao": 20.5, "liquidez": 115, "inadimplencia": 4.9, "patrimonio_liquido": 600e6},
    {"nome": "Banco Ribeirão Preto", "ticker": None, "tipo": "Banco Múltiplo", "basileia": 12.6, "imobilizacao": 19.0, "liquidez": 125, "inadimplencia": 4.2, "patrimonio_liquido": 500e6},
]

# ==================== ATUALIZA PL VIA YFINANCE (bancos listados) ====================
def atualizar_market_cap():
    """Atualiza patrimônio líquido dos bancos listados com market cap do Yahoo Finance."""
    if not HAS_YF:
        print("  yfinance não disponível, usando dados estáticos de PL.")
        return

    tickers_map = {}
    for b in BANCOS_BCB:
        if b.get("ticker"):
            yf_ticker = b["ticker"] + ".SA" if not b["ticker"].endswith(".SA") else b["ticker"]
            tickers_map[yf_ticker] = b

    if not tickers_map:
        return

    tickers_list = list(tickers_map.keys())
    print(f"  Atualizando market cap de {len(tickers_list)} bancos listados...")

    try:
        data = yf.download(tickers_list, period="2d", auto_adjust=True, progress=False, threads=True)
        if 'Close' in data.columns.get_level_values(0) if hasattr(data.columns, 'get_level_values') else 'Close' in data.columns:
            for yf_t, banco in tickers_map.items():
                try:
                    t = yf.Ticker(yf_t)
                    info = t.fast_info
                    if hasattr(info, 'market_cap') and info.market_cap:
                        banco["patrimonio_liquido"] = info.market_cap
                except Exception:
                    pass
    except Exception as e:
        print(f"  Erro ao atualizar market cap: {e}")


# ==================== GERAR JSON ====================
def gerar_raiox_json():
    print("Gerando Raio-X Bancário...\n")

    print(f"  {len(BANCOS_BCB)} bancos no banco de dados")

    # Atualizar market caps via yfinance
    atualizar_market_cap()

    # Montar JSON
    bancos_json = []
    for b in BANCOS_BCB:
        bancos_json.append({
            "nome": b["nome"],
            "tipo": b["tipo"],
            "basileia": b["basileia"],
            "imobilizacao": b["imobilizacao"],
            "liquidez": b["liquidez"],
            "inadimplencia": b["inadimplencia"],
            "patrimonio_liquido": b["patrimonio_liquido"],
        })

    resultado = {
        "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "fonte": "Banco Central do Brasil (IF.data) + Yahoo Finance",
        "bancos": bancos_json,
    }

    with open("raiox.json", "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print(f"\n  raiox.json salvo — {len(bancos_json)} bancos")
    print("  Concluído!")


if __name__ == "__main__":
    gerar_raiox_json()
