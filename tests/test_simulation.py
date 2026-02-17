import numpy as np

import src.simulation as simulation


def test_primeiro_turno_somas_e_faixas():
    n_original = simulation.N_SIM
    try:
        simulation.N_SIM = 1000
        df = simulation.simular_primeiro_turno()

        totais = df[["Lula", "Flávio", "Outros", "Brancos"]].sum(axis=1)
        totais_validos = df[["Lula_val", "Flávio_val", "Outros_val"]].sum(axis=1)

        assert np.allclose(totais, 100, atol=1e-6)
        assert np.allclose(totais_validos, 100, atol=1e-6)
        assert (df[["Lula", "Flávio", "Outros", "Brancos"]] >= 0).all().all()
        assert (df["vencedor"].isin(["Lula", "Flávio Bolsonaro", "Outros"])).all()
    finally:
        simulation.N_SIM = n_original


def test_segundo_turno_somas_e_vencedor():
    n_original = simulation.N_SIM
    try:
        simulation.N_SIM = 1000
        df = simulation.simular_segundo_turno()

        totais = df[["Lula_2T", "Flávio_2T"]].sum(axis=1)

        assert np.allclose(totais, 100, atol=1e-6)
        assert (df[["Lula_2T", "Flávio_2T"]] >= 0).all().all()
        assert (df["vencedor_2T"].isin(["Lula", "Flávio Bolsonaro"])).all()
        assert (df["diferenca"] >= 0).all()
    finally:
        simulation.N_SIM = n_original
