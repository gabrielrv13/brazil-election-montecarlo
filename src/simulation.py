"""
brazil-election-montecarlo
==========================
Monte Carlo Simulation for Brazil's 2026 Presidential Election
Bayesian model with PyMC + 40,000 simulations

License: MIT
"""

import numpy as np
import pandas as pd
import pymc as pm
import arviz as az
import matplotlib.pyplot as plt
from pathlib import Path

# ─── CONFIG ───────────────────────────────────────────────────────────────────

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)
np.random.seed(42)

CANDIDATOS = ["Lula", "Flávio Bolsonaro", "Outros", "Brancos/Nulos"]
VOTOS_MEDIA = np.array([35.0, 29.0, 21.0, 15.0])
DESVIO = 2.0
N_SIM = 40_000
CORES = ["#e74c3c", "#3498db", "#95a5a6", "#34495e"]


# ─── MODELO BAYESIANO ─────────────────────────────────────────────────────────

def construir_modelo():
    print("\n[1/4] Construindo modelo Bayesiano com PyMC...")
    with pm.Model() as modelo:
        pm.Normal("Lula", mu=VOTOS_MEDIA[0], sigma=DESVIO)
        pm.Normal("Flavio", mu=VOTOS_MEDIA[1], sigma=DESVIO)
        pm.Normal("Outros", mu=VOTOS_MEDIA[2], sigma=DESVIO)
        pm.Normal("Brancos", mu=VOTOS_MEDIA[3], sigma=DESVIO)
        trace = pm.sample(
            draws=10_000,
            tune=2_000,
            chains=4,
            return_inferencedata=True,
            random_seed=42,
        )
    print("    OK — 40.000 amostras MCMC geradas")
    return trace


# ─── 1º TURNO ─────────────────────────────────────────────────────────────────

def simular_primeiro_turno():
    print("\n[2/4] Simulando 1º turno (40.000 iteracoes)...")

    votos = np.maximum(np.random.normal(VOTOS_MEDIA, DESVIO, size=(N_SIM, 4)), 0)
    votos_norm = votos / votos.sum(axis=1, keepdims=True) * 100

    validos = votos_norm[:, :3]
    validos_norm = validos / validos.sum(axis=1, keepdims=True) * 100

    idx_vencedor = np.argmax(votos_norm[:, :3], axis=1)
    vencedores = np.array(CANDIDATOS[:3])[idx_vencedor]

    df = pd.DataFrame(
        {
            "Lula": votos_norm[:, 0],
            "Flávio": votos_norm[:, 1],
            "Outros": votos_norm[:, 2],
            "Brancos": votos_norm[:, 3],
            "Lula_val": validos_norm[:, 0],
            "Flávio_val": validos_norm[:, 1],
            "Outros_val": validos_norm[:, 2],
            "vencedor": vencedores,
            "tem_2turno": validos_norm.max(axis=1) < 50,
        }
    )

    df.to_csv(OUTPUT_DIR / "resultados_1turno.csv", index=False)
    print("    OK")
    return df


# ─── 2º TURNO ─────────────────────────────────────────────────────────────────

def simular_segundo_turno():
    """
    Transferência de votos de 'Outros':
      média de 40 % -> Lula | 35 % -> Flávio | 25 % -> brancos (descartados)

    A transferência é amostrada com Dirichlet para garantir proporções válidas
    (sempre positivas e somando 100%).
    """
    print("\n[3/4] Simulando 2o turno (Lula vs Flávio)...")

    bl = np.random.normal(35, 2.5, size=N_SIM)
    bf = np.random.normal(29, 2.5, size=N_SIM)
    ot = np.random.normal(21, 2.5, size=N_SIM)

    # concentrações escolhidas para manter incerteza moderada em torno das médias
    transferencias = np.random.dirichlet([40, 35, 25], size=N_SIM)
    tl = transferencias[:, 0]
    tf = transferencias[:, 1]

    vl = np.maximum(bl + ot * tl, 0)
    vf = np.maximum(bf + ot * tf, 0)
    tot = vl + vf

    l2 = vl / tot * 100
    f2 = vf / tot * 100

    df = pd.DataFrame(
        {
            "Lula_2T": l2,
            "Flávio_2T": f2,
            "vencedor_2T": np.where(l2 > f2, "Lula", "Flávio Bolsonaro"),
            "diferenca": np.abs(l2 - f2),
        }
    )

    df.to_csv(OUTPUT_DIR / "resultados_2turno.csv", index=False)
    print("    OK")
    return df


