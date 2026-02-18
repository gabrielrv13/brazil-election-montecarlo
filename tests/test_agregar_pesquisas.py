import pandas as pd

from src.agregar_pesquisas import agregar_pesquisas_dataframe


def test_agregacao_media_ponderada_recencia():
    df = pd.DataFrame(
        [
            {
                "candidato": "Lula",
                "intencao_voto_pct": 38.0,
                "desvio_padrao_pct": 2.0,
                "instituto": "Datafolha",
                "data": "2026-02-18",
                "amostra": 2000,
            },
            {
                "candidato": "Lula",
                "intencao_voto_pct": 36.0,
                "desvio_padrao_pct": 2.0,
                "instituto": "Quaest",
                "data": "2026-02-19",
                "amostra": 2500,
            },
            {
                "candidato": "Lula",
                "intencao_voto_pct": 37.0,
                "desvio_padrao_pct": 2.0,
                "instituto": "PoderData",
                "data": "2026-02-20",
                "amostra": 2200,
            },
        ]
    )

    agregado, outliers = agregar_pesquisas_dataframe(df)

    linha_lula = agregado.loc[agregado["candidato"] == "Lula"].iloc[0]

    assert 36.9 < linha_lula["intencao_voto_pct"] < 37.1
    assert linha_lula["desvio_padrao_pct"] > 2.0
    assert linha_lula["n_pesquisas"] == 3
    assert outliers.empty


def test_detecta_outlier_sem_remover():
    df = pd.DataFrame(
        [
            {
                "candidato": "Candidato X",
                "intencao_voto_pct": 31.0,
                "desvio_padrao_pct": 2.0,
                "instituto": "I1",
                "data": "2026-02-18",
                "amostra": 2000,
            },
            {
                "candidato": "Candidato X",
                "intencao_voto_pct": 32.0,
                "desvio_padrao_pct": 2.0,
                "instituto": "I2",
                "data": "2026-02-19",
                "amostra": 2000,
            },
            {
                "candidato": "Candidato X",
                "intencao_voto_pct": 45.0,
                "desvio_padrao_pct": 2.0,
                "instituto": "I3",
                "data": "2026-02-20",
                "amostra": 2000,
            },
        ]
    )

    _, outliers = agregar_pesquisas_dataframe(df, limite_z=1.2)

    assert len(outliers) == 1
    assert outliers.iloc[0]["instituto"] == "I3"


def test_remove_outlier_recalcula_agregado():
    df = pd.DataFrame(
        [
            {
                "candidato": "Candidato X",
                "intencao_voto_pct": 31.0,
                "desvio_padrao_pct": 2.0,
                "instituto": "I1",
                "data": "2026-02-18",
                "amostra": 2000,
            },
            {
                "candidato": "Candidato X",
                "intencao_voto_pct": 32.0,
                "desvio_padrao_pct": 2.0,
                "instituto": "I2",
                "data": "2026-02-19",
                "amostra": 2000,
            },
            {
                "candidato": "Candidato X",
                "intencao_voto_pct": 45.0,
                "desvio_padrao_pct": 2.0,
                "instituto": "I3",
                "data": "2026-02-20",
                "amostra": 2000,
            },
        ]
    )

    agregado, outliers = agregar_pesquisas_dataframe(df, remover_outliers=True, limite_z=1.2)

    linha = agregado.iloc[0]

    assert len(outliers) == 1
    assert linha["n_pesquisas"] == 2
    assert linha["intencao_voto_pct"] < 33
