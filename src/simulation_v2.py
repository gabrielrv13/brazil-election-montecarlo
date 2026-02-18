"""
brazil-election-montecarlo v2 (final)
======================================
Monte Carlo Simulation for Brazil's 2026 Presidential Election
Bayesian model with PyMC + 40,000 simulations

NEW in v2:
- Dirichlet distribution for vote shares (guarantees sum = 100%)
- Temporal uncertainty (increases with distance to election day)
- Reads polling data from data/pesquisas.csv (easy to update!)

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

# Data da eleição (1º turno em 4 de outubro de 2026)
DATA_ELEICAO = date(2026, 10, 4)
DATA_ATUAL = date.today()


# ─── CARREGAR DADOS DAS PESQUISAS ─────────────────────────────────────────────

def carregar_pesquisas():
    """
    Carrega dados de pesquisas eleitorais do arquivo CSV.
    Agora você só precisa atualizar o CSV e rodar o script de novo!
    """
    csv_path = Path("data/pesquisas.csv")
    
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Arquivo {csv_path} não encontrado!\n"
            "Crie o arquivo com as colunas: candidato, intencao_voto_pct, desvio_padrao_pct"
        )
    
    df = pd.read_csv(csv_path)
    
    # Valida colunas necessárias
    required_cols = ["candidato", "intencao_voto_pct", "desvio_padrao_pct"]
    missing = set(required_cols) - set(df.columns)
    if missing:
        raise ValueError(f"Colunas faltando no CSV: {missing}")
    
    # Mantém a ordem do CSV: ela define a prioridade dos candidatos
    # (ex.: os 2 primeiros nomes válidos usados no cenário de 2º turno).
    df = df.reset_index(drop=True)
    
    candidatos = df["candidato"].tolist()
    votos_media = df["intencao_voto_pct"].values
    
    # Usa o desvio médio como base (geralmente todos iguais)
    desvio_base = df["desvio_padrao_pct"].mean()
    
    print(f"\n📋 Dados carregados de {csv_path}")
    print(f"   Data da pesquisa: {df['data'].iloc[0] if 'data' in df.columns else 'não especificada'}")
    if 'fonte' in df.columns:
        print(f"   Fonte: {df['fonte'].iloc[0]}")
    
    return candidatos, votos_media, desvio_base


CANDIDATOS, VOTOS_MEDIA, DESVIO_BASE = carregar_pesquisas()
CORES = ["#e74c3c", "#3498db", "#95a5a6", "#34495e"]
N_SIM = 40_000


# ─── INCERTEZA TEMPORAL ───────────────────────────────────────────────────────

def calcular_desvio_ajustado():
    """
    Calcula desvio padrão ajustado baseado no tempo até a eleição.
    Incerteza aumenta com a raiz quadrada do tempo restante (efeito "funil").
    
    Fórmula: σ(t) = σ_base × √(dias_restantes / 30)
    """
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
    """
    Modelo Bayesiano hierárquico usando Dirichlet.
    A distribuição Dirichlet garante que as proporções sempre somem 1 (100%).
    """
    print("\n[1/4] Construindo modelo Bayesiano com PyMC (Dirichlet)...")
    
    fator_concentracao = 100 / DESVIO
    alphas = VOTOS_MEDIA * fator_concentracao
    
    with pm.Model() as modelo:
        votos_proporcao = pm.Dirichlet("votos_proporcao", a=alphas, shape=len(CANDIDATOS))
        
        # Cria variáveis determinísticas para cada candidato
        for i, cand in enumerate(CANDIDATOS):
            # Remove caracteres especiais do nome para usar como variável PyMC
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
    """
    Simulação usando Dirichlet.
    Garante que as proporções sempre são válidas (≥0 e soma=100%).
    """
    print("\n[2/4] Simulando 1º turno (40.000 iterações) — Dirichlet...")
    
    fator_concentracao = 100 / DESVIO
    alphas = VOTOS_MEDIA * fator_concentracao
    
    proporcoes = np.random.dirichlet(alphas, size=N_SIM)
    votos_norm = proporcoes * 100
    
    # Identifica candidatos válidos (não brancos/nulos) mantendo os índices corretos
    idx_validos = [
        i for i, c in enumerate(CANDIDATOS)
        if "Brancos" not in c and "Nulos" not in c
    ]
    candidatos_validos = [CANDIDATOS[i] for i in idx_validos]
    
    # Calcula votos válidos
    validos = votos_norm[:, idx_validos]
    validos_norm = validos / validos.sum(axis=1, keepdims=True) * 100
    
    # Identifica vencedor
    idx_vencedor = np.argmax(votos_norm[:, idx_validos], axis=1)
    vencedores = np.array(candidatos_validos)[idx_vencedor]
    
    # Cria DataFrame dinamicamente
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
    """
    Simulação do 2º turno usando Dirichlet para transferência de votos.
    Assume os dois primeiros candidatos nas pesquisas como os do 2º turno.
    """
    print("\n[3/4] Simulando 2º turno (top 2 candidatos) — Dirichlet...")
    
    # Identifica os 2 primeiros candidatos
    candidatos_validos = [c for c in CANDIDATOS if "Brancos" not in c and "Nulos" not in c]
    
    if len(candidatos_validos) < 2:
        print("    ⚠️  Menos de 2 candidatos válidos, pulando 2º turno")
        return pd.DataFrame()
    
    cand1, cand2 = candidatos_validos[0], candidatos_validos[1]
    idx1 = CANDIDATOS.index(cand1)
    idx2 = CANDIDATOS.index(cand2)
    idx_outros = [i for i, c in enumerate(CANDIDATOS) 
                  if c not in [cand1, cand2] and "Brancos" not in c and "Nulos" not in c]
    
    # Votos base
    voto1 = np.random.normal(VOTOS_MEDIA[idx1], DESVIO, size=N_SIM)
    voto2 = np.random.normal(VOTOS_MEDIA[idx2], DESVIO, size=N_SIM)
    
    # Soma votos de "Outros"
    votos_outros = sum(VOTOS_MEDIA[i] for i in idx_outros)
    outros = np.random.normal(votos_outros, DESVIO, size=N_SIM)
    
    # Transferência usando Dirichlet [cand1, cand2, brancos]
    # Proporções estimadas: 40%, 35%, 25%
    transferencias = np.random.dirichlet([40, 35, 25], size=N_SIM)
    t1 = transferencias[:, 0]
    t2 = transferencias[:, 1]
    
    # Voto final
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
    print(f"\n{sep}\n  RELATÓRIO — ELEIÇÕES BRASIL 2026 [v2]\n{sep}")
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
    
    # Mostra prob de vitória no 1T do líder
    lider = CANDIDATOS[0]
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


# ─── VISUALIZAÇÕES ────────────────────────────────────────────────────────────

def graficos(df1, df2, trace, pv, p2v, p2t):
    print("\n[4/4] Gerando visualizações...")
    plt.style.use("seaborn-v0_8-whitegrid")
    fig = plt.figure(figsize=(20, 14))
    gs = fig.add_gridspec(3, 4, hspace=0.38, wspace=0.30)
    
    # Cores dinâmicas baseadas no número de candidatos
    cores = CORES[:len(CANDIDATOS)]
    
    # Distribuições 1T
    ax = fig.add_subplot(gs[0, :2])
    for i, cand in enumerate(CANDIDATOS):
        ax.hist(df1[cand], bins=60, alpha=0.6, label=cand,
                color=cores[i], edgecolor="black", lw=0.3)
    ax.set_title("Distribuição de Votos — 1º Turno [v2: Dirichlet + CSV]", 
                 fontsize=13, fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    
    # Probabilidades 1T
    ax = fig.add_subplot(gs[0, 2])
    ps = pv.sort_values()
    colors = [cores[CANDIDATOS.index(c)] if c in CANDIDATOS else "#95a5a6" for c in ps.index]
    ax.barh(range(len(ps)), ps.values, color=colors)
    ax.set_yticks(range(len(ps)))
    ax.set_yticklabels(ps.index, fontsize=9)
    ax.set_title("Prob. Vitória\n1º Turno", fontweight="bold")
    for i, v in enumerate(ps.values):
        ax.text(v + 0.5, i, f"{v:.1f}%", va="center", fontsize=9)
    ax.grid(alpha=0.3, axis="x")
    
    # Posteriors Bayesianos
    var_names = [c.replace(" ", "_").replace("/", "_") for c in CANDIDATOS[:3]]
    for idx, (var_name, cor) in enumerate(zip(var_names, cores)):
        ax = fig.add_subplot(gs[idx // 2, 3 if idx % 2 else 1])
        try:
            az.plot_posterior(trace, var_names=[var_name], ax=ax, color=cor, textsize=9)
            ax.set_title(f"Posterior\n{CANDIDATOS[idx]}", fontweight="bold", fontsize=10)
        except:
            pass
    
    dias_restantes = (DATA_ELEICAO - DATA_ATUAL).days
    nota_temporal = f"Incerteza temporal: σ={DESVIO:.2f}% ({dias_restantes} dias) | Dados: data/pesquisas.csv"
    
    plt.suptitle(
        f"Eleições Brasil 2026 — 40k Simulações [v2: Dirichlet + Temporal + CSV]\n{nota_temporal}",
        fontsize=13, fontweight="bold", y=0.995
    )
    
    out = OUTPUT_DIR / "simulacao_eleicoes_brasil_2026_v2.png"
    plt.savefig(out, dpi=300, bbox_inches="tight")
    print(f"    Gráfico salvo: {out}")
    plt.close()


# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  BRAZIL ELECTION MONTE CARLO — 2026 [v2]")
    print("  Dirichlet + Temporal Uncertainty + CSV Data")
    print("=" * 60)
    
    trace = construir_modelo()
    df1 = simular_primeiro_turno()
    df2 = simular_segundo_turno()
    pv, p2v, p2t = relatorio(df1, df2)
    graficos(df1, df2, trace, pv, p2v, p2t)
    
    print("\n✅ Concluído! Veja a pasta /outputs")
    print(f"💡 Para atualizar: edite data/pesquisas.csv e rode novamente!")
