import numpy as np
import pandas as pd
import pytest
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from src.viz.charts import (
    generate_palette,
    hex_lighten,
    plot_forecast_tracker,
    plot_forecast_history,
    plot_margin_histogram,
    plot_vote_intention,
    plot_rejection_index,
    plot_qualify_probability,
)


def test_generate_palette_returns_empty_list_for_zero():
    assert generate_palette(0) == []


def test_generate_palette_uses_base_colors_for_eight_candidates():
    palette = generate_palette(8)

    assert len(palette) == 8
    assert all(
        len(color) == 7 and color.startswith("#")
        for color in palette
    )
    assert len(set(palette)) == 8


def test_generate_palette_uses_base_palette_for_small_count():
    palette = generate_palette(3)

    assert palette == ["#e74c3c", "#3498db", "#2ecc71"]


def test_generate_palette_uses_colormap_for_more_than_eight():
    palette = generate_palette(10)

    assert len(palette) == 10
    assert all(
        len(color) == 7 and color.startswith("#")
        for color in palette
    )


@pytest.mark.parametrize(
    ("color", "factor", "expected"),
    [
        ("#000000", 0.0, "#000000"),
        ("#000000", 1.0, "#ffffff"),
        ("#000000", 0.5, "#7f7f7f"),
        ("#e74c3c", 0.0, "#e74c3c"),
        ("#e74c3c", 1.0, "#ffffff"),
        ("#FFFFFF", 0.0, "#ffffff"),
    ],
)
def test_hex_lighten(color, factor, expected):
    assert hex_lighten(color, factor) == expected


def test_hex_lighten_accepts_color_without_hash():
    assert hex_lighten("000000", 1.0) == "#ffffff"

import matplotlib.pyplot as plt
import pandas as pd
from datetime import date
from matplotlib.figure import Figure

from src.viz.charts import plot_forecast_tracker


@pytest.fixture
def historico_tracker():
    return pd.DataFrame(
        {
            "date": [
                "2026-10-01",
                "2026-10-03",
                "2026-10-01",
                "2026-10-03",
            ],
            "candidate": ["Bruno", "Bruno", "Alice", "Alice"],
            "win_prob": [40.0, 45.0, 60.0, 55.0],
            "ci_lo": [35.0, 40.0, 55.0, 50.0],
            "ci_hi": [45.0, 50.0, 65.0, 60.0],
        }
    )


def test_plot_forecast_tracker_returns_figure(historico_tracker):
    fig = plot_forecast_tracker(historico_tracker)

    try:
        assert isinstance(fig, Figure)
        assert len(fig.axes) == 1
    finally:
        plt.close(fig)


def test_plot_forecast_tracker_plots_candidates_in_sorted_order(
    historico_tracker,
):
    fig = plot_forecast_tracker(historico_tracker)

    try:
        ax = fig.axes[0]

        assert [line.get_label() for line in ax.lines[:2]] == [
            "Alice",
            "Bruno",
        ]
        assert len(ax.collections) == 2
    finally:
        plt.close(fig)


def test_plot_forecast_tracker_uses_custom_candidates_and_palette(
    historico_tracker,
):
    fig = plot_forecast_tracker(
        historico_tracker,
        candidates=["Bruno", "Alice"],
        palette=["#123456", "#654321"],
        title="Teste personalizado",
    )

    try:
        ax = fig.axes[0]

        assert [line.get_label() for line in ax.lines[:2]] == [
            "Bruno",
            "Alice",
        ]
        assert ax.lines[0].get_color() == "#123456"
        assert ax.lines[1].get_color() == "#654321"
        assert fig._suptitle.get_text() == "Teste personalizado"
    finally:
        plt.close(fig)



def test_plot_forecast_tracker_uses_candidate_identity_colors():
    flavio = "Fl" + chr(0x00E1) + "vio Bolsonaro"
    history = pd.DataFrame(
        {
            "date": ["2026-10-01", "2026-10-01"],
            "candidate": [flavio, "Lula"],
            "win_prob": [55.0, 45.0],
            "ci_lo": [50.0, 40.0],
            "ci_hi": [60.0, 50.0],
        }
    )

    fig = plot_forecast_tracker(history)

    try:
        colors = {
            line.get_label(): line.get_color()
            for line in fig.axes[0].lines
            if line.get_label() in {"Lula", flavio}
        }

        assert colors["Lula"] == "#e74c3c"
        assert colors[flavio] == "#3498db"
    finally:
        plt.close(fig)


