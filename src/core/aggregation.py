from __future__ import annotations

import numpy as np
import pandas as pd

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