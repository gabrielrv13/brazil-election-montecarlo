"""Compatibility simulation module for automated tests."""
from __future__ import annotations
import numpy as np
import pandas as pd

N_SIM = 40_000

_BASE_MEDIA = np.array([37.0, 27.0, 21.0, 15.0], dtype=float)


def simular_primeiro_turno() -> pd.DataFrame:
    alpha = np.clip(_BASE_MEDIA, 0.1, None)
    votos = np.random.dirichlet(alpha, size=N_SIM) * 100
    df = pd.DataFrame(votos, columns=["Lula", "Flávio", "Outros", "Brancos"])
    validos = df[["Lula", "Flávio", "Outros"]].sum(axis=1)
    for col in ["Lula", "Flávio", "Outros"]:
        df[f"{col}_val"] = df[col] / validos * 100
    idx = np.argmax(df[["Lula_val", "Flávio_val", "Outros_val"]].values, axis=1)
    df["vencedor"] = np.array(["Lula", "Flávio Bolsonaro", "Outros"])[idx]
    return df


def simular_segundo_turno() -> pd.DataFrame:
    df1 = simular_primeiro_turno()
    outros = df1["Outros_val"].to_numpy()
    transf = np.random.beta(5, 4, size=N_SIM)
    lula = (df1["Lula_val"] + outros * transf).to_numpy()
    flavio = (df1["Flávio_val"] + outros * (1 - transf)).to_numpy()
    total = lula + flavio
    lula, flavio = lula / total * 100, flavio / total * 100
    df2 = pd.DataFrame({"Lula_2T": lula, "Flávio_2T": flavio})
    df2["vencedor_2T"] = np.where(lula >= flavio, "Lula", "Flávio Bolsonaro")
    df2["diferenca"] = np.abs(lula - flavio)
    return df2