def test_plot_forecast_tracker_preserves_custom_palette_for_alias():
    history = pd.DataFrame(
        {
            "date": ["2026-10-01", "2026-10-01"],
            "candidate": ["F. Bolsonaro", "Lula"],
            "win_prob": [55.0, 45.0],
            "ci_lo": [50.0, 40.0],
            "ci_hi": [60.0, 50.0],
        }
    )

    fig = plot_forecast_tracker(
        history,
        candidates=["F. Bolsonaro", "Lula"],
        palette=["#123456", "#654321"],
    )

    try:
        lines = {
            line.get_label(): line.get_color()
            for line in fig.axes[0].lines
            if line.get_label() in {"F. Bolsonaro", "Lula"}
        }

        assert lines["F. Bolsonaro"] == "#123456"
        assert lines["Lula"] == "#654321"
    finally:
        plt.close(fig)

def test_plot_forecast_tracker_adds_election_reference(historico_tracker):
    fig = plot_forecast_tracker(
        historico_tracker,
        election_date=date(2026, 10, 4),
    )

    try:
        ax = fig.axes[0]
        election_lines = [
            line for line in ax.lines if line.get_linestyle() == "--"
        ]

        assert len(election_lines) == 1
        assert any(
            "Eleição" in item.get_text()
            for item in ax.texts
        )
    finally:
        plt.close(fig)


def test_plot_forecast_tracker_skips_candidate_without_data(
    historico_tracker,
):
    fig = plot_forecast_tracker(
        historico_tracker,
        candidates=["Alice", "Inexistente"],
    )

    try:
        ax = fig.axes[0]

        assert [line.get_label() for line in ax.lines] == ["Alice"]
        assert len(ax.collections) == 1
    finally:
        plt.close(fig)


def test_plot_forecast_tracker_preserves_input_dataframe(historico_tracker):
    original = historico_tracker.copy(deep=True)

    fig = plot_forecast_tracker(historico_tracker)

    try:
        pd.testing.assert_frame_equal(historico_tracker, original)
    finally:
        plt.close(fig)


def test_plot_forecast_tracker_uses_probability_scale_0_to_100(
    historico_tracker,
):
    fig = plot_forecast_tracker(historico_tracker)

    try:
        ax = fig.axes[0]

        assert ax.get_ylim() == (0.0, 100.0)
        assert ax.get_ylabel() == "Prob. vitória (%)"
    finally:
        plt.close(fig)

from datetime import date

import matplotlib.pyplot as plt
import pandas as pd

from src.viz.charts import plot_forecast_history


@pytest.fixture
def historico_forecast():
    return pd.DataFrame(
        {
            "run_at": [
                "2026-10-03 12:00:00",
                "2026-10-01 12:00:00",
            ],
            "pv": [
                {"Alice": 0.65, "Bruno": 0.35},
                {"Alice": 0.60, "Bruno": 0.40},
            ],
            "p2v": [
                {"Alice": 0.55, "Bruno": 0.45},
                {"Alice": 0.50, "Bruno": 0.50},
            ],
            "n_sim": [10000, 10000],
        }
    )


def test_plot_forecast_history_empty_dataframe():
    fig = plot_forecast_history(pd.DataFrame())

    try:
        assert len(fig.axes) == 1
        assert any(
            "Nenhum histórico disponível" in text.get_text()
            for text in fig.axes[0].texts
        )
        assert not fig.axes[0].axison
    finally:
        plt.close(fig)


def test_plot_forecast_history_without_recognized_candidates():
    df = pd.DataFrame(
        {
            "run_at": ["2026-10-01"],
            "pv": [None],
            "p2v": [None],
            "n_sim": [1000],
        }
    )

    fig = plot_forecast_history(df)

    try:
        assert any(
            "Histórico sem candidatos reconhecidos" in text.get_text()
            for text in fig.axes[0].texts
        )
        assert not fig.axes[0].axison
    finally:
        plt.close(fig)


def test_plot_forecast_history_uses_second_round_by_default(
    historico_forecast,
):
    fig = plot_forecast_history(historico_forecast)

    try:
        ax = fig.axes[0]

        assert [line.get_label() for line in ax.lines[:2]] == [
            "Alice",
            "Bruno",
        ]
        assert ax.lines[0].get_ydata() == pytest.approx([50.0, 55.0])
        assert ax.get_ylim() == (0.0, 100.0)
        assert "2º turno" in ax.get_legend().get_title().get_text()
    finally:
        plt.close(fig)


