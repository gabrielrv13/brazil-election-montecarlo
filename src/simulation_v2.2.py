"""
brazil-election-montecarlo v2.2
================================
Monte Carlo Simulation for Brazil's 2026 Presidential Election

NEW in v2.2:
- Rejection index as electoral ceiling
- Rejection-based vote transfer in 2nd round
- Comprehensive validation warnings
- Enhanced visualizations

License: MIT
"""

import numpy as np
import pandas as pd
import pymc as pm
import arviz as az
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import date

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)
np.random.seed(42)

DATA_ELEICAO = date(2026, 10, 4)
DATA_ATUAL = date.today()

def carregar_pesquisas():
    csv_path = Path("data/pesquisas.csv")
    if not csv_path.exists():
        raise FileNotFoundError(f"Arquivo {csv_path} não encontrado!")
    df = pd.read_csv(csv_path)
    required_cols = ["candidato", "intencao_voto_pct", "desvio_padrao_pct"]
    missing = set(required_cols) - set(df.columns)
    if missing:
        raise ValueError(f"Colunas faltando: {missing}")
    tem_rejeicao = "rejeicao_pct" in df.columns
    candidatos = df["candidato"].tolist()
    votos_media = df["intencao_voto_pct"].values
    desvio_base = df["desvio_padrao_pct"].mean()
    if tem_rejeicao:
        rejeicao = df["rejeicao_pct"].values
        print(f"\n📋 Dados carregados (COM rejeição)")
    else:
        rejeicao = np.zeros(len(candidatos))
        print(f"\n📋 Dados carregados (SEM rejeição)")
        print("   ⚠️  Adicione coluna 'rejeicao_pct' para usar teto eleitoral")
    return candidatos, votos_media, rejeicao, desvio_base

CANDIDATOS, VOTOS_MEDIA, REJEICAO, DESVIO_BASE = carregar_pesquisas()
N_SIM = 40_000

def gerar_cores(n):
    cores = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6", "#34495e", "#95a5a6"]
    if n <= len(cores):
        return cores[:n]
    import matplotlib.cm as cm
    cmap = cm.get_cmap('tab10')
    return [cmap(i / n) for i in range(n)]

CORES = gerar_cores(len(CANDIDATOS))

def calcular_desvio_ajustado():
    dias = (DATA_ELEICAO - DATA_ATUAL).days
    if dias < 0:
        return DESVIO_BASE
    return max(DESVIO_BASE, DESVIO_BASE * np.sqrt(dias / 30))

DESVIO = calcular_desvio_ajustado()
print(f"\n📅 Dias até eleição: {(DATA_ELEICAO - DATA_ATUAL).days}")
print(f"📊 Desvio ajustado: {DESVIO:.2f}% (base: {DESVIO_BASE:.2f}%)")

def validar_viabilidade():
    print("\n" + "=" * 60)
    print("  ANÁLISE DE VIABILIDADE ELEITORAL")
    print("=" * 60)
    validos = [c for c in CANDIDATOS if "Brancos" not in c and "Nulos" not in c]
    for cand in validos:
        idx = CANDIDATOS.index(cand)
        rej = REJEICAO[idx]
        teto = 100 - rej
        if rej > 50:
            print(f"\n❌ {cand}:")
            print(f"   Rejeição: {rej:.1f}% (INVIÁVEL)")
            print(f"   Teto: {teto:.1f}%")
            print(f"   ⚠️  Nenhum presidente foi eleito com >50% rejeição")
        elif rej > 45:
            print(f"\n⚠️  {cand}:")
            print(f"   Rejeição: {rej:.1f}% (próximo ao limite)")
            print(f"   Teto: {teto:.1f}%")
        elif rej > 0:
            print(f"\n✅ {cand}:")
            print(f"   Rejeição: {rej:.1f}% (viável)")
            print(f"   Teto: {teto:.1f}%")
    print("=" * 60)

validar_viabilidade()

def aplicar_teto_rejeicao(votos, rejeicao_array):
    tetos = 100 - rejeicao_array
    ultrapassou = votos > tetos[np.newaxis, :]
    votos_lim = np.minimum(votos, tetos[np.newaxis, :])
    info = {}
    for i, cand in enumerate(CANDIDATOS):
        if "Brancos" not in cand and "Nulos" not in cand and rejeicao_array[i] > 0:
            n_lim = ultrapassou[:, i].sum()
            if n_lim > 0:
                info[cand] = {
                    'n_simulacoes_limitadas': int(n_lim),
                    'pct_simulacoes_limitadas': float((n_lim / len(votos)) * 100),
                    'teto': float(tetos[i]),
                    'rejeicao': float(rejeicao_array[i])
                }
    return votos_lim, info

