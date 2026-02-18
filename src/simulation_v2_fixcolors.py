"""
brazil-election-montecarlo v2.1.1 (CORES CORRIGIDAS)
====================================================
Monte Carlo Simulation for Brazil's 2026 Presidential Election

License: MIT
"""

import numpy as np
import pandas as pd
import pymc as pm
import arviz as az
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime, date

# ─── CONFIG ───────────────────────────────────────────────────────────────────

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)
np.random.seed(42)

DATA_ELEICAO = date(2026, 10, 4)
DATA_ATUAL = date.today()


# ─── CARREGAR DADOS DAS PESQUISAS ─────────────────────────────────────────────

def carregar_pesquisas():
    """Carrega dados de pesquisas eleitorais do arquivo CSV."""
    csv_path = Path("data/pesquisas.csv")
    
    if not csv_path.exists():
        raise FileNotFoundError(f"Arquivo {csv_path} não encontrado!")
    
    df = pd.read_csv(csv_path)
    
    required_cols = ["candidato", "intencao_voto_pct", "desvio_padrao_pct"]
    missing = set(required_cols) - set(df.columns)
    if missing:
        raise ValueError(f"Colunas faltando no CSV: {missing}")
    
    # NÃO ordenar alfabeticamente - manter ordem do CSV
    candidatos = df["candidato"].tolist()
    votos_media = df["intencao_voto_pct"].values
    desvio_base = df["desvio_padrao_pct"].mean()
    
    print(f"\n📋 Dados carregados de {csv_path}")
    if 'data' in df.columns:
        print(f"   Data da pesquisa: {df['data'].iloc[0]}")
    if 'fonte' in df.columns:
        print(f"   Fonte: {df['fonte'].iloc[0]}")
    
    return candidatos, votos_media, desvio_base


CANDIDATOS, VOTOS_MEDIA, DESVIO_BASE = carregar_pesquisas()
N_SIM = 40_000

# Gera cores dinamicamente para qualquer número de candidatos
def gerar_cores(n):
    """Gera cores distintas para N candidatos."""
    cores_base = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6", "#34495e", "#95a5a6"]
    if n <= len(cores_base):
        return cores_base[:n]
    # Se precisar de mais cores, gera usando colormap
    import matplotlib.cm as cm
    cmap = cm.get_cmap('tab10')
    return [cmap(i / n) for i in range(n)]

CORES = gerar_cores(len(CANDIDATOS))


# ─── INCERTEZA TEMPORAL ───────────────────────────────────────────────────────

def calcular_desvio_ajustado():
    dias_restantes = (DATA_ELEICAO - DATA_ATUAL).days
    if dias_restantes < 0:
        return DESVIO_BASE
    fator_temporal = np.sqrt(dias_restantes / 30)
    return max(DESVIO_BASE, DESVIO_BASE * fator_temporal)


DESVIO = calcular_desvio_ajustado()

print(f"\n📅 Dias até a eleição: {(DATA_ELEICAO - DATA_ATUAL).days}")
print(f"📊 Desvio padrão ajustado: {DESVIO:.2f}% (base: {DESVIO_BASE:.2f}%)")


# ─── MODELO BAYESIANO COM DIRICHLET ───────────────────────────────────────────

def construir_modelo():
    print("\n[1/4] Construindo modelo Bayesiano com PyMC (Dirichlet)...")
    
    fator_concentracao = 100 / DESVIO
    alphas = VOTOS_MEDIA * fator_concentracao
    
    with pm.Model() as modelo:
        votos_proporcao = pm.Dirichlet("votos_proporcao", a=alphas, shape=len(CANDIDATOS))
        
        for i, cand in enumerate(CANDIDATOS):
            var_name = cand.replace(" ", "_").replace("/", "_")
            pm.Deterministic(var_name, votos_proporcao[i] * 100)
        
        trace = pm.sample(
            draws=10_000,
            tune=2_000,
            chains=4,
            return_inferencedata=True,
            random_seed=42,
        )
    
    print("    OK — 40.000 amostras MCMC geradas")
    return trace


# ─── 1º TURNO COM DIRICHLET ───────────────────────────────────────────────────