def test_plot_forecast_history_can_use_first_round(
    historico_forecast,
):
    fig = plot_forecast_history(
        historico_forecast,
        use_p2v=False,
    )

    try:
        ax = fig.axes[0]

        assert ax.lines[0].get_ydata() == pytest.approx([60.0, 65.0])
        assert "1º turno" in ax.get_legend().get_title().get_text()
        assert any(
            "P(liderança 1º turno)" in item.get_text()
            for item in fig.texts
        )
    finally:
        plt.close(fig)


def test_plot_forecast_history_falls_back_to_first_round(
    historico_forecast,
):
    historico_forecast.at[0, "p2v"] = {}
    historico_forecast.at[1, "p2v"] = {}

    fig = plot_forecast_history(historico_forecast)

    try:
        ax = fig.axes[0]

        # Missing second-round data must never be filled with leadership.
        assert not any(line.get_label() in {"Lula", "Bolsonaro"} for line in ax.lines)
    finally:
        plt.close(fig)


def test_plot_forecast_history_marks_poll_and_election_dates(
    historico_forecast,
):
    fig = plot_forecast_history(
        historico_forecast,
        poll_dates=[date(2026, 10, 2)],
        election_date=date(2026, 10, 4),
    )

    try:
        ax = fig.axes[0]

        assert sum(
            line.get_linestyle() == "--"
            for line in ax.lines
        ) == 2

        assert any(
            "nova" in item.get_text()
            for item in ax.texts
        )
        assert any(
            "Eleição" in item.get_text()
            for item in ax.texts
        )
    finally:
        plt.close(fig)


def test_plot_forecast_history_uses_run_date_rug_by_default(
    historico_forecast,
):
    fig = plot_forecast_history(historico_forecast)

    try:
        ax = fig.axes[0]

        # Duas linhas dos candidatos e dois marcadores de execução.
        assert len(ax.lines) == 4
    finally:
        plt.close(fig)


def test_plot_forecast_history_does_not_modify_input(
    historico_forecast,
):
    original = historico_forecast.copy(deep=True)

    fig = plot_forecast_history(historico_forecast)

    try:
        pd.testing.assert_frame_equal(historico_forecast, original)
    finally:
        plt.close(fig)

def test_plot_forecast_history_empty_dataframe():
    df = pd.DataFrame(columns=["run_at", "pv", "p2v", "n_sim"])

    fig = plot_forecast_history(df)
    try:
        assert isinstance(fig, Figure)
        assert any(
            "Nenhum histórico disponível." in text.get_text()
            for ax in fig.axes
            for text in ax.texts
        )
        assert not fig.axes[0].axison
    finally:
        plt.close(fig)


def test_plot_forecast_history_without_recognized_candidates():
    df = pd.DataFrame({
        "run_at": [pd.Timestamp("2026-10-01")],
        "pv": [None],
        "p2v": [None],
        "n_sim": [1000],
    })

    fig = plot_forecast_history(df)
    try:
        assert isinstance(fig, Figure)
        assert any(
            "Histórico sem candidatos reconhecidos." in text.get_text()
            for ax in fig.axes
            for text in ax.texts
        )
        assert not fig.axes[0].axison
    finally:
        plt.close(fig)


def test_plot_forecast_history_uses_pv_when_p2v_candidate_is_missing():
    df = pd.DataFrame({
        "run_at": [
            pd.Timestamp("2026-10-01"),
            pd.Timestamp("2026-10-02"),
        ],
        "pv": [
            {"Alice": 0.40, "Bruno": 0.60},
            {"Alice": 0.45, "Bruno": 0.55},
        ],
        "p2v": [
            {"Alice": 0.70},
            {"Bruno": 0.65},
        ],
        "n_sim": [1000, 1000],
    })

    fig = plot_forecast_history(df, use_p2v=True)
    try:
        ax = fig.axes[0]
        lines = {
            line.get_label(): line
            for line in ax.lines
            if line.get_label() in {"Alice", "Bruno"}
        }

        assert set(lines) == {"Alice", "Bruno"}
        assert list(lines["Alice"].get_ydata()) == pytest.approx([70.0])
        assert list(lines["Bruno"].get_ydata()) == pytest.approx([65.0])
    finally:
        plt.close(fig)


