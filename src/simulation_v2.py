"""
brazil-election-montecarlo v2.5
================================
Monte Carlo Simulation for Brazil's 2026 Presidential Election

NEW in v2.5:
- Second round derived from actual first round top-2 per simulation
- Variable matchup support: each simulation independently determines its finalists
- Matchup probability matrix showing how often each pair reaches the runoff
- Per-matchup winner probability and overall victory probability

NEW in v2.4:
- Undecided voter category with proportional redistribution
- Redistribution weighted by candidate vote share and available electoral space
- Configurable blank/null allocation fraction

NEW in v2.3:
- Automatic poll aggregation with temporal weighting
- Inter-institute variance calculation
- Outlier detection and exclusion

NEW in v2.2:
- Rejection index as electoral ceiling
- Rejection-based vote transfer in second round
- Validation warnings for unviable candidates

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


# ─── POLL AGGREGATION FUNCTIONS (v2.3) ────────────────────────────────────────

def calcular_peso_temporal(data_pesquisa, data_referencia, tau=7):
    """
    Calculates temporal weight for a poll using exponential decay.
    
    More recent polls receive higher weights.
    
    Args:
        data_pesquisa: Poll date (string YYYY-MM-DD or date object)
        data_referencia: Reference date (usually today)
        tau: Time constant in days (default: 7 days)
    
    Returns:
        float: Weight between 0 and 1
    
    Formula:
        peso = exp(-dias_atras / tau)
        
    Examples:
        Today: weight = 1.0
        7 days ago: weight = 0.368 (1/e)
        14 days ago: weight = 0.135 (1/e²)
    """
    if isinstance(data_pesquisa, str):
        data_pesquisa = pd.to_datetime(data_pesquisa).date()
    
    dias_atras = (data_referencia - data_pesquisa).days
    dias_atras = max(0, dias_atras)
    
    peso = np.exp(-dias_atras / tau)
    return peso


def detectar_outliers(valores, threshold=2.5):
    """
    Detects outliers using modified z-score method (robust to outliers).
    
    Uses median absolute deviation (MAD) instead of standard deviation.
    
    Args:
        valores: Array of values
        threshold: Modified z-score threshold (default: 2.5)
    
    Returns:
        Array of boolean indicating outliers (True = outlier)
    """
    if len(valores) < 3:
        return np.zeros(len(valores), dtype=bool)
    
    mediana = np.median(valores)
    mad = np.median(np.abs(valores - mediana))
    
    if mad == 0:
        return np.zeros(len(valores), dtype=bool)
    
    # Modified z-score
    z_scores = 0.6745 * (valores - mediana) / mad
    return np.abs(z_scores) > threshold


def agregar_pesquisas_candidato(df_candidato, data_referencia):
    """
    Aggregates multiple polls for a single candidate.
    
    Uses temporal weighting and detects outliers.
    
    Args:
        df_candidato: DataFrame with polls for one candidate
        data_referencia: Reference date for temporal weighting
    
    Returns:
        tuple: (voto_agregado, rejeicao_agregada, desvio_agregado, info)
            - voto_agregado: Weighted mean of vote intention
            - rejeicao_agregada: Weighted mean of rejection
            - desvio_agregado: Combined standard deviation
            - info: Dictionary with aggregation details
    """
    n_pesquisas = len(df_candidato)
    
    # Single poll - no aggregation needed
    if n_pesquisas == 1:
        row = df_candidato.iloc[0]
        return (
            row['intencao_voto_pct'],
            row.get('rejeicao_pct', 0.0),
            row['desvio_padrao_pct'],
            {
                'n_pesquisas': 1,
                'n_validas': 1,
                'institutos': [row.get('instituto', 'Unknown')],
                'outliers': [],
                'desvio_medio': row['desvio_padrao_pct'],
                'desvio_entre': 0.0
            }
        )
    
    # Calculate temporal weights
    if 'data' in df_candidato.columns:
        pesos = df_candidato['data'].apply(
            lambda d: calcular_peso_temporal(d, data_referencia)
        ).values
    else:
        pesos = np.ones(n_pesquisas)
    
    # Normalize weights
    pesos = pesos / pesos.sum()
    
    # Detect outliers in vote intention
    votos = df_candidato['intencao_voto_pct'].values
    is_outlier = detectar_outliers(votos)
    
    # Calculate weighted mean (excluding outliers)
    mask_validos = ~is_outlier
    if mask_validos.sum() == 0:
        # All polls are outliers - keep all
        mask_validos = np.ones(n_pesquisas, dtype=bool)
    
    pesos_validos = pesos[mask_validos]
    pesos_validos = pesos_validos / pesos_validos.sum()
    
    # Weighted vote intention
    voto_agregado = np.average(
        df_candidato.loc[mask_validos, 'intencao_voto_pct'].values,
        weights=pesos_validos
    )
    
    # Weighted rejection (if available)
    # Rejection is an independent measurement from vote intention.
    # Outlier exclusion applied to vote intention must NOT carry over here:
    # a poll flagged as a vote intention outlier may still report a valid rejection value.
    # Filter only on rejeicao_pct > 0 (zero means "not measured by this institute").
    if 'rejeicao_pct' in df_candidato.columns:
        mask_tem_rejeicao = df_candidato['rejeicao_pct'].values > 0
        if mask_tem_rejeicao.any():
            pesos_rej = pesos[mask_tem_rejeicao]
            pesos_rej = pesos_rej / pesos_rej.sum()
            rejeicao_agregada = float(np.average(
                df_candidato['rejeicao_pct'].values[mask_tem_rejeicao],
                weights=pesos_rej
            ))
        else:
            rejeicao_agregada = 0.0
    else:
        rejeicao_agregada = 0.0
    
    # Calculate aggregated standard deviation
    # Formula: σ_agregado = √(σ_médio² + σ_entre_institutos²)
    
    # Average within-poll standard deviation
    desvio_medio = np.average(
        df_candidato.loc[mask_validos, 'desvio_padrao_pct'].values,
        weights=pesos_validos
    )
    
    # Between-institute variance
    variancia_entre = np.average(
        (df_candidato.loc[mask_validos, 'intencao_voto_pct'].values - voto_agregado) ** 2,
        weights=pesos_validos
    )
    desvio_entre = np.sqrt(variancia_entre)
    
    # Combined standard deviation
    desvio_agregado = np.sqrt(desvio_medio**2 + desvio_entre**2)
    
    # Collect info for reporting
    institutos = df_candidato['instituto'].tolist() if 'instituto' in df_candidato.columns else ['Unknown'] * n_pesquisas
    outliers_info = [
        {'instituto': inst, 'valor': val}
        for inst, val, is_out in zip(institutos, votos, is_outlier)
        if is_out
    ]
    
    info = {
        'n_pesquisas': n_pesquisas,
        'n_validas': int(mask_validos.sum()),
        'institutos': institutos,
        'outliers': outliers_info,
        'desvio_medio': float(desvio_medio),
        'desvio_entre': float(desvio_entre)
    }
    
    return voto_agregado, rejeicao_agregada, desvio_agregado, info


def carregar_pesquisas():
    """
    Loads and aggregates poll data from CSV file.
    
    Supports two modes:
    1. Single poll per candidate (backward compatible with v2.2)
    2. Multiple polls per candidate (v2.3: automatic aggregation)
    
    Returns:
        tuple: (candidatos, votos_media, rejeicao, desvio_base)
            - candidatos: List of candidate names (unique)
            - votos_media: Array of aggregated vote intentions (%)
            - rejeicao: Array of aggregated rejection rates (%)
            - desvio_base: Mean of aggregated standard deviations (%)
    
    CSV format (multiple polls):
        candidato,intencao_voto_pct,rejeicao_pct,desvio_padrao_pct,indecisos_pct,instituto,data
        Lula,38.0,42.0,2.0,12.0,Datafolha,2026-02-18
        Lula,36.0,43.0,2.0,13.0,Quaest,2026-02-19
        Lula,37.0,41.0,2.0,11.0,PoderData,2026-02-20
        Flávio Bolsonaro,29.0,48.0,2.0,12.0,Datafolha,2026-02-18
        ...
    
    Aggregation method:
        - Temporal weighting: peso = exp(-days_ago / 7)
        - Outlier detection: Modified z-score > 2.5
        - Combined std dev: √(σ_within² + σ_between²)
    
    Undecided voters (v2.4):
        - Optional column: indecisos_pct (poll-level, same value for all candidates in same poll)
        - Aggregated as weighted mean across all rows
        - Redistributed before simulation via distribuir_indecisos()
    """
    csv_path = Path("data/pesquisas.csv")
    
    if not csv_path.exists():
        raise FileNotFoundError(f"Arquivo {csv_path} não encontrado!")
    
    df = pd.read_csv(csv_path)
    
    # Validate required columns
    required_cols = ["candidato", "intencao_voto_pct", "desvio_padrao_pct"]
    missing = set(required_cols) - set(df.columns)
    if missing:
        raise ValueError(f"Colunas faltando no CSV: {missing}")
    
    # Detect if multiple polls per candidate
    candidatos_unicos = df['candidato'].unique()
    contagem_por_candidato = df['candidato'].value_counts()
    multiplas_pesquisas = (contagem_por_candidato > 1).any()
    
    data_referencia = date.today()
    
    # Print mode information
    if multiplas_pesquisas:
        print(f"\nData loaded from {csv_path} (multiple polls detected)")
        print(f"   Aggregation mode: ENABLED")
        print(f"   Reference date: {data_referencia}")
        print(f"   Temporal weighting: exp(-days/7)")
    else:
        print(f"\nData loaded from {csv_path} (single poll per candidate)")
        print(f"   Aggregation mode: DISABLED (backward compatible)")
    
    # Aggregate polls for each candidate
    candidatos = []
    votos_agregados = []
    rejeicao_agregada = []
    desvios_agregados = []
    
    print("\n" + "=" * 70)
    print("  POLL AGGREGATION SUMMARY")
    print("=" * 70)
    
    for candidato in candidatos_unicos:
        df_cand = df[df['candidato'] == candidato].copy()
        
        voto, rej, desv, info = agregar_pesquisas_candidato(df_cand, data_referencia)
        
        candidatos.append(candidato)
        votos_agregados.append(voto)
        rejeicao_agregada.append(rej)
        desvios_agregados.append(desv)
        
        # Report aggregation details
        if info['n_pesquisas'] > 1:
            print(f"\nCandidate: {candidato}")
            print(f"   Polls aggregated: {info['n_pesquisas']}")
            print(f"   Valid polls: {info['n_validas']}")
            print(f"   Sources: {', '.join(info['institutos'])}")
            print(f"   Aggregated vote: {voto:.2f}%")
            if rej > 0:
                print(f"   Aggregated rejection: {rej:.2f}%")
            print(f"   Base std dev: {info['desvio_medio']:.2f}%")
            print(f"   Inter-institute std dev: {info['desvio_entre']:.2f}%")
            print(f"   Combined std dev: {desv:.2f}%")
            
            if info['outliers']:
                print(f"   WARNING: {len(info['outliers'])} outlier(s) detected and excluded:")
                for outlier in info['outliers']:
                    print(f"      - {outlier['instituto']}: {outlier['valor']:.2f}%")
        else:
            print(f"\nCandidate: {candidato}")
            print(f"   Single poll: {voto:.2f}%")
            if rej > 0:
                print(f"   Rejection: {rej:.2f}%")
            print(f"   Std dev: {desv:.2f}%")
    
    print("=" * 70)
    
    # Convert to arrays
    votos_media = np.array(votos_agregados)
    rejeicao = np.array(rejeicao_agregada)
    desvio_base = np.mean(desvios_agregados)
    
    # Check if rejection data exists
    tem_rejeicao = (rejeicao > 0).any()
    if not tem_rejeicao:
        print("\nNote: 'rejeicao_pct' column not found - running without electoral ceiling")
    
    # Aggregate undecided voters (v2.4)
    # indecisos_pct is a poll-level statistic: aggregate as weighted mean across all rows
    indecisos = 0.0
    if 'indecisos_pct' in df.columns:
        if 'data' in df.columns:
            pesos_globais = df['data'].apply(
                lambda d: calcular_peso_temporal(d, data_referencia)
            ).values
            pesos_globais = pesos_globais / pesos_globais.sum()
        else:
            pesos_globais = np.ones(len(df)) / len(df)
        
        indecisos = float(np.average(df['indecisos_pct'].fillna(0).values, weights=pesos_globais))
        print(f"\nUndecided voters: {indecisos:.2f}% (will be redistributed before simulation)")
    else:
        print("\nNote: 'indecisos_pct' column not found - running without undecided voter redistribution")
    
    return candidatos, votos_media, rejeicao, desvio_base, indecisos


CANDIDATOS, VOTOS_MEDIA, REJEICAO, DESVIO_BASE, INDECISOS = carregar_pesquisas()
N_SIM = 40_000

# Dynamic color generation
def gerar_cores(n):
    """Generates distinct colors for N candidates."""
    cores_base = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6", "#34495e", "#95a5a6"]
    if n <= len(cores_base):
        return cores_base[:n]
    import matplotlib.cm as cm
    cmap = cm.get_cmap('tab10')
    return [cmap(i / n) for i in range(n)]

CORES = gerar_cores(len(CANDIDATOS))


# ─── TEMPORAL UNCERTAINTY (FUNNEL EFFECT) ─────────────────────────────────────

def calcular_desvio_ajustado():
    """
    Adjusts standard deviation based on days until election.
    
    Implements funnel effect: uncertainty increases with time to election.
    """
    dias_restantes = (DATA_ELEICAO - DATA_ATUAL).days
    if dias_restantes < 0:
        return DESVIO_BASE
    fator_temporal = np.sqrt(dias_restantes / 30)
    return max(DESVIO_BASE, DESVIO_BASE * fator_temporal)


DESVIO = calcular_desvio_ajustado()

print(f"\nDays until election: {(DATA_ELEICAO - DATA_ATUAL).days}")
print(f"Adjusted standard deviation: {DESVIO:.2f}% (base: {DESVIO_BASE:.2f}%)")


# ─── REJECTION INDEX VALIDATION (v2.2) ────────────────────────────────────────

def validar_viabilidade():
    """
    Validates electoral viability based on rejection rates.
    
    Historical rule: No Brazilian president has been elected with >50% rejection
    since redemocratization.
    
    Historical data:
        2022: Bolsonaro 51% rejection → LOST
        2022: Lula 49% rejection → WON
        2018: Bolsonaro 46% rejection → WON
    """
    print("\n" + "=" * 60)
    print("  ELECTORAL VIABILITY ANALYSIS")
    print("=" * 60)
    
    candidatos_validos = [c for c in CANDIDATOS if "Brancos" not in c and "Nulos" not in c]
    
    has_inviable = False
    has_warning = False
    
    for cand in candidatos_validos:
        idx = CANDIDATOS.index(cand)
        rej = REJEICAO[idx]
        teto = 100 - rej
        
        if rej > 50:
            print(f"\nCandidate: {cand}")
            print(f"   Rejection: {rej:.1f}% (ABOVE CRITICAL THRESHOLD)")
            print(f"   Electoral ceiling: {teto:.1f}%")
            print(f"   Status: ELECTORALLY UNVIABLE")
            print(f"   Note: No Brazilian president elected with >50% rejection")
            has_inviable = True
        elif rej > 45:
            print(f"\nCandidate: {cand}")
            print(f"   Rejection: {rej:.1f}% (near critical threshold)")
            print(f"   Electoral ceiling: {teto:.1f}%")
            print(f"   Status: HIGH ELECTORAL DIFFICULTY")
            has_warning = True
        elif rej > 0:
            print(f"\nCandidate: {cand}")
            print(f"   Rejection: {rej:.1f}%")
            print(f"   Electoral ceiling: {teto:.1f}%")
            print(f"   Status: ELECTORALLY VIABLE")
    
    print("=" * 60)
    
    if has_inviable:
        print("\nWARNING: There are electorally unviable candidates in this simulation")
    elif has_warning:
        print("\nNOTE: Some candidates are near the critical rejection threshold")


def aplicar_teto_rejeicao(votos, rejeicao_array):
    """
    Applies electoral ceiling based on rejection rates.
    
    A candidate cannot exceed (100 - rejection)% of valid votes.
    
    Args:
        votos: Array (N_SIM, n_candidatos) with vote percentages
        rejeicao_array: Array (n_candidatos,) with rejection percentages
    
    Returns:
        tuple: (votos_ajustados, info_limitacoes)
    """
    tetos = 100 - rejeicao_array
    
    ultrapassou = votos > tetos[np.newaxis, :]
    votos_limitados = np.minimum(votos, tetos[np.newaxis, :])
    
    info = {}
    for i, cand in enumerate(CANDIDATOS):
        if "Brancos" not in cand and "Nulos" not in cand and rejeicao_array[i] > 0:
            n_limitado = ultrapassou[:, i].sum()
            if n_limitado > 0:
                info[cand] = {
                    'n_simulacoes_limitadas': int(n_limitado),
                    'pct_simulacoes_limitadas': float((n_limitado / len(votos)) * 100),
                    'teto': float(tetos[i]),
                    'rejeicao': float(rejeicao_array[i])
                }
    
    return votos_limitados, info


# ─── UNDECIDED VOTER REDISTRIBUTION (v2.4) ────────────────────────────────────

def distribuir_indecisos(votos_base, indecisos_total, rejeicao_array, blank_fraction=0.15):
    """
    Redistributes undecided voter share proportionally among candidates.

    Distribution weights are the product of each candidate's vote share and
    available electoral space (100 - rejection), so that candidates with
    higher rejection absorb fewer undecided voters.

    A configurable fraction (blank_fraction) of undecided voters is allocated
    to blank/null categories and not redistributed to declared candidates.

    Args:
        votos_base: Array (n_candidatos,) with base vote intentions (%)
        indecisos_total: Total undecided voter share (%)
        rejeicao_array: Array (n_candidatos,) with rejection rates (%)
        blank_fraction: Fraction of undecided allocated to blank/null (default: 0.15)

    Returns:
        tuple: (votos_ajustados, info)
            - votos_ajustados: Adjusted vote intentions after redistribution
            - info: Dictionary with redistribution details per candidate

    Formula:
        weight_i = vote_share_i * (100 - rejection_i) / 100
        gain_i = (weight_i / sum(weights)) * indecisos_total * (1 - blank_fraction)

    Example:
        indecisos = 12%, blank_fraction = 0.15
        → 10.2% redistributed to declared candidates (proportional to weight)
        → 1.8% added to blank/null
    """
    if indecisos_total <= 0:
        return votos_base.copy(), {}

    votos_ajustados = votos_base.copy()

    # Mask for distributable candidates (not blank/null)
    mask_distributable = np.array([
        "Brancos" not in c and "Nulos" not in c
        for c in CANDIDATOS
    ])

    # Weight = vote_share * available_space
    espaco = np.maximum(100.0 - rejeicao_array, 0.0) / 100.0
    pesos = votos_base * espaco * mask_distributable

    total_peso = pesos.sum()
    if total_peso == 0:
        # Fallback: uniform distribution among distributable candidates
        n_dist = float(mask_distributable.sum())
        if n_dist == 0:
            return votos_base.copy(), {}
        pesos = mask_distributable.astype(float) / n_dist
        total_peso = 1.0

    proporcoes = pesos / total_peso

    # Partition undecided voters
    indecisos_redistribuiveis = indecisos_total * (1.0 - blank_fraction)
    indecisos_para_brancos = indecisos_total * blank_fraction

    # Apply gain to each candidate
    ganho = proporcoes * indecisos_redistribuiveis
    votos_ajustados += ganho

    # Distribute blank fraction to blank/null candidates if present
    mask_brancos = np.array(["Brancos" in c or "Nulos" in c for c in CANDIDATOS])
    if mask_brancos.any():
        n_brancos = float(mask_brancos.sum())
        votos_ajustados[mask_brancos] += indecisos_para_brancos / n_brancos

    # Build detailed info dictionary
    ganho_por_candidato = {
        CANDIDATOS[i]: float(ganho[i])
        for i in range(len(CANDIDATOS))
        if ganho[i] > 0.01
    }

    info = {
        'indecisos_total': float(indecisos_total),
        'indecisos_redistribuiveis': float(indecisos_redistribuiveis),
        'indecisos_para_brancos': float(indecisos_para_brancos),
        'blank_fraction': float(blank_fraction),
        'ganho_por_candidato': ganho_por_candidato,
    }

    return votos_ajustados, info


validar_viabilidade()


# ─── BAYESIAN MODEL WITH DIRICHLET ────────────────────────────────────────────

def construir_modelo():
    """Builds Bayesian model using Dirichlet distribution."""
    print("\n[1/4] Building Bayesian model with PyMC (Dirichlet)...")
    
    # Apply undecided redistribution to priors (v2.4)
    votos_efetivos = VOTOS_MEDIA.copy()
    if INDECISOS > 0:
        votos_efetivos, _ = distribuir_indecisos(VOTOS_MEDIA, INDECISOS, REJEICAO)
    
    fator_concentracao = 100 / DESVIO
    alphas = votos_efetivos * fator_concentracao
    
    with pm.Model() as modelo:
        votos_proporcao = pm.Dirichlet("votos_proporcao", a=alphas, shape=len(CANDIDATOS))
        
        for i, cand in enumerate(CANDIDATOS):
            var_name = cand.replace(" ", "_").replace("/", "_").replace("-", "_")
            pm.Deterministic(var_name, votos_proporcao[i] * 100)
        
        trace = pm.sample(
            draws=10_000,
            tune=2_000,
            chains=4,
            return_inferencedata=True,
            random_seed=42,
        )
    
    print("    OK - 40,000 MCMC samples generated")
    return trace


# ─── FIRST ROUND WITH REJECTION CEILING ───────────────────────────────────────

def simular_primeiro_turno():
    """Simulates first round applying undecided voter redistribution and rejection ceiling."""
    print("\n[2/4] Simulating first round (40,000 iterations) with rejection ceiling...")
    
    # Redistribute undecided voters before parameterizing the Dirichlet (v2.4)
    votos_efetivos = VOTOS_MEDIA.copy()
    info_indecisos = {}
    if INDECISOS > 0:
        votos_efetivos, info_indecisos = distribuir_indecisos(
            VOTOS_MEDIA, INDECISOS, REJEICAO
        )
        print(f"\n    Undecided voter redistribution ({INDECISOS:.2f}%):")
        for cand, ganho in info_indecisos['ganho_por_candidato'].items():
            idx = CANDIDATOS.index(cand)
            print(f"       {cand}: +{ganho:.2f}pp ({VOTOS_MEDIA[idx]:.2f}% → {votos_efetivos[idx]:.2f}%)")
        print(f"       → Blank/Null: +{info_indecisos['indecisos_para_brancos']:.2f}pp")
    
    fator_concentracao = 100 / DESVIO
    alphas = votos_efetivos * fator_concentracao
    
    proporcoes = np.random.dirichlet(alphas, size=N_SIM)
    votos_norm = proporcoes * 100
    
    indices_validos = [i for i, c in enumerate(CANDIDATOS) 
                      if "Brancos" not in c and "Nulos" not in c]
    candidatos_validos = [CANDIDATOS[i] for i in indices_validos]
    
    validos = votos_norm[:, indices_validos]
    validos_norm = validos / validos.sum(axis=1, keepdims=True) * 100
    
    # Apply rejection ceiling
    rejeicao_validos = REJEICAO[indices_validos]
    validos_com_teto, info_limitacoes = aplicar_teto_rejeicao(validos_norm, rejeicao_validos)
    
    # Re-normalize after ceiling
    validos_final = validos_com_teto / validos_com_teto.sum(axis=1, keepdims=True) * 100
    
    idx_vencedor_local = np.argmax(validos_final, axis=1)
    vencedores = np.array(candidatos_validos)[idx_vencedor_local]
    
    data = {}
    for i, cand in enumerate(CANDIDATOS):
        data[cand] = votos_norm[:, i]
    
    for i, cand in enumerate(candidatos_validos):
        data[f"{cand}_val"] = validos_final[:, i]
    
    data["vencedor"] = vencedores
    data["tem_2turno"] = validos_final.max(axis=1) < 50
    
    df = pd.DataFrame(data)
    df.to_csv(OUTPUT_DIR / "resultados_1turno_v2.5.csv", index=False)
    
    if info_indecisos:
        print(f"\n    Undecided redistribution summary:")
        print(f"       Total: {info_indecisos['indecisos_total']:.2f}%")
        print(f"       To declared candidates: {info_indecisos['indecisos_redistribuiveis']:.2f}%")
        print(f"       To blank/null: {info_indecisos['indecisos_para_brancos']:.2f}%")
    
    if info_limitacoes:
        print("\n    Rejection ceiling impact:")
        for cand, info in info_limitacoes.items():
            print(f"       {cand}: {info['pct_simulacoes_limitadas']:.1f}% simulations limited")
            print(f"                  (ceiling: {info['teto']:.1f}%, rejection: {info['rejeicao']:.1f}%)")
    else:
        print("\n    No simulations limited by rejection ceiling")
    
    print("    OK")
    return df, info_limitacoes, info_indecisos, validos_final, candidatos_validos


# ─── SECOND ROUND WITH DYNAMIC TOP-2 (v2.5) ──────────────────────────────────

def _simular_confronto(v_a, v_b, outros_votos, rej_a, rej_b, n):
    """
    Simulates a single second-round matchup between two candidates.

    Uses rejection-proportional vote transfer from eliminated candidates
    and applies the electoral ceiling to each finalist.

    Args:
        v_a: Array (n,) of first round valid vote % for candidate A
        v_b: Array (n,) of first round valid vote % for candidate B
        outros_votos: Array (n,) sum of other candidates' valid votes
        rej_a: Rejection rate for candidate A (%)
        rej_b: Rejection rate for candidate B (%)
        n: Number of simulations in this group

    Returns:
        tuple: (p_a, p_b) arrays of second-round vote shares (sum to 100)
    """
    espaco_a = max(100.0 - rej_a, 1.0)
    espaco_b = max(100.0 - rej_b, 1.0)
    total_espaco = espaco_a + espaco_b

    prop_a = espaco_a / total_espaco
    prop_b = espaco_b / total_espaco

    # Transfer: 80% of other votes go to the two finalists, 20% to blank/null
    concentracoes = [prop_a * 80, prop_b * 80, 20]
    transferencias = np.random.dirichlet(concentracoes, size=n)

    v_a_2t = np.maximum(v_a + outros_votos * transferencias[:, 0], 0)
    v_b_2t = np.maximum(v_b + outros_votos * transferencias[:, 1], 0)

    # Apply electoral ceiling
    v_a_2t = np.minimum(v_a_2t, espaco_a)
    v_b_2t = np.minimum(v_b_2t, espaco_b)

    total = v_a_2t + v_b_2t
    p_a = v_a_2t / total * 100
    p_b = v_b_2t / total * 100

    return p_a, p_b


def simular_segundo_turno(validos_final, candidatos_validos):
    """
    Simulates second round using actual top-2 finalists from each first-round simulation.

    For each simulation in validos_final, the two candidates with the highest
    valid vote share are identified as finalists. Simulations are then grouped
    by matchup pair, and each group runs an independent rejection-based transfer.

    This replaces the previous fixed-matchup approach where the same two candidates
    were always assumed to be the finalists regardless of first-round outcomes.

    Args:
        validos_final: Array (N_SIM, n_candidatos_validos) of per-simulation
                       valid vote shares after rejection ceiling
        candidatos_validos: List of valid candidate names (same order as validos_final columns)

    Returns:
        tuple: (df, info_matchups)
            df columns: matchup, finalista_a, finalista_b, voto_a, voto_b,
                        vencedor_2T, diferenca
            info_matchups: dict keyed by matchup label with probability and winner stats
    """
    print("\n[3/4] Simulating second round (dynamic top-2 per simulation)...")

    n_validos = len(candidatos_validos)
    if n_validos < 2:
        print("    Warning: Less than 2 valid candidates")
        return pd.DataFrame(), {}

    # Build REJEICAO lookup for valid candidates
    rej_validos = np.array([
        REJEICAO[CANDIDATOS.index(c)] if c in CANDIDATOS else 0.0
        for c in candidatos_validos
    ])

    # For each simulation, find indices of top-2 candidates (highest valid votes)
    top2_indices = np.argsort(validos_final, axis=1)[:, -2:]  # (N_SIM, 2), ascending
    # Sort within each row so pair is always (lower_idx, higher_idx) → canonical order
    top2_sorted = np.sort(top2_indices, axis=1)

    # Build matchup labels for each simulation
    matchup_labels = np.array([
        f"{candidatos_validos[a]} vs {candidatos_validos[b]}"
        for a, b in top2_sorted
    ])

    unique_matchups = np.unique(matchup_labels)
    print(f"    Unique matchups detected: {len(unique_matchups)}")
    for mu in unique_matchups:
        count = (matchup_labels == mu).sum()
        print(f"      {mu}: {count / len(matchup_labels) * 100:.1f}% of simulations")

    # Pre-allocate result arrays
    voto_a_arr = np.zeros(len(validos_final))
    voto_b_arr = np.zeros(len(validos_final))
    finalista_a_arr = np.empty(len(validos_final), dtype=object)
    finalista_b_arr = np.empty(len(validos_final), dtype=object)

    info_matchups = {}

    for matchup in unique_matchups:
        mask = matchup_labels == matchup
        idx_sims = np.where(mask)[0]
        n_group = len(idx_sims)

        # Canonical finalist indices for this matchup
        ia = top2_sorted[idx_sims[0], 0]
        ib = top2_sorted[idx_sims[0], 1]
        cand_a = candidatos_validos[ia]
        cand_b = candidatos_validos[ib]
        rej_a = rej_validos[ia]
        rej_b = rej_validos[ib]

        # First-round votes for this group of simulations
        v_a = validos_final[idx_sims, ia]
        v_b = validos_final[idx_sims, ib]
        outros_idx = [j for j in range(n_validos) if j not in (ia, ib)]
        outros_votos = validos_final[idx_sims][:, outros_idx].sum(axis=1) if outros_idx else np.zeros(n_group)

        p_a, p_b = _simular_confronto(v_a, v_b, outros_votos, rej_a, rej_b, n_group)

        voto_a_arr[idx_sims] = p_a
        voto_b_arr[idx_sims] = p_b
        finalista_a_arr[idx_sims] = cand_a
        finalista_b_arr[idx_sims] = cand_b

        wins_a = (p_a > p_b).sum()
        info_matchups[matchup] = {
            'cand_a': cand_a,
            'cand_b': cand_b,
            'n_sims': n_group,
            'prob_matchup': float(n_group / len(validos_final) * 100),
            'prob_a': float(wins_a / n_group * 100),
            'prob_b': float((n_group - wins_a) / n_group * 100),
            'rej_a': float(rej_a),
            'rej_b': float(rej_b),
        }

    vencedor_arr = np.where(voto_a_arr > voto_b_arr, finalista_a_arr, finalista_b_arr)
    diferenca_arr = np.abs(voto_a_arr - voto_b_arr)

    df = pd.DataFrame({
        'matchup': matchup_labels,
        'finalista_a': finalista_a_arr,
        'finalista_b': finalista_b_arr,
        'voto_a': voto_a_arr,
        'voto_b': voto_b_arr,
        'vencedor_2T': vencedor_arr,
        'diferenca': diferenca_arr,
    })

    df.to_csv(OUTPUT_DIR / "resultados_2turno_v2.5.csv", index=False)

    print("    OK")
    return df, info_matchups


# ─── REPORT ───────────────────────────────────────────────────────────────────

def relatorio(df1, df2, info_lim_1t, info_matchups, info_indecisos=None):
    """Generates comprehensive report."""
    sep = "=" * 60
    print(f"\n{sep}\n  REPORT - BRAZIL 2026 ELECTIONS [v2.4]\n{sep}")
    
    if info_indecisos:
        print("\nUNDECIDED VOTERS (v2.4):")
        print(f"  Total undecided:              {info_indecisos['indecisos_total']:.2f}%")
        print(f"  Redistributed to candidates:  {info_indecisos['indecisos_redistribuiveis']:.2f}%")
        print(f"  Allocated to blank/null:      {info_indecisos['indecisos_para_brancos']:.2f}%")
        print(f"  Blank fraction:               {info_indecisos['blank_fraction']*100:.0f}%")
        print(f"  Gain per candidate:")
        for cand, ganho in info_indecisos['ganho_por_candidato'].items():
            idx = CANDIDATOS.index(cand)
            base = VOTOS_MEDIA[idx]
            print(f"    {cand:22s} +{ganho:.2f}pp  ({base:.2f}% → {base+ganho:.2f}%)")
    
    print("\nREJECTION INDEX (Electoral Ceiling):")
    candidatos_validos = [c for c in CANDIDATOS if "Brancos" not in c and "Nulos" not in c]
    for cand in candidatos_validos:
        idx = CANDIDATOS.index(cand)
        rej = REJEICAO[idx]
        teto = 100 - rej
        
        if rej > 50:
            status = "UNVIABLE"
        elif rej > 45:
            status = "WARNING "
        elif rej > 0:
            status = "VIABLE  "
        else:
            status = "N/A     "
        
        print(f"  {status} {cand:20s} Rej: {rej:5.1f}% → Ceiling: {teto:5.1f}%")
    
    print("\nFIRST ROUND - Total votes:")
    for cand in CANDIDATOS:
        p5, p95 = df1[cand].quantile([0.05, 0.95])
        print(f"  {cand:22s} {df1[cand].mean():5.2f}%  90% CI:[{p5:.2f}-{p95:.2f}%]")
    
    pv = df1["vencedor"].value_counts() / N_SIM * 100
    print("\nFirst round victory probability:")
    for c, p in pv.items():
        print(f"  {c:22s} {p:.2f}%")
    
    p2t = df1["tem_2turno"].mean() * 100
    print(f"\nSecond round probability: {p2t:.2f}%")
    
    lider = candidatos_validos[0]
    if f"{lider}_val" in df1.columns:
        prob_lider_1t = (df1[f"{lider}_val"] > 50).mean() * 100
        print(f"{lider} first round victory: {prob_lider_1t:.2f}%")
    
    if not df2.empty:
        print("\nSECOND ROUND MATCHUP PROBABILITIES (v2.5):")
        for matchup, info in sorted(info_matchups.items(),
                                    key=lambda x: x[1]['prob_matchup'], reverse=True):
            print(f"\n  {matchup}  [{info['prob_matchup']:.1f}% of simulations]")
            print(f"    {info['cand_a']:22s} Rej:{info['rej_a']:5.1f}%  Victory: {info['prob_a']:.1f}%")
            print(f"    {info['cand_b']:22s} Rej:{info['rej_b']:5.1f}%  Victory: {info['prob_b']:.1f}%")

        p2v = df2["vencedor_2T"].value_counts() / len(df2) * 100
        print("\nOVERALL SECOND ROUND VICTORY PROBABILITY:")
        for c, p in p2v.items():
            print(f"  {c:22s} {p:.2f}%")

        print(f"\nClose race (<3pp): {(df2['diferenca'] < 3).mean() * 100:.2f}% of scenarios")
    
    print(sep)
    return pv, p2v if not df2.empty else pd.Series(), p2t


# ─── VISUALIZATIONS (Complete from v2.2) ──────────────────────────────────────

def graficos(df1, df2, trace, pv, p2v, p2t, info_lim_1t, info_matchups, info_indecisos=None):
    """Generates comprehensive visualizations."""
    print("\n[4/4] Generating visualizations...")
    plt.style.use("seaborn-v0_8-whitegrid")
    fig = plt.figure(figsize=(20, 14))
    gs = fig.add_gridspec(3, 4, hspace=0.38, wspace=0.30)
    
    candidatos_validos = [c for c in CANDIDATOS if "Brancos" not in c and "Nulos" not in c]
    cores_candidatos = CORES[:len(CANDIDATOS)]
    
    # 1. First round distributions
    ax = fig.add_subplot(gs[0, :2])
    for i, cand in enumerate(CANDIDATOS):
        ax.hist(df1[cand], bins=60, alpha=0.6, label=cand,
                color=cores_candidatos[i], edgecolor="black", lw=0.3)
    ax.set_title("Vote Distribution - First Round [v2.3: Poll Aggregation + Rejection]", 
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Vote %", fontsize=11)
    ax.set_ylabel("Frequency", fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    
    # 2. Rejection Index
    ax = fig.add_subplot(gs[0, 2])
    candidatos_plot = []
    rejeicao_plot = []
    cores_rej = []
    for cand in candidatos_validos:
        idx = CANDIDATOS.index(cand)
        if REJEICAO[idx] > 0:
            candidatos_plot.append(cand)
            rejeicao_plot.append(REJEICAO[idx])
            if REJEICAO[idx] > 50:
                cores_rej.append('#e74c3c')
            elif REJEICAO[idx] > 45:
                cores_rej.append('#f39c12')
            else:
                cores_rej.append('#27ae60')
    
    if candidatos_plot:
        y_pos = range(len(candidatos_plot))
        ax.barh(y_pos, rejeicao_plot, color=cores_rej, alpha=0.7, edgecolor='black', lw=1)
        ax.axvline(50, color='red', linestyle='--', lw=2, label='Critical Threshold (50%)', zorder=10)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(candidatos_plot, fontsize=9)
        ax.set_xlabel("Rejection (%)", fontsize=10)
        ax.set_title("Rejection Index\n(Electoral Ceiling)", fontweight="bold", fontsize=11)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3, axis='x')
        ax.set_xlim(0, max(60, max(rejeicao_plot) + 5) if rejeicao_plot else 60)
        
        for i, (rej, cand) in enumerate(zip(rejeicao_plot, candidatos_plot)):
            teto = 100 - rej
            ax.text(rej + 1, i, f"{rej:.0f}% → Ceiling: {teto:.0f}%", 
                    va='center', fontsize=8, fontweight='bold')
    else:
        ax.text(0.5, 0.5, "No rejection data", ha='center', va='center', transform=ax.transAxes)
        ax.set_title("Rejection Index", fontweight="bold")
    
    # 3. First round probabilities
    ax = fig.add_subplot(gs[0, 3])
    ps = pv.sort_values(ascending=True)
    colors_bar = []
    for c in ps.index:
        if c in CANDIDATOS:
            colors_bar.append(cores_candidatos[CANDIDATOS.index(c)])
        else:
            colors_bar.append("#95a5a6")
    ax.barh(range(len(ps)), ps.values, color=colors_bar)
    ax.set_yticks(range(len(ps)))
    ax.set_yticklabels(ps.index, fontsize=9)
    ax.set_xlabel("Probability (%)", fontsize=10)
    ax.set_title("Victory Prob.\n1st Round", fontweight="bold")
    for i, v in enumerate(ps.values):
        ax.text(v + 0.5, i, f"{v:.1f}%", va="center", fontsize=9)
    ax.grid(alpha=0.3, axis="x")
    
    # 4. Valid votes - Candidate 1
    if len(candidatos_validos) >= 1 and f"{candidatos_validos[0]}_val" in df1.columns:
        ax = fig.add_subplot(gs[1, 0])
        idx_cand = CANDIDATOS.index(candidatos_validos[0])
        ax.hist(df1[f"{candidatos_validos[0]}_val"], bins=60, color=cores_candidatos[idx_cand], 
                alpha=0.7, edgecolor="black", lw=0.3)
        ax.axvline(50, color="red", ls="--", lw=2, label="50%")
        ax.axvline(df1[f"{candidatos_validos[0]}_val"].mean(), color="darkred", lw=2, 
                   label=f'Mean: {df1[f"{candidatos_validos[0]}_val"].mean():.1f}%')
        
        rej = REJEICAO[idx_cand]
        if rej > 0:
            teto = 100 - rej
            ax.axvline(teto, color="orange", ls=":", lw=2, label=f'Ceiling: {teto:.0f}%', zorder=10)
        
        ax.set_xlabel("% Valid Votes", fontsize=10)
        ax.set_ylabel("Frequency", fontsize=10)
        ax.set_title(f"{candidatos_validos[0]} - Valid Votes", fontweight="bold")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
    
    # 5. Valid votes - Candidate 2
    if len(candidatos_validos) >= 2 and f"{candidatos_validos[1]}_val" in df1.columns:
        ax = fig.add_subplot(gs[1, 1])
        idx_cand = CANDIDATOS.index(candidatos_validos[1])
        ax.hist(df1[f"{candidatos_validos[1]}_val"], bins=60, color=cores_candidatos[idx_cand], 
                alpha=0.7, edgecolor="black", lw=0.3)
        ax.axvline(50, color="red", ls="--", lw=2, label="50%")
        ax.axvline(df1[f"{candidatos_validos[1]}_val"].mean(), color="darkblue", lw=2,
                   label=f'Mean: {df1[f"{candidatos_validos[1]}_val"].mean():.1f}%')
        
        rej = REJEICAO[idx_cand]
        if rej > 0:
            teto = 100 - rej
            ax.axvline(teto, color="orange", ls=":", lw=2, label=f'Ceiling: {teto:.0f}%', zorder=10)
        
        ax.set_xlabel("% Valid Votes", fontsize=10)
        ax.set_ylabel("Frequency", fontsize=10)
        ax.set_title(f"{candidatos_validos[1]} - Valid Votes", fontweight="bold")
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
    
    # 6. Second round probability (pie) + matchup probabilities (bar)
    ax = fig.add_subplot(gs[1, 2])
    ax.pie([p2t, 100 - p2t], labels=["2nd Round", "1st Round Win"],
           autopct="%1.1f%%", colors=["#f39c12", "#27ae60"], startangle=90,
           textprops={"fontsize": 10, "fontweight": "bold"})
    ax.set_title("2nd Round Prob.", fontweight="bold")

    # 6b. Matchup probability matrix (v2.5)
    ax2 = fig.add_subplot(gs[2, :2])
    if info_matchups:
        matchups_sorted = sorted(info_matchups.items(),
                                 key=lambda x: x[1]['prob_matchup'], reverse=True)
        labels_mu = [m for m, _ in matchups_sorted]
        prob_mu = [d['prob_matchup'] for _, d in matchups_sorted]
        prob_a  = [d['prob_a'] for _, d in matchups_sorted]
        prob_b  = [d['prob_b'] for _, d in matchups_sorted]
        y_pos = range(len(labels_mu))

        bars_mu = ax2.barh(y_pos, prob_mu, color='#bdc3c7', alpha=0.4,
                           label='Matchup probability', height=0.5)
        for i, (pa, pb, d) in enumerate(zip(prob_a, prob_b, matchups_sorted)):
            info = d[1]
            ca, cb = info['cand_a'], info['cand_b']
            color_a = cores_candidatos[CANDIDATOS.index(ca)] if ca in CANDIDATOS else '#7f8c8d'
            color_b = cores_candidatos[CANDIDATOS.index(cb)] if cb in CANDIDATOS else '#7f8c8d'
            ax2.barh(i - 0.18, pa * prob_mu[i] / 100, color=color_a,
                     alpha=0.85, height=0.28, label=ca if i == 0 else '_nolegend_')
            ax2.barh(i + 0.18, pb * prob_mu[i] / 100, color=color_b,
                     alpha=0.85, height=0.28, label=cb if i == 0 else '_nolegend_')

        ax2.set_yticks(list(y_pos))
        ax2.set_yticklabels(labels_mu, fontsize=9)
        ax2.set_xlabel("% of simulations", fontsize=10)
        ax2.set_title(
            "Matchup Probability & Per-Matchup Victory (v2.5: Dynamic Top-2)",
            fontweight="bold", fontsize=10
        )
        ax2.grid(alpha=0.3, axis='x')
        ax2.legend(fontsize=8, loc='lower right')
    else:
        ax2.text(0.5, 0.5, "No matchup data", ha='center', va='center',
                 transform=ax2.transAxes)
        ax2.set_title("Matchup Probabilities", fontweight="bold")
    
    # 7-11: Additional visualizations from v2.2...
    # (Simplified here for space - full implementation would include all 11 plots)
    
    # 7. Undecided voter redistribution (v2.4)
    ax = fig.add_subplot(gs[1, 3])
    if info_indecisos and info_indecisos.get('indecisos_total', 0) > 0:
        ganho_items = info_indecisos['ganho_por_candidato']
        nomes = list(ganho_items.keys())
        ganhos = [ganho_items[n] for n in nomes]
        cores_ganho = []
        for nome in nomes:
            if nome in CANDIDATOS:
                cores_ganho.append(cores_candidatos[CANDIDATOS.index(nome)])
            else:
                cores_ganho.append("#95a5a6")
        
        y_pos = range(len(nomes))
        ax.barh(y_pos, ganhos, color=cores_ganho, alpha=0.75, edgecolor="black", lw=0.5)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(nomes, fontsize=9)
        ax.set_xlabel("Gain (pp)", fontsize=10)
        ax.set_title(
            f"Undecided Redistribution\n(Total: {info_indecisos['indecisos_total']:.1f}%)",
            fontweight="bold", fontsize=10
        )
        for i, v in enumerate(ganhos):
            ax.text(v + 0.05, i, f"+{v:.2f}pp", va="center", fontsize=8)
        ax.grid(alpha=0.3, axis="x")
    else:
        ax.text(0.5, 0.5, "No undecided data\n(add indecisos_pct column)",
                ha="center", va="center", transform=ax.transAxes, fontsize=9,
                color="#7f8c8d")
        ax.set_title("Undecided Redistribution", fontweight="bold", fontsize=10)
    
    dias_restantes = (DATA_ELEICAO - DATA_ATUAL).days
    nota = f"v2.5: Dynamic Top-2 + Undecided + Poll Aggregation + Rejection Ceiling | σ={DESVIO:.2f}% ({dias_restantes} days)"
    
    plt.suptitle(
        f"Brazil 2026 Elections - 40,000 Monte Carlo Simulations\n{nota}",
        fontsize=13, fontweight="bold", y=0.998
    )
    
    out = OUTPUT_DIR / "simulacao_eleicoes_brasil_2026_v2.5.png"
    plt.savefig(out, dpi=300, bbox_inches="tight")
    print(f"    Graph saved: {out}")
    plt.close()


# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  BRAZIL ELECTION MONTE CARLO - 2026 [v2.5]")
    print("  NEW: Dynamic Second Round Top-2 Per Simulation")
    print("  v2.4: Undecided Voter Redistribution")
    print("  v2.3: Automatic Poll Aggregation with Temporal Weighting")
    print("  v2.2: Rejection Index as Electoral Ceiling")
    print("=" * 60)

    trace = construir_modelo()
    df1, info_lim_1t, info_indecisos, validos_final, candidatos_validos = simular_primeiro_turno()
    df2, info_matchups = simular_segundo_turno(validos_final, candidatos_validos)
    pv, p2v, p2t = relatorio(df1, df2, info_lim_1t, info_matchups, info_indecisos)
    graficos(df1, df2, trace, pv, p2v, p2t, info_lim_1t, info_matchups, info_indecisos)

    print("\nSimulation completed. Results available in /outputs")
    print("\nv2.5 Features:")
    print("  - Dynamic second round: top-2 identified per simulation")
    print("  - Matchup probability matrix across all N_SIM scenarios")
    print("  - Per-matchup winner probability with rejection-based transfer")
    print("\nv2.4 Features:")
    print("  - Undecided redistribution: proportional to vote_share * available_space")
    print("  - Blank fraction: 15% of undecided → blank/null")
    print("\nv2.3 Features:")
    print("  - Poll aggregation: Temporal weighting exp(-days/7)")
    print("  - Outlier detection: Modified z-score > 2.5")
    print("  - Combined std dev: √(σ_within² + σ_between²)")
    print("  - Rejection ceiling: Limits growth of high-rejection candidates")
