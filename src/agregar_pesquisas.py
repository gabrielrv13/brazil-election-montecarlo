"""Agregador de pesquisas eleitorais por candidato.

Lê múltiplas pesquisas (uma linha por instituto), calcula média ponderada por
recência e ajusta o desvio padrão incluindo divergência entre institutos.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

COLUNAS_OBRIGATORIAS = {
    "candidato",
    "intencao_voto_pct",
    "desvio_padrao_pct",
    "instituto",
    "data",
    "amostra",
}


def validar_csv(df: pd.DataFrame) -> None:
    faltantes = COLUNAS_OBRIGATORIAS - set(df.columns)
    if faltantes:
        raise ValueError(f"Colunas faltando no CSV: {sorted(faltantes)}")


def calcular_pesos_temporais(datas: pd.Series, data_referencia: pd.Timestamp) -> np.ndarray:
    dias_atras = (data_referencia - datas).dt.days.clip(lower=0)
    return np.exp(-dias_atras / 7.0)


def desvio_entre_institutos(valores: np.ndarray, pesos: np.ndarray) -> float:
    media = np.average(valores, weights=pesos)
    variancia = np.average((valores - media) ** 2, weights=pesos)
    return float(np.sqrt(max(variancia, 0.0)))


def _linhas_outlier(
    grupo: pd.DataFrame,
    media_ponderada: float,
    sigma_entre: float,
    limite_z: float,
) -> pd.DataFrame:
    if len(grupo) < 2 or sigma_entre <= 0:
        return grupo.iloc[0:0].copy()

    z_scores = (grupo["intencao_voto_pct"] - media_ponderada).abs() / sigma_entre
    outliers = grupo.loc[z_scores > limite_z].copy()
    outliers["z_score"] = z_scores.loc[outliers.index]
    return outliers


def agregar_pesquisas_dataframe(
    df: pd.DataFrame,
    remover_outliers: bool = False,
    limite_z: float = 2.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Agrega pesquisas por candidato e retorna (agregado, outliers)."""
    validar_csv(df)

    base = df.copy()
    base["data"] = pd.to_datetime(base["data"], errors="raise")
    data_referencia = base["data"].max()

    resultados = []
    outliers_detectados = []

    for candidato, grupo_original in base.groupby("candidato", sort=True):
        grupo = grupo_original.copy()
        outliers_candidato = []

        while True:
            pesos = calcular_pesos_temporais(grupo["data"], data_referencia)
            media_votos = float(np.average(grupo["intencao_voto_pct"], weights=pesos))
            sigma_medio = float(np.average(grupo["desvio_padrao_pct"], weights=pesos))
            sigma_entre = desvio_entre_institutos(grupo["intencao_voto_pct"].to_numpy(), pesos)
            sigma_agregado = float(np.sqrt(sigma_medio**2 + sigma_entre**2))

            outliers = _linhas_outlier(grupo, media_votos, sigma_entre, limite_z)

            if not outliers.empty:
                outliers = outliers.assign(
                    candidato=candidato,
                    media_ponderada_pct=media_votos,
                    sigma_entre_pct=sigma_entre,
                )
                outliers_candidato.append(outliers)

            if outliers.empty or not remover_outliers:
                break

            grupo = grupo.drop(index=outliers.index)
            if grupo.empty:
                grupo = grupo_original.copy()
                break

        if outliers_candidato:
            outliers_detectados.append(pd.concat(outliers_candidato, ignore_index=True))

        resultados.append(
            {
                "candidato": candidato,
                "intencao_voto_pct": media_votos,
                "desvio_padrao_pct": sigma_agregado,
                "n_pesquisas": int(len(grupo)),
                "amostra_total": int(grupo["amostra"].sum()),
                "data_referencia": data_referencia.date().isoformat(),
            }
        )

    agregado_df = pd.DataFrame(resultados).sort_values("candidato").reset_index(drop=True)
    outliers_df = (
        pd.concat(outliers_detectados, ignore_index=True)
        if outliers_detectados
        else pd.DataFrame(
            columns=[
                "candidato",
                "instituto",
                "data",
                "intencao_voto_pct",
                "desvio_padrao_pct",
                "amostra",
                "z_score",
                "media_ponderada_pct",
                "sigma_entre_pct",
            ]
        )
    )

    return agregado_df, outliers_df


def agregar_pesquisas_csv(
    caminho_entrada: Path,
    caminho_saida: Path,
    remover_outliers: bool = False,
    limite_z: float = 2.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(caminho_entrada)
    agregado_df, outliers_df = agregar_pesquisas_dataframe(
        df,
        remover_outliers=remover_outliers,
        limite_z=limite_z,
    )

    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    agregado_df.to_csv(caminho_saida, index=False)

    return agregado_df, outliers_df


def _formatar_alertas(outliers_df: pd.DataFrame) -> Iterable[str]:
    for _, linha in outliers_df.iterrows():
        yield (
            "⚠️ OUTLIER DETECTADO: "
            f"{linha['instituto']} reporta {linha['candidato']} com "
            f"{linha['intencao_voto_pct']:.2f}% "
            f"(média: {linha['media_ponderada_pct']:.2f}% ± {linha['sigma_entre_pct']:.2f}pp, "
            f"z={linha['z_score']:.2f})"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Agrega pesquisas eleitorais por candidato")
    parser.add_argument("--input", default="data/pesquisas.csv", help="CSV de entrada")
    parser.add_argument(
        "--output",
        default="data/pesquisas_agregadas.csv",
        help="CSV agregado de saída",
    )
    parser.add_argument(
        "--remove-outliers",
        action="store_true",
        help="Remove pesquisas outliers antes de calcular o agregado",
    )
    parser.add_argument(
        "--z-threshold",
        type=float,
        default=2.0,
        help="Limiar z-score para detecção de outliers",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    entrada = Path(args.input)
    saida = Path(args.output)

    agregado_df, outliers_df = agregar_pesquisas_csv(
        caminho_entrada=entrada,
        caminho_saida=saida,
        remover_outliers=args.remove_outliers,
        limite_z=args.z_threshold,
    )

    print(f"✅ Agregação concluída: {len(agregado_df)} candidatos processados")
    print(f"📁 Arquivo gerado: {saida}")

    if outliers_df.empty:
        print("✅ Nenhum outlier detectado")
    else:
        for alerta in _formatar_alertas(outliers_df):
            print(alerta)


if __name__ == "__main__":
    main()