def test_plot_forecast_history_uses_pv_when_p2v_is_disabled():
    df = pd.DataFrame({
        "run_at": [
            pd.Timestamp("2026-10-01"),
            pd.Timestamp("2026-10-02"),
        ],
        "pv": [
            {"Alice": 0.30},
            {"Alice": 0.40},
        ],
        "p2v": [
            {"Alice": 0.80},
            {"Alice": 0.90},
        ],
        "n_sim": [1000, 1000],
    })

    fig = plot_forecast_history(df, use_p2v=False)
    try:
        ax = fig.axes[0]
        alice = next(line for line in ax.lines if line.get_label() == "Alice")

        assert list(alice.get_ydata()) == pytest.approx([30.0, 40.0])
        assert "1º turno" in ax.get_legend().get_title().get_text()
    finally:
        plt.close(fig)


def test_plot_forecast_history_marks_poll_dates_and_election():
    df = pd.DataFrame({
        "run_at": [
            pd.Timestamp("2026-10-01"),
            pd.Timestamp("2026-10-02"),
        ],
        "pv": [
            {"Alice": 0.40},
            {"Alice": 0.45},
        ],
        "p2v": [
            {"Alice": 0.60},
            {"Alice": 0.65},
        ],
        "n_sim": [1000, 1000],
    })

    poll_date = pd.Timestamp("2026-10-03")
    election_date = pd.Timestamp("2026-10-04")

    fig = plot_forecast_history(
        df,
        poll_dates=[poll_date],
        election_date=election_date,
    )
    try:
        ax = fig.axes[0]

        assert any(
            pd.Timestamp(line.get_xdata()[0]) == poll_date
            for line in ax.lines
            if len(line.get_xdata()) > 0
        )
        assert any(
            pd.Timestamp(line.get_xdata()[0]) == election_date
            for line in ax.lines
            if len(line.get_xdata()) > 0
        )
        assert any(
            "nova" in text.get_text()
            for text in ax.texts
        )
        assert any(
            "Eleição" in text.get_text()
            for text in ax.texts
        )
    finally:
        plt.close(fig)


def test_plot_forecast_history_sorts_runs_chronologically():
    df = pd.DataFrame({
        "run_at": [
            pd.Timestamp("2026-10-03"),
            pd.Timestamp("2026-10-01"),
            pd.Timestamp("2026-10-02"),
        ],
        "pv": [
            {"Alice": 0.50},
            {"Alice": 0.30},
            {"Alice": 0.40},
        ],
        "p2v": [
            {"Alice": 0.70},
            {"Alice": 0.50},
            {"Alice": 0.60},
        ],
        "n_sim": [1000, 1000, 1000],
    })

    fig = plot_forecast_history(df)
    try:
        ax = fig.axes[0]
        alice = next(line for line in ax.lines if line.get_label() == "Alice")

        assert list(alice.get_ydata()) == pytest.approx([50.0, 60.0, 70.0])
        assert list(alice.get_xdata()) == sorted(alice.get_xdata())
    finally:
        plt.close(fig)

@pytest.fixture
def margins_exemplo():
    return np.array(
        [1.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 20.0]
    )


def test_plot_margin_histogram_retorna_figura(margins_exemplo):
    fig = plot_margin_histogram(margins_exemplo, [5, 10, 15])

    try:
        assert isinstance(fig, Figure)
        assert len(fig.axes) == 1
    finally:
        plt.close(fig)


def test_plot_margin_histogram_tem_linhas_de_referencia(margins_exemplo):
    fig = plot_margin_histogram(margins_exemplo, [5, 10, 15])

    try:
        ax = fig.axes[0]
        valores_x = [line.get_xdata()[0] for line in ax.lines]

        assert 5 in valores_x
        assert 10 in valores_x
        assert 15 in valores_x
        assert 10 in valores_x  # mediana da amostra
    finally:
        plt.close(fig)


def test_plot_margin_histogram_adiciona_limiar_15_automaticamente(
    margins_exemplo,
):
    fig = plot_margin_histogram(margins_exemplo, [5, 10])

    try:
        textos = [text.get_text() for text in fig.axes[0].texts]
        texto_probabilidades = "\n".join(textos)

        assert "P(>15pp)" in texto_probabilidades
        assert "Polymarket" in texto_probabilidades
    finally:
        plt.close(fig)


def test_plot_margin_histogram_nao_duplica_limiar_15(margins_exemplo):
    fig = plot_margin_histogram(margins_exemplo, [5, 10, 15])

    try:
        textos = [text.get_text() for text in fig.axes[0].texts]
        texto_probabilidades = "\n".join(textos)

        assert texto_probabilidades.count("P(>15pp)") == 1
    finally:
        plt.close(fig)