def simular_primeiro_turno():
    print("\n[2/4] Simulando 1º turno (40.000 iterações) — Dirichlet...")
    
    fator_concentracao = 100 / DESVIO
    alphas = VOTOS_MEDIA * fator_concentracao
    
    proporcoes = np.random.dirichlet(alphas, size=N_SIM)
    votos_norm = proporcoes * 100
    
    # Identifica índices de candidatos válidos
    indices_validos = [i for i, c in enumerate(CANDIDATOS) 
                      if "Brancos" not in c and "Nulos" not in c]
    candidatos_validos = [CANDIDATOS[i] for i in indices_validos]
    
    # Calcula votos válidos
    validos = votos_norm[:, indices_validos]
    validos_norm = validos / validos.sum(axis=1, keepdims=True) * 100
    
    # Identifica vencedor
    idx_vencedor_local = np.argmax(validos, axis=1)
    vencedores = np.array(candidatos_validos)[idx_vencedor_local]
    
    # Cria DataFrame
    data = {}
    for i, cand in enumerate(CANDIDATOS):
        data[cand] = votos_norm[:, i]
    
    for i, cand in enumerate(candidatos_validos):
        data[f"{cand}_val"] = validos_norm[:, i]
    
    data["vencedor"] = vencedores
    data["tem_2turno"] = validos_norm.max(axis=1) < 50
    
    df = pd.DataFrame(data)
    df.to_csv(OUTPUT_DIR / "resultados_1turno_v2.csv", index=False)
    print("    OK")
    return df


# ─── 2º TURNO COM DIRICHLET ───────────────────────────────────────────────────

def simular_segundo_turno():
    print("\n[3/4] Simulando 2º turno (top 2 candidatos) — Dirichlet...")
    
    candidatos_validos = [c for c in CANDIDATOS if "Brancos" not in c and "Nulos" not in c]
    
    if len(candidatos_validos) < 2:
        print("    ⚠️  Menos de 2 candidatos válidos, pulando 2º turno")
        return pd.DataFrame()
    
    cand1, cand2 = candidatos_validos[0], candidatos_validos[1]
    idx1 = CANDIDATOS.index(cand1)
    idx2 = CANDIDATOS.index(cand2)
    
    idx_outros = [i for i, c in enumerate(CANDIDATOS) 
                  if c not in [cand1, cand2] and "Brancos" not in c and "Nulos" not in c]
    
    voto1 = np.random.normal(VOTOS_MEDIA[idx1], DESVIO, size=N_SIM)
    voto2 = np.random.normal(VOTOS_MEDIA[idx2], DESVIO, size=N_SIM)
    
    votos_outros = sum(VOTOS_MEDIA[i] for i in idx_outros)
    outros = np.random.normal(votos_outros, DESVIO, size=N_SIM)
    
    transferencias = np.random.dirichlet([40, 35, 25], size=N_SIM)
    t1 = transferencias[:, 0]
    t2 = transferencias[:, 1]
    
    v1 = np.maximum(voto1 + outros * t1, 0)
    v2 = np.maximum(voto2 + outros * t2, 0)
    
    tot = v1 + v2
    p1 = v1 / tot * 100
    p2 = v2 / tot * 100
    
    df = pd.DataFrame({
        f"{cand1}_2T": p1,
        f"{cand2}_2T": p2,
        "vencedor_2T": np.where(p1 > p2, cand1, cand2),
        "diferenca": np.abs(p1 - p2),
    })
    
    df.to_csv(OUTPUT_DIR / "resultados_2turno_v2.csv", index=False)
    print("    OK")
    return df


# ─── RELATÓRIO ────────────────────────────────────────────────────────────────

