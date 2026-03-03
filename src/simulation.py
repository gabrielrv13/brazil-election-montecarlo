"""Compatibility simulation module used by automated tests.

This module provides a stable API (`simular_primeiro_turno` and
`simular_segundo_turno`) while the main implementation evolves in other files.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

N_SIM = 40_000

# Média simples em % para [Lula, Flávio, Outros, Brancos]
_BASE_MEDIA = np.array([37.0, 27.0, 21.0, 15.0], dtype=float)



def _sample_primeiro_turno(n: int) -> np.ndarray:
    """Gera intenções de voto que sempre somam 100%."""
    alpha = np.clip(_BASE_MEDIA, 0.1, None)
    return np.random.dirichlet(alpha, size=n) * 100



def simular_primeiro_turno() -> pd.DataFrame:
    """Simula cenários do 1º turno e retorna DataFrame padronizado."""
    votos = _sample_primeiro_turno(N_SIM)

    df = pd.DataFrame(votos, columns=["Lula", "Flávio", "Outros", "Brancos"])

    validos = df[["Lula", "Flávio", "Outros"]].sum(axis=1)
    for col in ["Lula", "Flávio", "Outros"]:
        df[f"{col}_val"] = df[col] / validos * 100

    vencedor_idx = np.argmax(df[["Lula_val", "Flávio_val", "Outros_val"]].values, axis=1)
    mapa_vencedor = np.array(["Lula", "Flávio Bolsonaro", "Outros"], dtype=object)
    df["vencedor"] = mapa_vencedor[vencedor_idx]

    return df



def simular_segundo_turno() -> pd.DataFrame:
    """Simula 2º turno entre Lula e Flávio Bolsonaro."""
    df1 = simular_primeiro_turno()

    lula_base = df1["Lula_val"].to_numpy()
    flavio_base = df1["Flávio_val"].to_numpy()
    outros = df1["Outros_val"].to_numpy()

    # Distribui votos de "Outros" com leve viés para o candidato menos rejeitado.
    transf_lula = np.random.beta(5, 4, size=N_SIM)  # média ~55.5%
    lula_2t = lula_base + outros * transf_lula
    flavio_2t = flavio_base + outros * (1 - transf_lula)

    total = lula_2t + flavio_2t
    lula_2t = lula_2t / total * 100
    flavio_2t = flavio_2t / total * 100

    df2 = pd.DataFrame({"Lula_2T": lula_2t, "Flávio_2T": flavio_2t})
    df2["vencedor_2T"] = np.where(df2["Lula_2T"] >= df2["Flávio_2T"], "Lula", "Flávio Bolsonaro")
    df2["diferenca"] = (df2["Lula_2T"] - df2["Flávio_2T"]).abs()

    return df2