def construir_modelo():
    print("\n[1/4] Construindo modelo Bayesiano...")
    fator = 100 / DESVIO
    alphas = VOTOS_MEDIA * fator
    with pm.Model() as modelo:
        votos_prop = pm.Dirichlet("votos_proporcao", a=alphas, shape=len(CANDIDATOS))
        for i, cand in enumerate(CANDIDATOS):
            var = cand.replace(" ", "_").replace("/", "_").replace("-", "_")
            pm.Deterministic(var, votos_prop[i] * 100)
        trace = pm.sample(draws=10_000, tune=2_000, chains=4, return_inferencedata=True, random_seed=42)
    print("    OK")
    return trace

def simular_primeiro_turno():
    print("\n[2/4] Simulando 1º turno com TETO DE REJEIÇÃO...")
    fator = 100 / DESVIO
    alphas = VOTOS_MEDIA * fator
    proporcoes = np.random.dirichlet(alphas, size=N_SIM)
    votos_norm = proporcoes * 100
    indices_val = [i for i, c in enumerate(CANDIDATOS) if "Brancos" not in c and "Nulos" not in c]
    cands_val = [CANDIDATOS[i] for i in indices_val]
    validos = votos_norm[:, indices_val]
    validos_norm = validos / validos.sum(axis=1, keepdims=True) * 100
    rej_val = REJEICAO[indices_val]
    validos_teto, info_lim = aplicar_teto_rejeicao(validos_norm, rej_val)
    validos_final = validos_teto / validos_teto.sum(axis=1, keepdims=True) * 100
    idx_venc = np.argmax(validos_final, axis=1)
    vencedores = np.array(cands_val)[idx_venc]
    data = {}
    for i, cand in enumerate(CANDIDATOS):
        data[cand] = votos_norm[:, i]
    for i, cand in enumerate(cands_val):
        data[f"{cand}_val"] = validos_final[:, i]
    data["vencedor"] = vencedores
    data["tem_2turno"] = validos_final.max(axis=1) < 50
    df = pd.DataFrame(data)
    df.to_csv(OUTPUT_DIR / "resultados_1turno_v2.2.csv", index=False)
    if info_lim:
        print("\n    📉 Impacto do teto:")
        for c, i in info_lim.items():
            print(f"       {c}: {i['pct_simulacoes_limitadas']:.1f}% limitadas (teto: {i['teto']:.1f}%)")
    print("    OK")
    return df, info_lim

def simular_segundo_turno():
    print("\n[3/4] Simulando 2º turno com TRANSFERÊNCIA POR REJEIÇÃO...")
    validos = [c for c in CANDIDATOS if "Brancos" not in c and "Nulos" not in c]
    if len(validos) < 2:
        return pd.DataFrame(), {}
    c1, c2 = validos[0], validos[1]
    i1, i2 = CANDIDATOS.index(c1), CANDIDATOS.index(c2)
    r1, r2 = REJEICAO[i1], REJEICAO[i2]
    e1, e2 = 100 - r1, 100 - r2
    print(f"    {c1}: rejeição {r1:.1f}% → espaço {e1:.1f}%")
    print(f"    {c2}: rejeição {r2:.1f}% → espaço {e2:.1f}%")
    total_e = e1 + e2
    p1 = e1 / total_e if total_e > 0 else 0.5
    p2 = e2 / total_e if total_e > 0 else 0.5
    print(f"    Transferência: {p1*100:.1f}% → {c1}, {p2*100:.1f}% → {c2}")
    idx_out = [i for i, c in enumerate(CANDIDATOS) if c not in [c1, c2] and "Brancos" not in c and "Nulos" not in c]
    v1 = np.random.normal(VOTOS_MEDIA[i1], DESVIO, N_SIM)
    v2 = np.random.normal(VOTOS_MEDIA[i2], DESVIO, N_SIM)
    vout = sum(VOTOS_MEDIA[i] for i in idx_out)
    outros = np.random.normal(vout, DESVIO, N_SIM)
    conc = [p1 * 80, p2 * 80, 20]
    transf = np.random.dirichlet(conc, N_SIM)
    v1 = np.maximum(v1 + outros * transf[:, 0], 0)
    v2 = np.maximum(v2 + outros * transf[:, 1], 0)
    v1 = np.minimum(v1, e1)
    v2 = np.minimum(v2, e2)
    tot = v1 + v2
    p1_final = v1 / tot * 100
    p2_final = v2 / tot * 100
    df = pd.DataFrame({
        f"{c1}_2T": p1_final,
        f"{c2}_2T": p2_final,
        "vencedor_2T": np.where(p1_final > p2_final, c1, c2),
        "diferenca": np.abs(p1_final - p2_final),
    })
    df.to_csv(OUTPUT_DIR / "resultados_2turno_v2.2.csv", index=False)
    print("    OK")
    return df, {}