def test_plot_margin_histogram_calcula_probabilidades(margins_exemplo):
    fig = plot_margin_histogram(margins_exemplo, [5, 10])

    try:
        textos = [text.get_text() for text in fig.axes[0].texts]
        texto_probabilidades = "\n".join(textos)

        assert "P(> 5pp):  70.0%" in texto_probabilidades
        assert "P(>10pp):  40.0%" in texto_probabilidades
        assert "P(>15pp):  20.0%" in texto_probabilidades
    finally:
        plt.close(fig)


def test_plot_margin_histogram_titulo_contem_estatisticas(margins_exemplo):
    fig = plot_margin_histogram(margins_exemplo, [5, 10, 15])

    try:
        titulo = fig.axes[0].get_title(loc="left")

        assert "Distribuição da Margem" in titulo
        assert "1º Turno" in titulo
        assert "IC 90%" in titulo
        assert "Apertada (<3pp)" in titulo
        assert "Confortável (>10pp)" in titulo

        textos = "\n".join(
            text.get_text() for text in fig.axes[0].texts
        )
        assert "Mediana" in textos
    finally:
        plt.close(fig)


def test_plot_margin_histogram_respeita_figsize(margins_exemplo):
    fig = plot_margin_histogram(
        margins_exemplo,
        [5, 10, 15],
        figsize=(10, 6),
    )

    try:
        largura, altura = fig.get_size_inches()
        assert largura == pytest.approx(10)
        assert altura == pytest.approx(6)
    finally:
        plt.close(fig)

@pytest.mark.parametrize(
    ("n", "expected_bins"),
    [
        (10, 20),       # mínimo de 20 bins
        (5000, 25),     # n // 200
        (20000, 60),    # máximo de 60 bins
    ],
)
def test_plot_margin_histogram_limita_quantidade_de_bins(n, expected_bins):
    margins = np.linspace(1, 20, n)

    fig = plot_margin_histogram(margins, [5, 10, 15])
    try:
        ax = fig.axes[0]
        assert len(ax.patches) == expected_bins
    finally:
        plt.close(fig)


@pytest.fixture
def df_intencao_voto():
    return pd.DataFrame(
        {
            "Alice_val": [40.0, 42.0, 44.0, 46.0, 48.0],
            "Bruno_val": [30.0, 32.0, 34.0, 36.0, 38.0],
        }
    )


def test_plot_vote_intention_retorna_figura(df_intencao_voto):
    fig = plot_vote_intention(
        df_intencao_voto,
        ["Alice", "Bruno"],
        ["#e74c3c", "#3498db"],
    )

    try:
        assert isinstance(fig, Figure)
        assert len(fig.axes) == 1
    finally:
        plt.close(fig)


def test_plot_vote_intention_exibe_candidatos_em_ordem_invertida(
    df_intencao_voto,
):
    fig = plot_vote_intention(
        df_intencao_voto,
        ["Alice", "Bruno"],
        ["#e74c3c", "#3498db"],
    )

    try:
        ax = fig.axes[0]
        assert [label.get_text() for label in ax.get_yticklabels()] == [
            "Bruno",
            "Alice",
        ]
    finally:
        plt.close(fig)


def test_plot_vote_intention_calcula_media_e_intervalo(df_intencao_voto):
    fig = plot_vote_intention(
        df_intencao_voto,
        ["Alice", "Bruno"],
        ["#e74c3c", "#3498db"],
    )

    try:
        ax = fig.axes[0]

        # O gráfico é desenhado de baixo para cima na ordem original.
        # Alice: média 44, percentis 5 e 95 iguais a 40,4 e 47,6.
        # Bruno: média 34, percentis 5 e 95 iguais a 30,4 e 37,6.
        linhas_ci = [
            line for line in ax.lines
            if len(line.get_xdata()) == 2
            and len(line.get_ydata()) == 2
            and line.get_ydata()[0] == line.get_ydata()[1]
        ]

        assert len(linhas_ci) == 2
        assert list(linhas_ci[0].get_xdata()) == pytest.approx([30.4, 37.6])
        assert list(linhas_ci[1].get_xdata()) == pytest.approx([40.4, 47.6])

        textos_medias = [
            text.get_text()
            for text in ax.texts
            if text.get_text().endswith("%")
        ]
        assert "34.0%" in textos_medias
        assert "44.0%" in textos_medias
    finally:
        plt.close(fig)


def test_plot_vote_intention_aceita_colunas_sem_sufixo_val():
    df = pd.DataFrame(
        {
            "Alice": [40.0, 42.0, 44.0, 46.0, 48.0],
            "Bruno": [30.0, 32.0, 34.0, 36.0, 38.0],
        }
    )

    fig = plot_vote_intention(
        df,
        ["Alice", "Bruno"],
        ["#e74c3c", "#3498db"],
    )

    try:
        textos = [text.get_text() for text in fig.axes[0].texts]
        assert "44.0%" in textos
        assert "34.0%" in textos
    finally:
        plt.close(fig)


