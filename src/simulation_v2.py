"""
brazil-election-montecarlo v2.6
================================
Monte Carlo Simulation for Brazil's 2026 Presidential Election

NEW in v2.6:
- Absolute vote projections for first and second rounds
- Stochastic abstention modeled as Normal(mu, sigma) per simulation
- Absolute vote margin distribution in second round
- PDF report generation (Issue #7)

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

import sys
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

# ─── ELECTORATE CONSTANTS (v2.6) ──────────────────────────────────────────────

ELEITORADO         = 158_600_000  # TSE 2026 registered voters
ABSTENCAO_1T_MU    = 0.20         # First round abstention: historical mean
ABSTENCAO_1T_SIGMA = 0.02         # First round abstention: std dev (90% CI: 16.7–23.3%)
ABSTENCAO_2T_MU    = 0.22         # Second round abstention: mean (higher than 1st round)
ABSTENCAO_2T_SIGMA = 0.03         # Second round abstention: std dev (90% CI: 17.1–26.9%)


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
    if data_pesquisa is None or (hasattr(data_pesquisa, '__class__') and 
            data_pesquisa.__class__.__name__ in ('NaTType', 'float')):
        return 1.0  # No date available: treat as most recent (weight = 1)

    if isinstance(data_pesquisa, str):
        data_pesquisa = pd.to_datetime(data_pesquisa).date()
    elif isinstance(data_pesquisa, float):
        return 1.0  # NaN read as float: treat as most recent

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
    # Rows with rejeicao_pct == 0 are treated as not measured, not as true zero rejection.
    # Only polls that explicitly reported a rejection value (> 0) are included.
    if 'rejeicao_pct' in df_candidato.columns:
        # Rejection is an independent measurement from vote intention.
        # Outlier exclusion applied to vote intention (mask_validos) must NOT
        # carry over here — a poll flagged as a vote outlier may still report
        # a valid rejection value. Filter only on rejeicao_pct > 0.
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


def carregar_pesquisas(csv_path=None):
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
    csv_path = Path(csv_path) if csv_path else Path("data/pesquisas.csv")
    
    if not csv_path.exists():
        raise FileNotFoundError(f"Arquivo {csv_path} não encontrado!")
    
    df = pd.read_csv(csv_path)

    # Parse date column if present — errors='coerce' turns unparseable values into NaT
    if 'data' in df.columns:
        df['data'] = pd.to_datetime(df['data'], errors='coerce').dt.date

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
    votos_media = np.array(votos_agregados, dtype=float)
    rejeicao = np.array(rejeicao_agregada, dtype=float)
    desvio_base = float(np.mean(desvios_agregados))

    # Detect NaN or zero values that would break the Dirichlet model
    nan_mask = np.isnan(votos_media)
    zero_mask = votos_media <= 0
    if nan_mask.any() or zero_mask.any():
        for i, cand in enumerate(candidatos):
            if nan_mask[i]:
                print(f"   WARNING: {cand} has NaN vote share — check CSV for missing intencao_voto_pct")
            if zero_mask[i]:
                print(f"   WARNING: {cand} has zero/negative vote share ({votos_media[i]:.2f}%)")
        raise ValueError(
            "Invalid vote shares detected after aggregation. "
            "All candidates must have intencao_voto_pct > 0 in the CSV."
        )
    
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


# ─── GLOBALS (populated by inicializar()) ─────────────────────────────────────
# Empty until inicializar() is called. Importing this module will NOT trigger
# CSV loading or console output, allowing safe import from dashboard.py.

N_SIM: int = 40_000
CANDIDATOS: list = []
VOTOS_MEDIA: np.ndarray = np.array([])
REJEICAO: np.ndarray = np.array([])
DESVIO_BASE: float = 2.0
INDECISOS: float = 0.0
CORES: list = []
DESVIO: float = 2.0


# ─── COLOR GENERATION ─────────────────────────────────────────────────────────

def gerar_cores(n):
    """Generates distinct colors for N candidates."""
    cores_base = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6", "#34495e", "#95a5a6"]
    if n <= len(cores_base):
        return cores_base[:n]
    import matplotlib.cm as cm
    cmap = cm.get_cmap("tab10")
    return [cmap(i / n) for i in range(n)]


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


# ─── INITIALIZATION ────────────────────────────────────────────────────────────

def inicializar(csv_path=None):
    """
    Initializes global simulation state from a CSV file.

    Must be called before any simulation function. Automatically invoked when
    the module runs as __main__. External callers (e.g. dashboard.py) must
    call this explicitly, optionally supplying a custom csv_path.

    Args:
        csv_path: Path to poll CSV file (str or Path). Defaults to data/pesquisas.csv.
    """
    global CANDIDATOS, VOTOS_MEDIA, REJEICAO, DESVIO_BASE, INDECISOS, CORES, DESVIO
    CANDIDATOS, VOTOS_MEDIA, REJEICAO, DESVIO_BASE, INDECISOS = carregar_pesquisas(csv_path)
    CORES = gerar_cores(len(CANDIDATOS))
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

    # Sanity checks: NaN or non-positive alphas cause Dirichlet to fail at init
    if np.any(np.isnan(votos_efetivos)):
        raise ValueError(
            f"VOTOS_MEDIA contains NaN after undecided redistribution: {votos_efetivos}\n"
            "Check the CSV for missing or invalid intencao_voto_pct values."
        )
    if np.any(votos_efetivos <= 0):
        bad = [CANDIDATOS[i] for i, v in enumerate(votos_efetivos) if v <= 0]
        raise ValueError(
            f"Candidates with zero or negative vote share: {bad}\n"
            "Dirichlet requires all alpha parameters > 0. "
            "Check intencao_voto_pct values in the CSV."
        )

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
    
    if np.any(np.isnan(votos_efetivos)) or np.any(votos_efetivos <= 0):
        bad = [(CANDIDATOS[i], float(v)) for i, v in enumerate(votos_efetivos)
               if np.isnan(v) or v <= 0]
        raise ValueError(
            f"Invalid vote shares before first-round simulation: {bad}\n"
            "All candidates must have intencao_voto_pct > 0."
        )

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

    # ── Absolute vote projections (v2.6) ──────────────────────────────────────
    # Abstention is sampled independently per simulation as Normal(mu, sigma),
    # clipped to [5%, 45%] to avoid degenerate scenarios.
    abstencao_1t_sim = np.random.normal(
        ABSTENCAO_1T_MU, ABSTENCAO_1T_SIGMA, N_SIM
    ).clip(0.05, 0.45)
    votos_validos_1t = (ELEITORADO * (1 - abstencao_1t_sim)).astype(np.int64)
    data["abstencao_1t_pct"] = abstencao_1t_sim * 100
    data["votos_validos_1t"] = votos_validos_1t
    for i, cand in enumerate(candidatos_validos):
        data[f"{cand}_abs"] = (votos_validos_1t * validos_final[:, i] / 100).astype(np.int64)

    df = pd.DataFrame(data)
    df.to_csv(OUTPUT_DIR / "resultados_1turno_v2.6.csv", index=False)
    
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

    # Absolute vote arrays (v2.6): abstention sampled once per simulation
    abstencao_2t_sim = np.random.normal(
        ABSTENCAO_2T_MU, ABSTENCAO_2T_SIGMA, len(validos_final)
    ).clip(0.05, 0.45)
    votos_validos_2t = (ELEITORADO * (1 - abstencao_2t_sim)).astype(np.int64)

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

    votos_a_abs = (votos_validos_2t * voto_a_arr / 100).astype(np.int64)
    votos_b_abs = (votos_validos_2t * voto_b_arr / 100).astype(np.int64)

    df = pd.DataFrame({
        'matchup': matchup_labels,
        'finalista_a': finalista_a_arr,
        'finalista_b': finalista_b_arr,
        'voto_a': voto_a_arr,
        'voto_b': voto_b_arr,
        'vencedor_2T': vencedor_arr,
        'diferenca': diferenca_arr,
        'abstencao_2t_pct': abstencao_2t_sim * 100,
        'votos_validos_2t': votos_validos_2t,
        'votos_a_abs': votos_a_abs,
        'votos_b_abs': votos_b_abs,
        'margem_votos': np.abs(votos_a_abs - votos_b_abs),
    })

    df.to_csv(OUTPUT_DIR / "resultados_2turno_v2.6.csv", index=False)

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

        # ── Absolute vote projections (v2.6) ──────────────────────────────────
        if 'votos_validos_2t' in df2.columns and not df2.empty:
            print("\nABSOLUTE VOTE PROJECTIONS — SECOND ROUND (v2.6):")
            print(f"  Electorate: {ELEITORADO:,}")
            med_abs  = df2['abstencao_2t_pct'].median()
            med_turn = df2['votos_validos_2t'].median()
            print(f"  Median turnout:   {med_turn:>14,.0f}  (abstention: {med_abs:.1f}%)")
            dominant = max(info_matchups.items(), key=lambda x: x[1]['prob_matchup'])[1]
            for col, label in [('votos_a_abs', dominant['cand_a']),
                                ('votos_b_abs', dominant['cand_b'])]:
                if col in df2.columns:
                    p5, p50, p95 = df2[col].quantile([0.05, 0.50, 0.95])
                    print(f"  {label:22s} {p50:>12,.0f} votes  "
                          f"90% CI: [{p5:,.0f} – {p95:,.0f}]")
            p5m, p50m, p95m = df2['margem_votos'].quantile([0.05, 0.50, 0.95])
            print(f"  Median margin:    {p50m:>12,.0f} votes  "
                  f"90% CI: [{p5m:,.0f} – {p95m:,.0f}]")

    print(sep)
    return pv, p2v if not df2.empty else pd.Series(), p2t


# ─── VISUALIZATIONS (v2.5 redesign) ───────────────────────────────────────────

def _hex_lighten(hex_color, factor):
    """Blend a hex color toward white by factor (0.0 = original, 1.0 = white)."""
    h = hex_color.lstrip('#')
    r, g, b = [int(h[i:i+2], 16) for i in (0, 2, 4)]
    return '#{:02x}{:02x}{:02x}'.format(
        int(r + (255 - r) * factor),
        int(g + (255 - g) * factor),
        int(b + (255 - b) * factor),
    )


def graficos(df1, df2, trace, pv, p2v, p2t, info_lim_1t, info_matchups, info_indecisos=None):
    """
    Generates redesigned visualizations (v2.5).

    Layout:
        Left (main):   Semicircle showing 2nd round outcome distribution by margin category.
        Top right:     1st round vote intention with 90% CI (dot + error bar).
        Bottom right:  Rejection index and electoral viability.

    The semicircle mirrors the Hungarian parliamentary forecast style but adapted
    to Brazil's binary presidential runoff: left = leading candidate wins,
    right = trailing candidate wins, shading encodes margin of victory.
    """
    from matplotlib.patches import Wedge, FancyBboxPatch
    import matplotlib.gridspec as gridspec

    print("\n[4/4] Generating visualizations...")

    BG = '#F7F7F7'
    plt.rcParams.update({'axes.facecolor': BG, 'figure.facecolor': BG})

    fig = plt.figure(figsize=(18, 11), facecolor=BG)
    gs  = gridspec.GridSpec(
        2, 2, figure=fig,
        width_ratios=[1.35, 1], height_ratios=[1, 1],
        hspace=0.40, wspace=0.10,
        left=0.03, right=0.97, top=0.87, bottom=0.06,
    )
    ax_semi = fig.add_subplot(gs[:, 0])
    ax_vote = fig.add_subplot(gs[0, 1])
    ax_rej  = fig.add_subplot(gs[1, 1])

    candidatos_validos = [c for c in CANDIDATOS if "Brancos" not in c and "Nulos" not in c]
    dias_restantes = (DATA_ELEICAO - DATA_ATUAL).days

    # ── Identify finalists and their colors ────────────────────────────────────
    if info_matchups and not df2.empty:
        dominant = max(info_matchups.items(), key=lambda x: x[1]['prob_matchup'])
        info_d = dominant[1]
        if info_d['prob_a'] >= info_d['prob_b']:
            lider, vice = info_d['cand_a'], info_d['cand_b']
            prob_lider, prob_vice = info_d['prob_a'], info_d['prob_b']
        else:
            lider, vice = info_d['cand_b'], info_d['cand_a']
            prob_lider, prob_vice = info_d['prob_b'], info_d['prob_a']
    else:
        lider = candidatos_validos[0]
        vice  = candidatos_validos[1] if len(candidatos_validos) > 1 else ''
        prob_lider = float(p2v.get(lider, 50)) if not p2v.empty else 50.0
        prob_vice  = float(p2v.get(vice,  50)) if not p2v.empty else 50.0

    idx_lider = CANDIDATOS.index(lider) if lider in CANDIDATOS else 0
    idx_vice  = CANDIDATOS.index(vice)  if vice  in CANDIDATOS else 1
    cor_lider = CORES[idx_lider]
    cor_vice  = CORES[idx_vice]

    # ── Compute margin segments ─────────────────────────────────────────────────
    if not df2.empty:
        n = len(df2)
        mask_l = df2['vencedor_2T'] == lider
        mask_v = df2['vencedor_2T'] == vice

        def _pct(mask):
            return mask.sum() / n * 100

        seg = {
            'lider_confort': _pct(mask_l & (df2['diferenca'] >= 5)),
            'lider_close':   _pct(mask_l & df2['diferenca'].between(1, 5)),
            'lider_photo':   _pct(mask_l & (df2['diferenca'] < 1)),
            'vice_photo':    _pct(mask_v & (df2['diferenca'] < 1)),
            'vice_close':    _pct(mask_v & df2['diferenca'].between(1, 5)),
            'vice_confort':  _pct(mask_v & (df2['diferenca'] >= 5)),
        }
        pct_apertada = (df2['diferenca'] < 3).mean() * 100
    else:
        seg = {k: 0.0 for k in [
            'lider_confort', 'lider_close', 'lider_photo',
            'vice_photo', 'vice_close', 'vice_confort']}
        pct_apertada = 0.0

    # ── PANEL 1: Semicircle ─────────────────────────────────────────────────────
    ax_semi.set_aspect('equal')
    ax_semi.set_xlim(-1.50, 1.50)
    ax_semi.set_ylim(-0.54, 1.50)
    ax_semi.axis('off')

    R_OUT, R_IN = 1.0, 0.50
    center = (0.0, 0.0)

    colors_seq = [
        _hex_lighten(cor_lider, 0.00),
        _hex_lighten(cor_lider, 0.38),
        _hex_lighten(cor_lider, 0.65),
        _hex_lighten(cor_vice,  0.65),
        _hex_lighten(cor_vice,  0.38),
        _hex_lighten(cor_vice,  0.00),
    ]

    seg_values = list(seg.values())
    total_seg  = sum(seg_values) or 100.0
    angles = [v / total_seg * 180.0 for v in seg_values]

    current = 180.0
    arc_mids = []
    for angle, color in zip(angles, colors_seq):
        theta2, theta1 = current, current - angle
        arc_mids.append((theta1 + theta2) / 2.0)
        if angle >= 0.3:
            ax_semi.add_patch(Wedge(
                center, R_OUT, theta1, theta2,
                width=R_OUT - R_IN,
                facecolor=color, edgecolor=BG, lw=3.0, zorder=3,
            ))
        current -= angle

    # White divider at the lider/vice boundary
    boundary_deg = 180.0 - (prob_lider / 100.0 * 180.0)
    bx = np.cos(np.radians(boundary_deg))
    by = np.sin(np.radians(boundary_deg))
    ax_semi.plot(
        [center[0] + R_IN * bx, center[0] + R_OUT * bx],
        [center[1] + R_IN * by, center[1] + R_OUT * by],
        color=BG, lw=4.5, zorder=5,
    )

    # Center hole: probability labels
    ax_semi.text(0, 0.14, f"{prob_lider:.1f}%",
                 ha='center', va='center', fontsize=32, fontweight='bold',
                 color=cor_lider, zorder=6)
    ax_semi.text(0, -0.08, f"{prob_vice:.1f}%",
                 ha='center', va='center', fontsize=20,
                 color=cor_vice, zorder=6)
    ax_semi.text(0, -0.24,
                 f"Corrida apertada (<3pp): {pct_apertada:.1f}%",
                 ha='center', va='center', fontsize=8.5, color='#777777', zorder=6)

    # Outer arc labels — positioned outside the arc with adaptive offset
    # Photo-finish segments (idx 2,3) are labeled inline at the bottom info line
    outer_labels = [
        (0, f"Folgado\n{seg['lider_confort']:.1f}%",  cor_lider,                    4.0),
        (1, f"Apertado\n{seg['lider_close']:.1f}%",   _hex_lighten(cor_lider, 0.2), 6.0),
        (2, f"<1pp\n{seg['lider_photo']:.1f}%",        _hex_lighten(cor_lider, 0.5), 2.0),
        (3, f"<1pp\n{seg['vice_photo']:.1f}%",         _hex_lighten(cor_vice,  0.5), 2.0),
        (4, f"Apertado\n{seg['vice_close']:.1f}%",    _hex_lighten(cor_vice,  0.2), 6.0),
        (5, f"Folgado\n{seg['vice_confort']:.1f}%",   cor_vice,                     4.0),
    ]
    for idx_seg, text, col, min_angle in outer_labels:
        if angles[idx_seg] < min_angle:
            continue
        deg = arc_mids[idx_seg]
        rad = np.radians(deg)
        # Segments near the top (60-120°) need more room to clear "SEGUNDO TURNO"
        if 55 < deg < 125:
            r_label = R_OUT + 0.32
        elif 30 < deg < 150:
            r_label = R_OUT + 0.20
        else:
            r_label = R_OUT + 0.14
        lx = r_label * np.cos(rad)
        ly = r_label * np.sin(rad)
        ha = 'right' if deg > 90 else 'left'
        ax_semi.text(lx, ly, text, ha=ha, va='center',
                     fontsize=8.0, color=col, fontweight='bold')

    # Bottom summary boxes
    w_box, h_box = 1.10, 0.26
    for x0, cand_name, cor in [(-1.44, lider, cor_lider), (0.34, vice, cor_vice)]:
        prob = prob_lider if cand_name == lider else prob_vice
        ax_semi.add_patch(FancyBboxPatch(
            (x0, -0.51), w_box, h_box,
            boxstyle="round,pad=0.03",
            facecolor=cor, edgecolor='none', alpha=0.12, zorder=2,
        ))
        ax_semi.text(x0 + w_box / 2, -0.51 + h_box * 0.72,
                     cand_name, ha='center', va='center',
                     fontsize=10.5, fontweight='bold', color=cor)
        ax_semi.text(x0 + w_box / 2, -0.51 + h_box * 0.22,
                     f"Vitória no 2º turno: {prob:.1f}%",
                     ha='center', va='center', fontsize=9, color=cor)

    ax_semi.text(0, 1.20, "SEGUNDO TURNO",
                 ha='center', va='center', fontsize=13,
                 color='#333333', fontweight='bold')

    # ── PANEL 2: Vote intention with 90% CI ────────────────────────────────────
    for spine in ax_vote.spines.values():
        spine.set_visible(False)
    ax_vote.tick_params(left=False, bottom=False)

    cands_plot = list(reversed(candidatos_validos))
    for y, cand in enumerate(cands_plot):
        idx   = CANDIDATOS.index(cand)
        col   = CORES[idx]
        col_v = f"{cand}_val"
        serie = df1[col_v] if col_v in df1.columns else df1[cand]

        mean_v = serie.mean()
        ci_lo  = serie.quantile(0.05)
        ci_hi  = serie.quantile(0.95)

        # CI bar
        ax_vote.plot([ci_lo, ci_hi], [y, y], color=col, lw=3,
                     alpha=0.35, solid_capstyle='round')
        # Mean dot
        ax_vote.scatter([mean_v], [y], color=col, s=110, zorder=5)
        # Mean label (above dot)
        ax_vote.text(mean_v, y + 0.34, f"{mean_v:.1f}%",
                     ha='center', va='bottom', fontsize=9.5,
                     fontweight='bold', color=col)
        # CI bounds (muted)
        ax_vote.text(ci_lo - 0.8, y, f"{ci_lo:.1f}",
                     ha='right', va='center', fontsize=7.5, color='#aaaaaa')
        ax_vote.text(ci_hi + 0.8, y, f"{ci_hi:.1f}",
                     ha='left',  va='center', fontsize=7.5, color='#aaaaaa')

    ax_vote.set_yticks(range(len(cands_plot)))
    ax_vote.set_yticklabels(cands_plot, fontsize=10.5)
    ax_vote.axvline(50, color='#aaaaaa', ls='--', lw=1, alpha=0.5)
    # xlim upper bound: max CI high + 12pp headroom to prevent label clipping
    max_ci_hi = max(
        (df1[f"{c}_val"] if f"{c}_val" in df1.columns else df1[c]).quantile(0.95)
        for c in candidatos_validos
    )
    ax_vote.set_xlim(0, max(68, max_ci_hi + 12))
    ax_vote.set_ylim(-0.6, len(cands_plot) - 0.4)
    ax_vote.grid(axis='x', alpha=0.18, color='#aaaaaa')
    ax_vote.set_axisbelow(True)
    ax_vote.set_xlabel("Votos válidos (%)", fontsize=9, color='#666666', labelpad=6)
    ax_vote.set_title(
        "Intenção de Voto  ·  1º Turno\nIC 90% — votos válidos",
        fontsize=11, fontweight='bold', pad=12, loc='left', color='#222222',
    )

    # ── PANEL 3: Rejection index ────────────────────────────────────────────────
    for spine in ax_rej.spines.values():
        spine.set_visible(False)
    ax_rej.tick_params(left=False, bottom=False)

    cands_rej = [c for c in candidatos_validos if REJEICAO[CANDIDATOS.index(c)] > 0]
    cands_rej_rev = list(reversed(cands_rej))

    for y, cand in enumerate(cands_rej_rev):
        idx  = CANDIDATOS.index(cand)
        rej  = REJEICAO[idx]
        teto = 100 - rej

        if rej > 50:
            bar_color, status = '#c0392b', 'Inviável'
        elif rej > 45:
            bar_color, status = '#e67e22', 'Dificuldade alta'
        else:
            bar_color, status = '#27ae60', 'Viável'

        # Track background
        ax_rej.barh(y, 72, color='#e8e8e8', height=0.50, zorder=1)
        # Rejection bar
        ax_rej.barh(y, rej, color=bar_color, height=0.50, alpha=0.80, zorder=2)

        # Labels always outside the bar (after it) in dark color — avoids white-on-light issue
        label_x = rej + 1.2
        ax_rej.text(label_x, y + 0.13,
                    f"{rej:.0f}%  →  teto {teto:.0f}%   {status}",
                    ha='left', va='center', fontsize=8.5,
                    color='#333333', fontweight='bold')

    ax_rej.axvline(50, color='#c0392b', ls='--', lw=1.5, alpha=0.65, zorder=5)
    ax_rej.text(50.8, len(cands_rej_rev) - 0.50,
                'Limite crítico\n(50%)', fontsize=7.5, color='#c0392b', va='top')

    ax_rej.set_yticks(range(len(cands_rej_rev)))
    ax_rej.set_yticklabels(cands_rej_rev, fontsize=10.5)
    ax_rej.set_xlim(0, 95)  # wider to accommodate outside labels
    ax_rej.set_ylim(-0.55, len(cands_rej_rev) - 0.45)
    ax_rej.grid(axis='x', alpha=0.18, color='#aaaaaa')
    ax_rej.set_axisbelow(True)
    ax_rej.set_xlabel("Rejeição (%)", fontsize=9, color='#666666', labelpad=6)
    ax_rej.set_title(
        "Índice de Rejeição  ·  Teto Eleitoral",
        fontsize=11, fontweight='bold', pad=12, loc='left', color='#222222',
    )

    # ── Header ─────────────────────────────────────────────────────────────────
    fig.text(0.03, 0.950, "BRASIL 2026",
             fontsize=24, fontweight='bold', color='#1a1a2e', va='bottom')
    fig.text(0.03, 0.932,
             f"Previsão Presidencial  ·  Eleição em {dias_restantes} dias"
             f"  ({DATA_ELEICAO.strftime('%d/%m/%Y')})",
             fontsize=10, color='#555555', va='bottom')
    fig.text(0.03, 0.916,
             f"Baseado em 40.000 simulações Monte Carlo  ·  σ = {DESVIO:.2f}%  ·"
             f"  {len(candidatos_validos)} candidatos + brancos/nulos",
             fontsize=8.5, color='#999999', va='bottom')
    fig.add_artist(plt.Line2D(
        [0.03, 0.97], [0.910, 0.910],
        transform=fig.transFigure, color='#dddddd', lw=1.2,
    ))

    out = OUTPUT_DIR / "simulacao_eleicoes_brasil_2026_v2.5.png"
    plt.savefig(out, dpi=300, bbox_inches='tight', facecolor=BG)
    print(f"    Graph saved: {out}")
    plt.close()


# ─── PDF REPORT (Issue #7) ────────────────────────────────────────────────────

def gerar_relatorio_pdf(df1, df2, pv, p2v, p2t, info_matchups, info_indecisos=None):
    """
    Generates a multi-page PDF report with simulation results.

    Pages:
        1 — Summary dashboard: key probabilities and first-round distribution.
        2 — Second-round matchup analysis with absolute vote projections.
        3 — Candidate viability table (rejection index and electoral ceiling).

    Args:
        df1: First-round simulation DataFrame.
        df2: Second-round simulation DataFrame.
        pv: Series — first-round victory probabilities.
        p2v: Series — second-round victory probabilities.
        p2t: float — probability of going to second round.
        info_matchups: dict — matchup details from simular_segundo_turno.
        info_indecisos: dict or None — undecided voter redistribution info.

    Returns:
        Path: path to the generated PDF file.
    """
    from matplotlib.backends.backend_pdf import PdfPages
    import matplotlib.gridspec as gridspec

    out_path = OUTPUT_DIR / "relatorio_eleicoes_brasil_2026.pdf"
    candidatos_validos = [c for c in CANDIDATOS if "Brancos" not in c and "Nulos" not in c]
    BG = '#F7F7F7'

    print("\n[PDF] Generating PDF report...")

    with PdfPages(out_path) as pdf:

        # ── Page 1: Summary ───────────────────────────────────────────────────
        fig = plt.figure(figsize=(11, 8.5), facecolor=BG)
        fig.patch.set_facecolor(BG)
        gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.35,
                               left=0.08, right=0.95, top=0.82, bottom=0.08)

        # Title block
        fig.text(0.08, 0.93, "BRASIL 2026 — PREVISÃO ELEITORAL",
                 fontsize=18, fontweight='bold', color='#1a1a2e')
        fig.text(0.08, 0.88,
                 f"Relatório gerado em {date.today().strftime('%d/%m/%Y')}  ·  "
                 f"{N_SIM:,} simulações Monte Carlo  ·  σ = {DESVIO:.2f}%",
                 fontsize=9, color='#666666')
        fig.add_artist(plt.Line2D([0.08, 0.95], [0.865, 0.865],
                                  transform=fig.transFigure, color='#cccccc', lw=1))

        # Panel A: 1st round vote shares
        ax_a = fig.add_subplot(gs[0, 0])
        ax_a.set_facecolor(BG)
        for spine in ax_a.spines.values():
            spine.set_visible(False)
        cands_rev = list(reversed(candidatos_validos))
        for y, cand in enumerate(cands_rev):
            idx = CANDIDATOS.index(cand)
            col_v = f"{cand}_val"
            serie = df1[col_v] if col_v in df1.columns else df1[cand]
            mean_v = serie.mean()
            ci_lo = serie.quantile(0.05)
            ci_hi = serie.quantile(0.95)
            col = CORES[idx]
            ax_a.plot([ci_lo, ci_hi], [y, y], color=col, lw=3, alpha=0.30, solid_capstyle='round')
            ax_a.scatter([mean_v], [y], color=col, s=80, zorder=5)
            ax_a.text(mean_v, y + 0.30, f"{mean_v:.1f}%",
                      ha='center', fontsize=8.5, fontweight='bold', color=col)
        ax_a.set_yticks(range(len(cands_rev)))
        ax_a.set_yticklabels(cands_rev, fontsize=9)
        ax_a.set_xlim(0, 62)
        ax_a.axvline(50, color='#aaaaaa', ls='--', lw=1, alpha=0.5)
        ax_a.set_title("1º Turno — Votos válidos (IC 90%)", fontsize=10, fontweight='bold', pad=8)
        ax_a.grid(axis='x', alpha=0.15)
        ax_a.set_axisbelow(True)

        # Panel B: 2nd round probability
        ax_b = fig.add_subplot(gs[0, 1])
        ax_b.set_facecolor(BG)
        for spine in ax_b.spines.values():
            spine.set_visible(False)
        if not p2v.empty:
            bars = ax_b.barh(range(len(p2v)), p2v.values,
                             color=[CORES[CANDIDATOS.index(c)] if c in CANDIDATOS else '#95a5a6'
                                    for c in p2v.index],
                             height=0.55, alpha=0.85)
            for bar, (cand, prob) in zip(bars, p2v.items()):
                ax_b.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                          f"{prob:.1f}%", va='center', fontsize=9, fontweight='bold')
            ax_b.set_yticks(range(len(p2v)))
            ax_b.set_yticklabels(p2v.index, fontsize=9)
            ax_b.set_xlim(0, 115)
            ax_b.tick_params(bottom=False)
        ax_b.set_title("2º Turno — Prob. de vitória", fontsize=10, fontweight='bold', pad=8)
        ax_b.grid(axis='x', alpha=0.15)
        ax_b.set_axisbelow(True)

        # Panel C: Key stats table
        ax_c = fig.add_subplot(gs[1, :])
        ax_c.axis('off')
        rows = [["Candidato", "Voto médio (%)", "IC 90%", "Rejeição", "Teto eleitoral", "Viabilidade"]]
        for cand in candidatos_validos:
            idx = CANDIDATOS.index(cand)
            col_v = f"{cand}_val"
            serie = df1[col_v] if col_v in df1.columns else df1[cand]
            mean_v = serie.mean()
            ci_lo = serie.quantile(0.05)
            ci_hi = serie.quantile(0.95)
            rej = REJEICAO[idx]
            teto = 100 - rej
            if rej > 50:
                viab = "Inviável"
            elif rej > 45:
                viab = "Dific. alta"
            elif rej > 0:
                viab = "Viável"
            else:
                viab = "N/A"
            rows.append([
                cand,
                f"{mean_v:.2f}%",
                f"{ci_lo:.1f}% – {ci_hi:.1f}%",
                f"{rej:.1f}%" if rej > 0 else "N/A",
                f"{teto:.1f}%" if rej > 0 else "N/A",
                viab,
            ])
        tbl = ax_c.table(cellText=rows[1:], colLabels=rows[0],
                         loc='center', cellLoc='center')
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(8.5)
        tbl.scale(1, 1.5)
        for (r, c), cell in tbl.get_celld().items():
            cell.set_facecolor('#e8e8e8' if r == 0 else BG)
            cell.set_edgecolor('#dddddd')
        ax_c.set_title("Resumo por candidato", fontsize=10, fontweight='bold', pad=8, loc='left')

        pdf.savefig(fig, bbox_inches='tight', facecolor=BG)
        plt.close(fig)

        # ── Page 2: Second round details + absolute votes ─────────────────────
        fig2 = plt.figure(figsize=(11, 8.5), facecolor=BG)
        fig2.patch.set_facecolor(BG)
        gs2 = gridspec.GridSpec(1, 2, figure=fig2, hspace=0.0, wspace=0.40,
                                left=0.08, right=0.95, top=0.82, bottom=0.08)

        fig2.text(0.08, 0.93, "ANÁLISE DO 2º TURNO",
                  fontsize=16, fontweight='bold', color='#1a1a2e')
        fig2.text(0.08, 0.88,
                  f"Probabilidade de 2º turno: {p2t:.1f}%  ·  "
                  f"Eleitorado: {ELEITORADO:,}",
                  fontsize=9, color='#666666')
        fig2.add_artist(plt.Line2D([0.08, 0.95], [0.865, 0.865],
                                   transform=fig2.transFigure, color='#cccccc', lw=1))

        # Left panel: matchup bars when multiple matchups exist;
        # absolute vote summary table when there is only one matchup.
        ax_m = fig2.add_subplot(gs2[0, 0])
        ax_m.set_facecolor(BG)
        for spine in ax_m.spines.values():
            spine.set_visible(False)

        single_matchup = info_matchups and len(info_matchups) == 1

        if info_matchups and not single_matchup:
            sorted_matchups = sorted(info_matchups.items(),
                                     key=lambda x: x[1]['prob_matchup'], reverse=True)
            labels_m = [m[:30] for m, _ in sorted_matchups]
            probs_m = [info['prob_matchup'] for _, info in sorted_matchups]
            ax_m.barh(range(len(labels_m)), probs_m, color='#3498db', height=0.5, alpha=0.75)
            for y, (prob, (mu, info)) in enumerate(zip(probs_m, sorted_matchups)):
                ax_m.text(prob + 0.5, y,
                          f"{prob:.1f}%  ({info['cand_a'][:8]}: {info['prob_a']:.0f}% | "
                          f"{info['cand_b'][:8]}: {info['prob_b']:.0f}%)",
                          va='center', fontsize=7.5)
            ax_m.set_yticks(range(len(labels_m)))
            ax_m.set_yticklabels(labels_m, fontsize=8)
            ax_m.set_xlim(0, 130)
            ax_m.set_title("Confrontos possíveis (%  das simulações)", fontsize=10,
                            fontweight='bold', pad=8)
            ax_m.grid(axis='x', alpha=0.15)
            ax_m.set_axisbelow(True)

        elif info_matchups and single_matchup and not df2.empty:
            # Single confirmed matchup: show absolute vote projection table instead
            ax_m.axis('off')
            dominant = list(info_matchups.values())[0]
            cand_a, cand_b = dominant['cand_a'], dominant['cand_b']

            rows_abs = [["Candidato", "Mediana (votos)", "IC 5%", "IC 95%", "Prob. vitória"]]
            for col_key, cand, prob in [
                ('votos_a_abs', cand_a, dominant['prob_a']),
                ('votos_b_abs', cand_b, dominant['prob_b']),
            ]:
                if col_key in df2.columns:
                    p5, p50, p95 = df2[col_key].quantile([0.05, 0.50, 0.95])
                    rows_abs.append([
                        cand,
                        f"{p50 / 1_000_000:.2f}M",
                        f"{p5 / 1_000_000:.2f}M",
                        f"{p95 / 1_000_000:.2f}M",
                        f"{prob:.1f}%",
                    ])

            if 'votos_validos_2t' in df2.columns:
                turn_med = df2['votos_validos_2t'].median()
                abs_med  = df2['abstencao_2t_pct'].median()
                rows_abs.append([
                    "Comparecimento",
                    f"{turn_med / 1_000_000:.2f}M",
                    "—", "—",
                    f"Abst. {abs_med:.1f}%",
                ])

            tbl_abs = ax_m.table(cellText=rows_abs[1:], colLabels=rows_abs[0],
                                 loc='center', cellLoc='center')
            tbl_abs.auto_set_font_size(False)
            tbl_abs.set_fontsize(8.5)
            tbl_abs.scale(1, 1.8)
            for (r, c), cell in tbl_abs.get_celld().items():
                cell.set_facecolor('#e8e8e8' if r == 0 else BG)
                cell.set_edgecolor('#dddddd')

            ax_m.set_title(
                f"Projeção de votos absolutos\n{cand_a} vs {cand_b}",
                fontsize=10, fontweight='bold', pad=8, loc='left',
            )
        else:
            ax_m.axis('off')

        # Absolute vote margin distribution
        ax_v = fig2.add_subplot(gs2[0, 1])
        ax_v.set_facecolor(BG)
        for spine in ax_v.spines.values():
            spine.set_visible(False)

        if not df2.empty and 'margem_votos' in df2.columns:
            margem_m = df2['margem_votos'] / 1_000_000
            ax_v.hist(margem_m, bins=60, color='#2ecc71', alpha=0.70, edgecolor='none')
            p50 = margem_m.median()
            ax_v.axvline(p50, color='#1a8a4a', lw=2, ls='--')
            ax_v.text(p50 + 0.05, ax_v.get_ylim()[1] * 0.92,
                      f"Mediana\n{p50:.2f}M votos", fontsize=8, color='#1a8a4a')
            ax_v.set_xlabel("Margem de votos (milhões)", fontsize=9)
            ax_v.set_ylabel("Frequência", fontsize=9)
        ax_v.set_title("Distribuição da margem — 2º Turno\n(votos absolutos)", fontsize=10,
                        fontweight='bold', pad=8)
        ax_v.grid(axis='y', alpha=0.15)
        ax_v.set_axisbelow(True)

        pdf.savefig(fig2, bbox_inches='tight', facecolor=BG)
        plt.close(fig2)

    print(f"    PDF saved: {out_path}")
    return out_path


# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  BRAZIL ELECTION MONTE CARLO - 2026 [v2.6]")
    print("  NEW: Absolute vote projections + PDF report")
    print("  v2.5: Dynamic Second Round Top-2 Per Simulation")
    print("  v2.4: Undecided Voter Redistribution")
    print("  v2.3: Automatic Poll Aggregation with Temporal Weighting")
    print("  v2.2: Rejection Index as Electoral Ceiling")
    print("=" * 60)

    inicializar()
    validar_viabilidade()

    trace = construir_modelo()
    df1, info_lim_1t, info_indecisos, validos_final, candidatos_validos = simular_primeiro_turno()
    df2, info_matchups = simular_segundo_turno(validos_final, candidatos_validos)
    pv, p2v, p2t = relatorio(df1, df2, info_lim_1t, info_matchups, info_indecisos)
    graficos(df1, df2, trace, pv, p2v, p2t, info_lim_1t, info_matchups, info_indecisos)
    gerar_relatorio_pdf(df1, df2, pv, p2v, p2t, info_matchups, info_indecisos)

    print("\nSimulation completed. Results available in /outputs")
    print("\nv2.6 Features:")
    print("  - Absolute vote projections: ELEITORADO × (1 - abstencao_simulada)")
    print("  - Stochastic abstention: Normal(0.20, 0.02) 1T / Normal(0.22, 0.03) 2T")
    print("  - PDF report: relatorio_eleicoes_brasil_2026.pdf")
    print("\nv2.5 Features:")
    print("  - Dynamic second round: top-2 identified per simulation")
    print("  - Matchup probability matrix across all N_SIM scenarios")
    print("\nv2.4 Features:")
    print("  - Undecided redistribution: proportional to vote_share × available_space")
    print("\nv2.3 Features:")
    print("  - Poll aggregation: Temporal weighting exp(-days/7)")
    print("  - Outlier detection: Modified z-score > 2.5")