# ─── RELATÓRIO ────────────────────────────────────────────────────────────────

def relatorio(df1, df2):
    sep = "=" * 60
    print(f"\n{sep}\n  RELATÓRIO — ELEIÇÕES BRASIL 2026\n{sep}")
    print("\n📊 1o TURNO — votos totais:")
    for c, col in zip(CANDIDATOS, ["Lula", "Flávio", "Outros", "Brancos"]):
        p5, p95 = df1[col].quantile([0.05, 0.95])
        print(f"  {c:22s} {df1[col].mean():5.2f}%  IC90%:[{p5:.2f}–{p95:.2f}%]")

    pv = df1["vencedor"].value_counts() / N_SIM * 100
    print("\n🏆 Prob. vitória 1o turno:")
    for c, p in pv.items():
        print(f"  {c:22s} {p:.2f}%")
    p2t = df1["tem_2turno"].mean() * 100
    print(f"\n📌 Prob. 2o turno : {p2t:.2f}%")
    print(f"🎯 Lula vence 1T  : {(df1['Lula_val'] > 50).mean() * 100:.2f}%")

    p2v = df2["vencedor_2T"].value_counts() / N_SIM * 100
    print(f"\n📊 2o TURNO:")
    print(f"  Lula   {df2['Lula_2T'].mean():.2f}% ± {df2['Lula_2T'].std():.2f}%")
    print(f"  Flávio {df2['Flávio_2T'].mean():.2f}% ± {df2['Flávio_2T'].std():.2f}%")
    print("\n🏆 Prob. vitória 2o turno:")
    for c, p in p2v.items():
        print(f"  {c:22s} {p:.2f}%")
    print(f"\n⚠️  Disputa <3pp  : {(df2['diferenca'] < 3).mean() * 100:.2f}% dos cenários")
    print(sep)
    return pv, p2v, p2t


# ─── VISUALIZAÇÕES ────────────────────────────────────────────────────────────