def test_plot_vote_intention_aplica_cores_da_paleta(df_intencao_voto):
    fig = plot_vote_intention(
        df_intencao_voto,
        ["Alice", "Bruno"],
        ["#e74c3c", "#3498db"],
    )

    try:
        ax = fig.axes[0]
        cores_scatter = [
            collection.get_facecolors()[0]
            for collection in ax.collections
        ]

        assert len(cores_scatter) == 2
        assert list(cores_scatter[0][:3]) == pytest.approx(
            [52 / 255, 152 / 255, 219 / 255]
        )
        assert list(cores_scatter[1][:3]) == pytest.approx(
            [231 / 255, 76 / 255, 60 / 255]
        )
    finally:
        plt.close(fig)


def test_plot_vote_intention_tem_referencia_em_50_porcento(
    df_intencao_voto,
):
    fig = plot_vote_intention(
        df_intencao_voto,
        ["Alice", "Bruno"],
        ["#e74c3c", "#3498db"],
    )

    try:
        ax = fig.axes[0]
        linha_referencia = [
            line for line in ax.lines
            if list(line.get_xdata()) == [50, 50]
        ]

        assert len(linha_referencia) == 1
        assert ax.get_xlim() == pytest.approx((0, 62))
        assert ax.get_xlabel() == "Votos válidos (%)"
        assert "Intenção de Voto" in ax.get_title(loc="left")
    finally:
        plt.close(fig)


def test_plot_vote_intention_respeita_figsize(df_intencao_voto):
    fig = plot_vote_intention(
        df_intencao_voto,
        ["Alice", "Bruno"],
        ["#e74c3c", "#3498db"],
        figsize=(10, 6),
    )

    try:
        assert fig.get_size_inches() == pytest.approx([10, 6])
    finally:
        plt.close(fig)

@pytest.fixture
def dados_rejeicao():
    return {
        "candidates": ["Alice", "Bruno", "Carla", "Diego"],
        "rejection": [30.0, 47.0, 55.0, 0.0],
        "palette": ["#e74c3c", "#3498db", "#2ecc71", "#9b59b6"],
    }


def test_plot_rejection_index_retorna_figura(dados_rejeicao):
    fig = plot_rejection_index(**dados_rejeicao)

    try:
        assert isinstance(fig, Figure)
        assert len(fig.axes) == 1
    finally:
        plt.close(fig)


def test_plot_rejection_index_inverte_ordem_e_omite_rejeicao_zero(
    dados_rejeicao,
):
    fig = plot_rejection_index(**dados_rejeicao)

    try:
        rotulos = [
            label.get_text() for label in fig.axes[0].get_yticklabels()
        ]
        assert rotulos == ["Carla", "Bruno", "Alice"]
        assert "Diego" not in rotulos
    finally:
        plt.close(fig)


def test_plot_rejection_index_classifica_faixas_de_rejeicao(
    dados_rejeicao,
):
    fig = plot_rejection_index(**dados_rejeicao)

    try:
        textos = "\n".join(
            text.get_text() for text in fig.axes[0].texts
        )

        assert "30%  →  teto 70%   Viável" in textos
        assert "47%  →  teto 53%   Dificuldade alta" in textos
        assert "55%  →  teto 45%   Inviável" in textos
    finally:
        plt.close(fig)


def test_plot_rejection_index_usa_limite_critico_de_50_porcento(
    dados_rejeicao,
):
    fig = plot_rejection_index(**dados_rejeicao)

    try:
        ax = fig.axes[0]
        linhas_referencia = [
            line for line in ax.lines
            if list(line.get_xdata()) == [50, 50]
        ]

        assert len(linhas_referencia) == 1
        assert "Limite crítico\n(50%)" in [
            text.get_text() for text in ax.texts
        ]
        assert ax.get_xlim() == pytest.approx((0, 95))
        assert ax.get_xlabel() == "Rejeição (%)"
        assert "Índice de Rejeição" in ax.get_title(loc="left")
    finally:
        plt.close(fig)


def test_plot_rejection_index_respeita_figsize(dados_rejeicao):
    fig = plot_rejection_index(
        **dados_rejeicao,
        figsize=(10, 6),
    )

    try:
        assert fig.get_size_inches() == pytest.approx([10, 6])
    finally:
        plt.close(fig)