def relatorio(df1, df2):
    sep = "=" * 60
    print(f"\n{sep}\n  RELATÓRIO — ELEIÇÕES BRASIL 2026 [v2.1.1]\n{sep}")
    print("\n📊 1º TURNO — votos totais:")
    for cand in CANDIDATOS:
        p5, p95 = df1[cand].quantile([0.05, 0.95])
        print(f"  {cand:22s} {df1[cand].mean():5.2f}%  IC90%:[{p5:.2f}–{p95:.2f}%]")
    
    pv = df1["vencedor"].value_counts() / N_SIM * 100
    print("\n🏆 Prob. vitória 1º turno:")
    for c, p in pv.items():
        print(f"  {c:22s} {p:.2f}%")
    
    p2t = df1["tem_2turno"].mean() * 100
    print(f"\n📌 Prob. 2º turno : {p2t:.2f}%")
    
    candidatos_validos = [c for c in CANDIDATOS if "Brancos" not in c and "Nulos" not in c]
    lider = candidatos_validos[0]
    if f"{lider}_val" in df1.columns:
        prob_lider_1t = (df1[f"{lider}_val"] > 50).mean() * 100
        print(f"🎯 {lider} vence 1T : {prob_lider_1t:.2f}%")
    
    if not df2.empty:
        p2v = df2["vencedor_2T"].value_counts() / N_SIM * 100
        cols_2t = [c for c in df2.columns if "_2T" in c and c != "vencedor_2T"]
        
        print(f"\n📊 2º TURNO:")
        for col in cols_2t:
            cand = col.replace("_2T", "")
            print(f"  {cand:20s} {df2[col].mean():5.2f}% ± {df2[col].std():.2f}%")
        
        print("\n🏆 Prob. vitória 2º turno:")
        for c, p in p2v.items():
            print(f"  {c:22s} {p:.2f}%")
        
        print(f"\n⚠️  Disputa <3pp : {(df2['diferenca'] < 3).mean() * 100:.2f}% dos cenários")
    
    print(sep)
    return pv, p2v if not df2.empty else pd.Series(), p2t


# ─── VISUALIZAÇÕES (COMPLETAS) ────────────────────────────────────────────────