def relatorio(df1, df2, info_lim_1t, info_lim_2t):
    sep = "=" * 60
    print(f"\n{sep}\n  RELATÓRIO v2.2\n{sep}")
    print("\n📊 ÍNDICE DE REJEIÇÃO:")
    validos = [c for c in CANDIDATOS if "Brancos" not in c and "Nulos" not in c]
    for c in validos:
        idx = CANDIDATOS.index(c)
        rej = REJEICAO[idx]
        teto = 100 - rej
        st = "❌" if rej > 50 else ("⚠️" if rej > 45 else ("✅" if rej > 0 else "  "))
        print(f"  {st} {c:20s} Rej: {rej:5.1f}% → Teto: {teto:5.1f}%")
    print("\n📊 1º TURNO:")
    for c in CANDIDATOS:
        print(f"  {c:22s} {df1[c].mean():5.2f}%")
    pv = df1["vencedor"].value_counts() / N_SIM * 100
    print("\n🏆 Prob. Vitória 1T:")
    for c, p in pv.items():
        print(f"  {c:22s} {p:.2f}%")
    if not df2.empty:
        print("\n📊 2º TURNO:")
        for col in df2.columns:
            if "_2T" in col and col != "vencedor_2T":
                print(f"  {col.replace('_2T', ''):20s} {df2[col].mean():5.2f}%")
        p2v = df2["vencedor_2T"].value_counts() / N_SIM * 100
        print("\n🏆 Prob. Vitória 2T:")
        for c, p in p2v.items():
            print(f"  {c:22s} {p:.2f}%")
    print(sep)
    return pv, p2v if not df2.empty else pd.Series(), 0

def graficos(df1, df2, trace, pv, p2v, p2t, info_lim_1t, info_lim_2t):
    print("\n[4/4] Gerando visualizações...")
    plt.style.use("seaborn-v0_8-whitegrid")
    fig = plt.figure(figsize=(20, 14))
    gs = fig.add_gridspec(3, 4, hspace=0.40, wspace=0.32)
    validos = [c for c in CANDIDATOS if "Brancos" not in c and "Nulos" not in c]
    
    # Distribuições 1T
    ax = fig.add_subplot(gs[0, :2])
    for i, c in enumerate(CANDIDATOS):
        ax.hist(df1[c], bins=60, alpha=0.6, label=c, color=CORES[i], edgecolor="black", lw=0.3)
    ax.set_title("Distribuição 1º Turno [v2.2: Com Rejeição]", fontsize=13, fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    
    # Rejeição
    ax = fig.add_subplot(gs[0, 2])
    cands_plot, rej_plot, cores_rej = [], [], []
    for c in validos:
        idx = CANDIDATOS.index(c)
        if REJEICAO[idx] > 0:
            cands_plot.append(c)
            rej_plot.append(REJEICAO[idx])
            cores_rej.append('#e74c3c' if REJEICAO[idx] > 50 else ('#f39c12' if REJEICAO[idx] > 45 else '#27ae60'))
    if cands_plot:
        ax.barh(range(len(cands_plot)), rej_plot, color=cores_rej, alpha=0.7)
        ax.axvline(50, color='red', ls='--', lw=2, label='Limite 50%')
        ax.set_yticks(range(len(cands_plot)))
        ax.set_yticklabels(cands_plot, fontsize=9)
        ax.set_title("Índice de Rejeição", fontweight="bold")
        ax.legend(fontsize=8)
        for i, (r, c) in enumerate(zip(rej_plot, cands_plot)):
            ax.text(r + 1, i, f"{r:.0f}% → {100-r:.0f}%", va='center', fontsize=8)
    ax.grid(alpha=0.3, axis='x')
    
    plt.suptitle(f"Eleições Brasil 2026 — v2.2: Teto de Rejeição", fontsize=13, fontweight="bold", y=0.998)
    out = OUTPUT_DIR / "simulacao_eleicoes_brasil_2026_v2.2.png"
    plt.savefig(out, dpi=300, bbox_inches="tight")
    print(f"    Salvo: {out}")
    plt.close()

if __name__ == "__main__":
    print("=" * 60)
    print("  BRAZIL ELECTION MONTE CARLO — v2.2")
    print("  NEW: Rejection Index")
    print("=" * 60)
    trace = construir_modelo()
    df1, info1 = simular_primeiro_turno()
    df2, info2 = simular_segundo_turno()
    pv, p2v, p2t = relatorio(df1, df2, info1, info2)
    graficos(df1, df2, trace, pv, p2v, p2t, info1, info2)
    print("\n✅ v2.2 Concluído!")