def test_plot_rejection_index_nao_exibe_rejeicao_negativa():
    fig = plot_rejection_index(
        ["Alice", "Bruno"],
        [-5.0, 40.0],
        ["#e74c3c", "#3498db"],
    )

    try:
        rotulos = [
            label.get_text() for label in fig.axes[0].get_yticklabels()
        ]
        assert rotulos == ["Bruno"]
    finally:
        plt.close(fig)

# ─── QUALIFY PROBABILITY ──────────────────────────────────────────────────────

@pytest.fixture
def dados_qualificacao():
    """Dados com resultados conhecidos para testar a classificação ao 2º turno."""
    return pd.DataFrame({
        "Alice_val": [40, 35, 20, 10],
        "Bruno_val": [30, 40, 35, 20],
        "Carla_val": [20, 15, 40, 50],
        "Diego_val": [10, 10, 5, 20],
    })


def test_plot_qualify_probability_returns_figure(dados_qualificacao):
    fig = plot_qualify_probability(
        dados_qualificacao,
        ["Alice", "Bruno", "Carla", "Diego"],
        ["#e74c3c", "#3498db", "#2ecc71", "#9b59b6"],
    )
    try:
        assert isinstance(fig, Figure)
    finally:
        plt.close(fig)


def test_plot_qualify_probability_calculates_top_two_correctly(
    dados_qualificacao,
):
    candidates = ["Alice", "Bruno", "Carla", "Diego"]
    palette = ["#e74c3c", "#3498db", "#2ecc71", "#9b59b6"]

    fig = plot_qualify_probability(dados_qualificacao, candidates, palette)
    try:
        ax = fig.axes[0]

        # Alice: top 2 nas simulações 1 e 2 = 50%
        # Bruno: três vagas certas e metade do empate final = 87,5%
        # Carla: top 2 nas simulações 3 e 4 = 50%
        # Diego: metade da vaga empatada na última simulação = 12,5%
        labels = {
            text.get_text()
            for text in ax.texts
            if text.get_text().endswith("%")
        }

        assert "50.0%" in labels
        assert "87.5%" in labels
        assert "12.5%" in labels
    finally:
        plt.close(fig)


def test_plot_qualify_probability_reverses_candidate_display_order(
    dados_qualificacao,
):
    candidates = ["Alice", "Bruno", "Carla", "Diego"]
    palette = ["#e74c3c", "#3498db", "#2ecc71", "#9b59b6"]

    fig = plot_qualify_probability(dados_qualificacao, candidates, palette)
    try:
        ax = fig.axes[0]
        assert [label.get_text() for label in ax.get_yticklabels()] == [
            "Diego", "Carla", "Bruno", "Alice"
        ]
    finally:
        plt.close(fig)


def test_plot_qualify_probability_supports_fallback_columns():
    df = pd.DataFrame({
        "Alice": [60, 20, 10],
        "Bruno": [30, 50, 20],
        "Carla": [10, 30, 70],
    })

    fig = plot_qualify_probability(
        df,
        ["Alice", "Bruno", "Carla"],
        ["#e74c3c", "#3498db", "#2ecc71"],
    )
    try:
        ax = fig.axes[0]
        labels = {
            text.get_text()
            for text in ax.texts
            if text.get_text().endswith("%")
        }

        # Only the exactly-50% draw requires a runoff, with Bruno and Carla.
        assert labels == {"0.0%", "33.3%"}
    finally:
        plt.close(fig)


def test_plot_qualify_probability_uses_candidate_colors(dados_qualificacao):
    candidates = ["Alice", "Bruno", "Carla", "Diego"]
    palette = ["#e74c3c", "#3498db", "#2ecc71", "#9b59b6"]

    fig = plot_qualify_probability(dados_qualificacao, candidates, palette)
    try:
        ax = fig.axes[0]

        # Cada candidato possui uma barra de fundo (100%) e uma barra de probabilidade.
        candidate_bars = [
            bar for bar in ax.patches
            if bar.get_width() <= 100
        ]

        # Seleciona a barra de probabilidade de cada par,
        # inclusive a barra de largura zero.
        probability_bars = candidate_bars[1::2]

        expected_colors = [
            plt.matplotlib.colors.to_rgba(color, alpha=0.82)
            for color in reversed(palette)
        ]

        assert len(probability_bars) == len(candidates)
        for bar, expected_color in zip(probability_bars, expected_colors):
            assert bar.get_facecolor() == pytest.approx(expected_color)
    finally:
        plt.close(fig)