def graficos(df1, df2, trace, pv, p2v, p2t):
    print("\n[4/4] Gerando visualizações...")
    plt.style.use("seaborn-v0_8-whitegrid")
    fig = plt.figure(figsize=(20, 14))
    gs = fig.add_gridspec(3, 4, hspace=0.38, wspace=0.30)
    
    candidatos_validos = [c for c in CANDIDATOS if "Brancos" not in c and "Nulos" not in c]
    
    # Certifica que temos cores suficientes
    cores_candidatos = CORES[:len(CANDIDATOS)]
    
    # 1. Distribuições 1T
    ax = fig.add_subplot(gs[0, :2])
    for i, cand in enumerate(CANDIDATOS):
        ax.hist(df1[cand], bins=60, alpha=0.6, label=cand,
                color=cores_candidatos[i], edgecolor="black", lw=0.3)
    ax.set_title("Distribuição de Votos — 1º Turno", fontsize=13, fontweight="bold")
    ax.set_xlabel("% de Votos", fontsize=11)
    ax.set_ylabel("Frequência", fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    
    # 2. Probabilidades 1T
    ax = fig.add_subplot(gs[0, 2])
    ps = pv.sort_values(ascending=True)
    # Mapeia cores para cada candidato vencedor
    colors_bar = []
    for c in ps.index:
        if c in CANDIDATOS:
            colors_bar.append(cores_candidatos[CANDIDATOS.index(c)])
        else:
            colors_bar.append("#95a5a6")
    ax.barh(range(len(ps)), ps.values, color=colors_bar)
    ax.set_yticks(range(len(ps)))
    ax.set_yticklabels(ps.index, fontsize=9)
    ax.set_xlabel("Probabilidade (%)", fontsize=10)
    ax.set_title("Prob. Vitória\n1º Turno", fontweight="bold")
    for i, v in enumerate(ps.values):
        ax.text(v + 0.5, i, f"{v:.1f}%", va="center", fontsize=9)
    ax.grid(alpha=0.3, axis="x")
    
    # 3. Posterior Bayesiano - Candidato 1
    if len(candidatos_validos) >= 1:
        ax = fig.add_subplot(gs[0, 3])
        var_name = candidatos_validos[0].replace(" ", "_").replace("/", "_")
        idx_cand = CANDIDATOS.index(candidatos_validos[0])
        try:
            az.plot_posterior(trace, var_names=[var_name], ax=ax, color=cores_candidatos[idx_cand], textsize=9)
            ax.set_title(f"Posterior Bayesiano\n{candidatos_validos[0]}", fontweight="bold", fontsize=10)
        except:
            ax.text(0.5, 0.5, "Erro ao plotar", ha="center", va="center")
    
    # 4. Votos válidos - Candidato 1
    if len(candidatos_validos) >= 1 and f"{candidatos_validos[0]}_val" in df1.columns:
        ax = fig.add_subplot(gs[1, 0])
        idx_cand = CANDIDATOS.index(candidatos_validos[0])
        ax.hist(df1[f"{candidatos_validos[0]}_val"], bins=60, color=cores_candidatos[idx_cand], alpha=0.7, edgecolor="black", lw=0.3)
        ax.axvline(50, color="red", ls="--", lw=2, label="50%")
        ax.axvline(df1[f"{candidatos_validos[0]}_val"].mean(), color="darkred", lw=2, 
                   label=f'Média: {df1[f"{candidatos_validos[0]}_val"].mean():.1f}%')
        ax.set_xlabel("% Votos Válidos", fontsize=10)
        ax.set_ylabel("Frequência", fontsize=10)
        ax.set_title(f"{candidatos_validos[0]} — Votos Válidos", fontweight="bold")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
    
    # 5. Votos válidos - Candidato 2
    if len(candidatos_validos) >= 2 and f"{candidatos_validos[1]}_val" in df1.columns:
        ax = fig.add_subplot(gs[1, 1])
        idx_cand = CANDIDATOS.index(candidatos_validos[1])
        ax.hist(df1[f"{candidatos_validos[1]}_val"], bins=60, color=cores_candidatos[idx_cand], alpha=0.7, edgecolor="black", lw=0.3)
        ax.axvline(50, color="red", ls="--", lw=2, label="50%")
        ax.axvline(df1[f"{candidatos_validos[1]}_val"].mean(), color="darkblue", lw=2,
                   label=f'Média: {df1[f"{candidatos_validos[1]}_val"].mean():.1f}%')
        ax.set_xlabel("% Votos Válidos", fontsize=10)
        ax.set_ylabel("Frequência", fontsize=10)
        ax.set_title(f"{candidatos_validos[1]} — Votos Válidos", fontweight="bold")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
    
    # 6. Probabilidade de 2º turno
    ax = fig.add_subplot(gs[1, 2])
    ax.pie([p2t, 100 - p2t], labels=["2º Turno", "Vitória 1º"],
           autopct="%1.1f%%", colors=["#f39c12", "#27ae60"], startangle=90,
           textprops={"fontsize": 10, "fontweight": "bold"})
    ax.set_title("Prob. 2º Turno", fontweight="bold")
    
    # 7. Posterior Bayesiano - Candidato 2
    if len(candidatos_validos) >= 2:
        ax = fig.add_subplot(gs[1, 3])
        var_name = candidatos_validos[1].replace(" ", "_").replace("/", "_")
        idx_cand = CANDIDATOS.index(candidatos_validos[1])
        try:
            az.plot_posterior(trace, var_names=[var_name], ax=ax, color=cores_candidatos[idx_cand], textsize=9)
            ax.set_title(f"Posterior Bayesiano\n{candidatos_validos[1]}", fontweight="bold", fontsize=10)
        except:
            ax.text(0.5, 0.5, "Erro ao plotar", ha="center", va="center")
    
    # 8-11. Gráficos do 2º turno (se houver)
    if not df2.empty:
        cols_2t = [c for c in df2.columns if "_2T" in c and c != "vencedor_2T"]
        
        # 8. Distribuição 2T - Candidato 1
        if len(cols_2t) >= 1:
            ax = fig.add_subplot(gs[2, 0])
            cand_name = cols_2t[0].replace("_2T", "")
            idx_cand = CANDIDATOS.index(cand_name) if cand_name in CANDIDATOS else 0
            ax.hist(df2[cols_2t[0]], bins=60, color=cores_candidatos[idx_cand], alpha=0.7, edgecolor="black", lw=0.3)
            ax.axvline(50, color="red", ls="--", lw=2)
            ax.axvline(df2[cols_2t[0]].mean(), color="darkred", lw=2,
                       label=f'Média: {df2[cols_2t[0]].mean():.1f}%')
            ax.set_xlabel("% Votos (2º Turno)", fontsize=10)
            ax.set_ylabel("Frequência", fontsize=10)
            ax.set_title(f"{cand_name} — 2º Turno", fontweight="bold")
            ax.legend(fontsize=8)
            ax.grid(alpha=0.3)
        
        # 9. Distribuição 2T - Candidato 2
        if len(cols_2t) >= 2:
            ax = fig.add_subplot(gs[2, 1])
            cand_name = cols_2t[1].replace("_2T", "")
            idx_cand = CANDIDATOS.index(cand_name) if cand_name in CANDIDATOS else 1
            ax.hist(df2[cols_2t[1]], bins=60, color=cores_candidatos[idx_cand], alpha=0.7, edgecolor="black", lw=0.3)
            ax.axvline(50, color="red", ls="--", lw=2)
            ax.axvline(df2[cols_2t[1]].mean(), color="darkblue", lw=2,
                       label=f'Média: {df2[cols_2t[1]].mean():.1f}%')
            ax.set_xlabel("% Votos (2º Turno)", fontsize=10)
            ax.set_ylabel("Frequência", fontsize=10)
            ax.set_title(f"{cand_name} — 2º Turno", fontweight="bold")
            ax.legend(fontsize=8)
            ax.grid(alpha=0.3)
        
        # 10. Probabilidades 2T
        ax = fig.add_subplot(gs[2, 2])
        if not p2v.empty:
            p2s = p2v.sort_values(ascending=True)
            # Mapeia cores dos candidatos
            colors_2t = []
            for cand in p2s.index:
                if cand in CANDIDATOS:
                    colors_2t.append(cores_candidatos[CANDIDATOS.index(cand)])
                else:
                    colors_2t.append("#95a5a6")
            ax.barh(range(len(p2s)), p2s.values, color=colors_2t)
            ax.set_yticks(range(len(p2s)))
            ax.set_yticklabels(p2s.index, fontsize=9)
            ax.set_xlabel("Probabilidade (%)", fontsize=10)
            ax.set_title("Prob. Vitória\n2º Turno", fontweight="bold")
            for i, v in enumerate(p2s.values):
                ax.text(v + 0.5, i, f"{v:.1f}%", va="center", fontsize=9)
            ax.grid(alpha=0.3, axis="x")
    
    # 11. Posterior Bayesiano - Outros (se houver)
    if "Outros" in CANDIDATOS:
        ax = fig.add_subplot(gs[2, 3])
        var_name = "Outros"
        idx_cand = CANDIDATOS.index("Outros")
        try:
            az.plot_posterior(trace, var_names=[var_name], ax=ax, color=cores_candidatos[idx_cand], textsize=9)
            ax.set_title("Posterior Bayesiano\nOutros", fontweight="bold", fontsize=10)
        except:
            ax.text(0.5, 0.5, "N/A", ha="center", va="center")
    
    dias_restantes = (DATA_ELEICAO - DATA_ATUAL).days
    nota_temporal = f"Incerteza temporal: σ={DESVIO:.2f}% ({dias_restantes} dias) | Dados: data/pesquisas.csv"
    
    plt.suptitle(
        f"Eleições Brasil 2026 — 40k Simulações [v2.1.1: Cores Corrigidas]\n{nota_temporal}",
        fontsize=13, fontweight="bold", y=0.998
    )
    
    out = OUTPUT_DIR / "simulacao_eleicoes_brasil_2026_v2.png"
    plt.savefig(out, dpi=300, bbox_inches="tight")
    print(f"    Gráfico salvo: {out}")
    plt.close()


# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  BRAZIL ELECTION MONTE CARLO — 2026 [v2.1.1]")
    print("  BUGFIX + Complete + Colors Fixed")
    print("=" * 60)
    
    trace = construir_modelo()
    df1 = simular_primeiro_turno()
    df2 = simular_segundo_turno()
    pv, p2v, p2t = relatorio(df1, df2)
    graficos(df1, df2, trace, pv, p2v, p2t)
    
    print("\n✅ Concluído! Veja os gráficos em /outputs")