def graficos(df1, df2, trace, pv, p2v, p2t):
    print("\n[4/4] Gerando visualizações...")
    plt.style.use("seaborn-v0_8-whitegrid")
    fig = plt.figure(figsize=(20, 14))
    gs = fig.add_gridspec(3, 4, hspace=0.38, wspace=0.30)

    # distribuições 1T
    ax = fig.add_subplot(gs[0, :2])
    for i, col in enumerate(["Lula", "Flávio", "Outros", "Brancos"]):
        ax.hist(
            df1[col],
            bins=60,
            alpha=0.6,
            label=CANDIDATOS[i],
            color=CORES[i],
            edgecolor="black",
            lw=0.3,
        )
    ax.set_title("Distribuição de Votos — 1º Turno", fontsize=13, fontweight="bold")
    ax.legend()
    ax.grid(alpha=0.3)

    # barras prob 1T
    ax = fig.add_subplot(gs[0, 2])
    ps = pv.sort_values()
    ax.barh(range(len(ps)), ps.values, color=["#3498db", "#95a5a6", "#e74c3c"])
    ax.set_yticks(range(len(ps)))
    ax.set_yticklabels(ps.index)
    ax.set_title("Prob. Vitória\n1º Turno", fontweight="bold")
    for i, v in enumerate(ps.values):
        ax.text(v + 0.5, i, f"{v:.1f}%", va="center", fontsize=9)
    ax.grid(alpha=0.3, axis="x")

    # posterior Lula
    ax = fig.add_subplot(gs[0, 3])
    az.plot_posterior(trace, var_names=["Lula"], ax=ax, color="#e74c3c", textsize=9)
    ax.set_title("Posterior Bayesiano\nLula", fontweight="bold")

    # Lula válidos
    ax = fig.add_subplot(gs[1, 0])
    ax.hist(df1["Lula_val"], bins=60, color="#e74c3c", alpha=0.7, edgecolor="black", lw=0.3)
    ax.axvline(50, color="red", ls="--", lw=2, label="50%")
    ax.axvline(df1["Lula_val"].mean(), color="darkred", lw=2, label=f"Média {df1['Lula_val'].mean():.1f}%")
    ax.set_title("Lula — Votos Válidos", fontweight="bold")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # Flávio válidos
    ax = fig.add_subplot(gs[1, 1])
    ax.hist(df1["Flávio_val"], bins=60, color="#3498db", alpha=0.7, edgecolor="black", lw=0.3)
    ax.axvline(50, color="red", ls="--", lw=2, label="50%")
    ax.axvline(
        df1["Flávio_val"].mean(),
        color="darkblue",
        lw=2,
        label=f"Média {df1['Flávio_val'].mean():.1f}%",
    )
    ax.set_title("Flávio — Votos Válidos", fontweight="bold")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # pizza 2T
    ax = fig.add_subplot(gs[1, 2])
    ax.pie(
        [p2t, 100 - p2t],
        labels=["2º Turno", "Vitória 1º"],
        autopct="%1.1f%%",
        colors=["#f39c12", "#27ae60"],
        startangle=90,
        textprops={"fontsize": 10, "fontweight": "bold"},
    )
    ax.set_title("Prob. 2º Turno", fontweight="bold")

    # posterior Flávio
    ax = fig.add_subplot(gs[1, 3])
    az.plot_posterior(trace, var_names=["Flavio"], ax=ax, color="#3498db", textsize=9)
    ax.set_title("Posterior Bayesiano\nFlávio", fontweight="bold")

    # Lula 2T
    ax = fig.add_subplot(gs[2, 0])
    ax.hist(df2["Lula_2T"], bins=60, color="#e74c3c", alpha=0.7, edgecolor="black", lw=0.3)
    ax.axvline(50, color="red", ls="--", lw=2)
    ax.axvline(df2["Lula_2T"].mean(), color="darkred", lw=2, label=f"Média {df2['Lula_2T'].mean():.1f}%")
    ax.set_title("Lula — 2º Turno", fontweight="bold")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # Flávio 2T
    ax = fig.add_subplot(gs[2, 1])
    ax.hist(df2["Flávio_2T"], bins=60, color="#3498db", alpha=0.7, edgecolor="black", lw=0.3)
    ax.axvline(50, color="red", ls="--", lw=2)
    ax.axvline(
        df2["Flávio_2T"].mean(),
        color="darkblue",
        lw=2,
        label=f"Média {df2['Flávio_2T'].mean():.1f}%",
    )
    ax.set_title("Flávio — 2º Turno", fontweight="bold")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # barras prob 2T
    ax = fig.add_subplot(gs[2, 2])
    p2s = p2v.sort_values()
    ax.barh(range(len(p2s)), p2s.values, color=["#3498db", "#e74c3c"])
    ax.set_yticks(range(len(p2s)))
    ax.set_yticklabels(p2s.index)
    ax.set_title("Prob. Vitória\n2º Turno", fontweight="bold")
    for i, v in enumerate(p2s.values):
        ax.text(v + 0.5, i, f"{v:.1f}%", va="center", fontsize=9)
    ax.grid(alpha=0.3, axis="x")

    # posterior Outros
    ax = fig.add_subplot(gs[2, 3])
    az.plot_posterior(trace, var_names=["Outros"], ax=ax, color="#95a5a6", textsize=9)
    ax.set_title("Posterior Bayesiano\nOutros", fontweight="bold")

    plt.suptitle(
        "Eleições Presidenciais Brasil 2026 — 40.000 Simulações Monte Carlo + Análise Bayesiana",
        fontsize=14,
        fontweight="bold",
        y=1.01,
    )
    out = OUTPUT_DIR / "simulacao_eleicoes_brasil_2026.png"
    plt.savefig(out, dpi=300, bbox_inches="tight")
    print(f"    Gráfico salvo: {out}")
    plt.close()


# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  BRAZIL ELECTION MONTE CARLO — 2026")
    print("=" * 60)
    for c, m in zip(CANDIDATOS, VOTOS_MEDIA):
        print(f"  {c:22s} {m:.1f}% ± {DESVIO}%")

    trace = construir_modelo()
    df1 = simular_primeiro_turno()
    df2 = simular_segundo_turno()
    pv, p2v, p2t = relatorio(df1, df2)
    graficos(df1, df2, trace, pv, p2v, p2t)

    print("\n✅ Concluído! Veja a pasta /outputs")