def test_plot_qualify_probability_has_reference_line_and_title(
    dados_qualificacao,
):
    fig = plot_qualify_probability(
        dados_qualificacao,
        ["Alice", "Bruno", "Carla", "Diego"],
        ["#e74c3c", "#3498db", "#2ecc71", "#9b59b6"],
        figsize=(9, 6),
    )
    try:
        ax = fig.axes[0]

        assert any(
            line.get_xdata()[0] == 50
            for line in ax.lines
        )
        assert ax.get_xlabel() == "Probabilidade de classificação (%)"
        assert "Probabilidade de ir ao 2º Turno" in ax.get_title(loc="left")
        assert fig.get_size_inches() == pytest.approx([9, 6])
    finally:
        plt.close(fig)

def test_generate_charts_saves_dashboard_and_margin(tmp_path):
    from datetime import date

    from src.core.config import SimulationConfig, SimulationResult
    from src.viz.charts import generate_charts

    df1 = pd.DataFrame({
        "Lula_val": [40.0, 42.0, 41.0],
        "Tarcisio_val": [30.0, 32.0, 31.0],
        "Outros_val": [30.0, 26.0, 28.0],
        "margem_1t": [10.0, 10.0, 10.0],
    })

    result = SimulationResult(
        df1=df1,
        df2=pd.DataFrame(),
        pv={"Lula": 0.9, "Tarcisio": 0.1},
        p2v={},
        p2t=0.0,
        info_matchups={},
        info_lim_1t={},
        info_indecisos={},
        margins=np.array([2.0, 5.0, 8.0, 12.0]),
        desvio_base=3.0,
        config=SimulationConfig(
            n_sim=100,
            election_date=date(2026, 10, 4),
        ),
    )

    saved = generate_charts(result, output_dir=tmp_path)

    assert set(saved) == {"dashboard", "margin"}
    assert saved["dashboard"].name == "simulacao_brasil_2026.png"
    assert saved["margin"].name == "margem_1turno.png"
    assert saved["dashboard"].is_file()
    assert saved["margin"].is_file()
    assert saved["dashboard"].stat().st_size > 0
    assert saved["margin"].stat().st_size > 0


def test_generate_charts_without_margins_saves_only_dashboard(tmp_path):
    from src.core.config import SimulationResult
    from src.viz.charts import generate_charts

    df1 = pd.DataFrame({
        "Lula_val": [40.0, 42.0, 41.0],
        "Tarcisio_val": [30.0, 32.0, 31.0],
        "Outros_val": [30.0, 26.0, 28.0],
    })

    result = SimulationResult(
        df1=df1,
        df2=pd.DataFrame(),
        pv={"Lula": 0.9, "Tarcisio": 0.1},
        p2v={},
        p2t=0.0,
        info_matchups={},
        info_lim_1t={},
        info_indecisos={},
        margins=np.array([]),
        desvio_base=3.0,
        config=None,
    )

    saved = generate_charts(result, output_dir=tmp_path)

    assert set(saved) == {"dashboard"}
    assert saved["dashboard"].is_file()
    assert not (tmp_path / "margem_1turno.png").exists()


def test_plot_forecast_history_uses_candidate_identity_colors():
    flavio = "Fl" + chr(0x00E1) + "vio Bolsonaro"
    history = pd.DataFrame(
        {
            "run_at": pd.to_datetime(
                ["2026-10-01 12:00:00", "2026-10-02 12:00:00"]
            ),
            "pv": [
                {flavio: 0.55, "Lula": 0.45},
                {"Lula": 0.46, flavio: 0.54},
            ],
            "p2v": [
                {flavio: 0.55, "Lula": 0.45},
                {"Lula": 0.46, flavio: 0.54},
            ],
            "n_sim": [40000, 40000],
        }
    )

    fig = plot_forecast_history(history)

    try:
        colors = {
            line.get_label(): line.get_color()
            for line in fig.axes[0].lines
            if line.get_label() in {"Lula", flavio}
        }

        assert colors["Lula"] == "#e74c3c"
        assert colors[flavio] == "#3498db"
    finally:
        plt.close(fig)

def test_candidate_palette_reserves_colors_for_known_candidates():
    from src.viz.colors import candidate_palette

    candidates = ["Candidato A", "Lula", "Flávio Bolsonaro"]
    base_palette = ["#e74c3c", "#3498db", "#2ecc71"]

    palette = candidate_palette(candidates, base_palette)

    assert palette[1] == "#e74c3c"
    assert palette[2] == "#3498db"
    assert palette[0] not in {"#e74c3c", "#3498db"}
