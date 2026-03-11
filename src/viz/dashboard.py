"""
src/viz/dashboard.py
====================
Streamlit dashboard for brazil-election-montecarlo v3.0.

Imports exclusively from:
    src.core.config      — SimulationConfig, SimulationResult, PollData
    src.core.simulation  — simular_primeiro_turno
    src.core.polymarket  — polymarket_edge
    src.io               — load_polls
    src.io.history       — init_db, salvar_historico, carregar_historico
    src.io.report        — generate_pdf, save_csvs
    src.viz.charts       — all visualization functions

Zero imports from simulation_v2, simulation_combined, or any legacy module.

Usage:
    streamlit run src/viz/dashboard.py
"""

from __future__ import annotations

import sys
import tempfile
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

# ── Path setup — allow running from project root or from src/viz/ ─────────────
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ── v3 public APIs ────────────────────────────────────────────────────────────
from src.core.config import SimulationConfig, SimulationResult
from src.io import load_polls
from src.io.report import generate_pdf, save_csvs
from src.viz.charts import (
    MARGIN_THRESHOLDS,
    generate_palette,
    plot_forecast_history,
    plot_margin_histogram,
    plot_simulation_dashboard,
    plot_vote_intention,
)

try:
    from src.core.polymarket import polymarket_edge
except ImportError:
    polymarket_edge = None  # type: ignore[assignment]

try:
    from src.core.simulation import simular_primeiro_turno
except ImportError:
    simular_primeiro_turno = None  # type: ignore[assignment]

# ── Constants ─────────────────────────────────────────────────────────────────
_ELEITORADO: int    = 158_600_000
_ELECTION_DATE: date = date(2026, 10, 4)
_DB_PATH: Path      = _ROOT / "outputs" / "forecast_history.db"
_OUTPUT_DIR: Path   = _ROOT / "outputs"

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Brazil 2026 — Election Forecast",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── HELPERS ──────────────────────────────────────────────────────────────────

_DEFAULT_CSV = pd.DataFrame({
    "candidato":         ["Lula", "Flávio Bolsonaro", "Outros", "Brancos/Nulos"],
    "intencao_voto_pct": [35.0, 29.0, 21.0, 15.0],
    "rejeicao_pct":      [42.0, 48.0,  0.0,  0.0],
    "desvio_padrao_pct": [ 2.0,  2.0,  2.0,  2.0],
    "indecisos_pct":     [12.0, 12.0, 12.0, 12.0],
    "instituto":         ["Datafolha"] * 4,
    "data":              [str(date.today())] * 4,
})


def _fmt_votes(n: float) -> str:
    """Format an integer vote count as 'X.XM' or 'X,XXX'."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    return f"{n:,.0f}"


def _build_result(tmp_path: str, n_sim: int) -> tuple[SimulationResult, object]:
    """Run the simulation pipeline and return (SimulationResult, PollData).

    Replicates the logic of ``src.cli._run_simulation`` without CLI overhead. Second-round wiring is pending Sprint 3 completion; ``df2`` is an empty DataFrame until ``simular_segundo_turno`` is delivered.

    Args:
        tmp_path: Path to the temporary CSV file written from the editor.
        n_sim:    Number of Monte Carlo iterations.

    Returns:
        Tuple of (SimulationResult, PollData).

    Raises:
        RuntimeError: If ``src.core.simulation`` is not yet available.
    """
    if simular_primeiro_turno is None:
        raise RuntimeError(
            "src.core.simulation not available. "
            "Ensure Sprint 2 deliverables are on the Python path."
        )

    config = SimulationConfig(
        csv_path=Path(tmp_path),
        n_sim=n_sim,
        seed=None,
        use_bayesian=False,
        election_date=_ELECTION_DATE,
    )
    poll_data = load_polls(config)
    first = simular_primeiro_turno(config, poll_data)

    pv: dict[str, float] = {
        cand: float((first.df["vencedor"] == cand).mean())
        for cand in first.candidatos_validos
    }
    p2t = float(first.df["tem_2turno"].mean())

    result = SimulationResult(
        df1=first.df,
        df2=pd.DataFrame(),
        pv=pv,
        p2v={},
        p2t=p2t,
        info_matchups={},
        info_lim_1t=first.info_lim_1t,
        info_indecisos=first.info_indecisos,
        margins=first.df["margem_1t"].to_numpy(),
        desvio_base=poll_data.desvio_base,
        config=config,
    )
    return result, poll_data


# ─── SIDEBAR: POLL INPUT ──────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚙️ Configuração")
    st.divider()

    upload = st.file_uploader(
        "Upload pesquisas.csv",
        type=["csv"],
        help="Formato v2.3+: candidato, intencao_voto_pct, rejeicao_pct, "
             "desvio_padrao_pct, indecisos_pct, instituto, data",
    )

    if upload is not None:
        try:
            df_input = pd.read_csv(upload)
            st.success(f"{len(df_input)} linhas carregadas")
        except Exception as e:
            st.error(f"Erro ao ler CSV: {e}")
            df_input = _DEFAULT_CSV.copy()
    else:
        df_input = _DEFAULT_CSV.copy()

    st.markdown("**Editar pesquisas**")
    df_edited = st.data_editor(
        df_input,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "intencao_voto_pct": st.column_config.NumberColumn(
                "Intenção (%)", min_value=0, max_value=100),
            "rejeicao_pct":      st.column_config.NumberColumn(
                "Rejeição (%)",  min_value=0, max_value=100),
            "desvio_padrao_pct": st.column_config.NumberColumn(
                "Desvio (%)",    min_value=0, max_value=20),
            "indecisos_pct":     st.column_config.NumberColumn(
                "Indecisos (%)", min_value=0, max_value=50),
        },
    )

    st.divider()
    n_sim = st.select_slider(
        "Simulações",
        options=[5_000, 10_000, 20_000, 40_000],
        value=40_000,
        help="Mais simulações = mais precisão, mais tempo de execução",
    )

    run_btn = st.button("▶ Rodar simulação", type="primary", use_container_width=True)

    st.divider()
    st.caption(
        "**brazil-election-montecarlo v3.0**  \n"
        "Monte Carlo · Dirichlet · PyMC  \n"
        "[GitHub](https://github.com/gabrielrv13/brazil-election-montecarlo)"
    )

# ─── HEADER ───────────────────────────────────────────────────────────────────

st.markdown("# 🗳️ Brazil 2026 — Previsão Eleitoral")
col_h1, col_h2, col_h3 = st.columns(3)
col_h1.metric("Eleitorado", f"{_ELEITORADO:,}")
col_h2.metric("Data da eleição", "04/10/2026")
dias = (_ELECTION_DATE - date.today()).days
col_h3.metric("Dias até a eleição", dias)

# ─── RUN SIMULATION ───────────────────────────────────────────────────────────

if run_btn:
    with st.spinner("Rodando simulação…"):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            df_edited.to_csv(f, index=False)
            tmp_path = f.name

        try:
            result, poll_data = _build_result(tmp_path, n_sim)

            # Persist to SQLite history.
            try:
                from src.io.history import init_db, salvar_historico  # noqa: PLC0415
                init_db(_DB_PATH)
                salvar_historico(result, _DB_PATH)
            except Exception as hist_exc:
                st.warning(f"Histórico não salvo: {hist_exc}")

            # Save CSV outputs and PDF.
            _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            save_csvs(result, output_dir=_OUTPUT_DIR)
            try:
                generate_pdf(result, output_dir=_OUTPUT_DIR)
            except Exception as pdf_exc:
                st.warning(f"PDF não gerado: {pdf_exc}")

            st.session_state.update({
                "result":            result,
                "poll_data":         poll_data,
                "candidatos_validos": list(result.pv.keys()),
                "ran":               True,
            })
            st.success("Simulação concluída!")

        except Exception as e:
            st.error(f"Erro na simulação: {e}")
            st.exception(e)

# ─── RESULTS ──────────────────────────────────────────────────────────────────

if st.session_state.get("ran"):
    result: SimulationResult = st.session_state["result"]
    poll_data                = st.session_state["poll_data"]
    df1                      = result.df1
    df2                      = result.df2
    pv                       = result.pv       # {cand: float in [0, 1]}
    p2v                      = result.p2v      # {cand: float in [0, 1]}
    candidatos_v: list[str]  = st.session_state["candidatos_validos"]

    palette = generate_palette(len(candidatos_v))

    # ── Key metrics ────────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### Resultados")

    if p2v:
        cols_metric = st.columns(len(p2v) + 1)
        for col_st, (cand, prob) in zip(cols_metric, p2v.items()):
            col_st.metric(f"🏆 {cand[:18]}", f"{prob * 100:.1f}%",
                          help="Vitória no 2º turno")
        cols_metric[-1].metric("Probabilidade de 2º turno", f"{result.p2t * 100:.1f}%")
    else:
        # Second round not yet wired — show 1st-round outright win probabilities.
        cols_metric = st.columns(len(pv) + 1)
        for col_st, (cand, prob) in zip(cols_metric, pv.items()):
            col_st.metric(f"{cand[:18]}", f"{prob * 100:.1f}%",
                          help="Vitória no 1º turno")
        cols_metric[-1].metric("Probabilidade de 2º turno", f"{result.p2t * 100:.1f}%")

    # ── Main visualization ─────────────────────────────────────────────────────
    fig_dash = plot_simulation_dashboard(
        df1=df1,
        df2=df2,
        candidates=candidatos_v,
        rejection=list(poll_data.rejeicao),
        palette=palette,
        n_sim=result.config.n_sim if result.config else n_sim,
        desvio=result.desvio_base,
        election_date=_ELECTION_DATE,
    )
    st.pyplot(fig_dash, use_container_width=True)
    import matplotlib.pyplot as plt  # noqa: PLC0415
    plt.close(fig_dash)

    # ── Tabs ───────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["1º Turno", "2º Turno", "Votos Absolutos", "Downloads", "Histórico"]
    )

    # ──────────────────────────────────────────────────────────────────────────
    with tab1:
        st.markdown("#### Intenção de voto — 1º turno (votos válidos, IC 90%)")
        rows = []
        for i, cand in enumerate(candidatos_v):
            col_v = f"{cand}_val"
            serie = df1[col_v] if col_v in df1.columns else df1.get(cand, pd.Series(dtype=float))
            rej = float(poll_data.rejeicao[poll_data.candidatos.index(cand)]) \
                if cand in poll_data.candidatos else 0.0
            rows.append({
                "Candidato":    cand,
                "Média (%)":    f"{serie.mean():.2f}",
                "IC 5%":        f"{serie.quantile(0.05):.2f}",
                "IC 95%":       f"{serie.quantile(0.95):.2f}",
                "Rejeição (%)": f"{rej:.1f}" if rej > 0 else "N/A",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        if "margem_1t" in df1.columns:
            st.markdown("#### Distribuição da margem — 1º turno")
            m = df1["margem_1t"]
            p50_m = m.quantile(0.50)
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Mediana da margem", f"{p50_m:.1f}pp")
            col_m2.metric("Corrida apertada (<3pp)", f"{(m < 3).mean() * 100:.1f}%")
            col_m3.metric("Confortável (>10pp)", f"{(m > 10).mean() * 100:.1f}%")

            thr_rows = [
                {
                    "Threshold":       f"> {thr}pp",
                    "P(margem > X)":   f"{(m > thr).mean() * 100:.1f}%",
                    "Polymarket":      "← mercado" if thr == 15 else "",
                }
                for thr in MARGIN_THRESHOLDS
            ]
            st.dataframe(pd.DataFrame(thr_rows), use_container_width=True, hide_index=True)

            fig_margin = plot_margin_histogram(result.margins, MARGIN_THRESHOLDS)
            st.pyplot(fig_margin, use_container_width=True)
            plt.close(fig_margin)

        pv_rows = [
            {"Candidato": c, "Prob. vitória no 1T (%)": f"{p * 100:.2f}"}
            for c, p in pv.items()
        ]
        st.markdown("**Probabilidade de vitória no 1º turno**")
        st.dataframe(pd.DataFrame(pv_rows), use_container_width=True, hide_index=True)

    # ──────────────────────────────────────────────────────────────────────────
    with tab2:
        st.markdown("#### Confrontos no 2º turno")
        if result.info_matchups:
            matchup_rows = []
            for mu, info in sorted(
                result.info_matchups.items(),
                key=lambda x: x[1]["prob_matchup"],
                reverse=True,
            ):
                matchup_rows.append({
                    "Confronto":             mu,
                    "% das simulações":      f"{info['prob_matchup']:.1f}%",
                    f"Vitória {info['cand_a'][:14]}": f"{info['prob_a']:.1f}%",
                    f"Vitória {info['cand_b'][:14]}": f"{info['prob_b']:.1f}%",
                })
            st.dataframe(pd.DataFrame(matchup_rows), use_container_width=True,
                         hide_index=True)

        if not df2.empty and "diferenca" in df2.columns:
            st.metric(
                "Corrida apertada (<3pp)",
                f"{(df2['diferenca'] < 3).mean() * 100:.1f}% dos cenários",
            )
            fig_m2, ax_m2 = plt.subplots(figsize=(8, 3), facecolor="#F7F7F7")
            ax_m2.set_facecolor("#F7F7F7")
            ax_m2.hist(df2["diferenca"], bins=60, color="#3498db",
                       alpha=0.75, edgecolor="none")
            ax_m2.axvline(3, color="#e74c3c", ls="--", lw=1.5,
                          label="Margem apertada (3pp)")
            ax_m2.set_xlabel("Margem de vitória (pp)", fontsize=9)
            ax_m2.set_ylabel("Frequência", fontsize=9)
            ax_m2.set_title("Distribuição da margem — 2º turno", fontsize=10,
                             fontweight="bold")
            ax_m2.legend(fontsize=8)
            for spine in ax_m2.spines.values():
                spine.set_visible(False)
            st.pyplot(fig_m2, use_container_width=True)
            plt.close(fig_m2)
        else:
            st.info("Simulação do 2º turno não disponível nesta versão. "
                    "Wiring completo previsto para Sprint 3.")

    # ──────────────────────────────────────────────────────────────────────────
    with tab3:
        st.markdown("#### Projeção de votos absolutos")
        st.caption(
            f"Eleitorado: {_ELEITORADO:,}  ·  "
            "Abstenção 1T: Normal(20%, σ=2%)  ·  Abstenção 2T: Normal(22%, σ=3%)"
        )

        if "votos_validos_1t" in df1.columns:
            st.markdown("**1º Turno**")
            rows_abs = []
            for cand in candidatos_v:
                col_abs = f"{cand}_abs"
                if col_abs in df1.columns:
                    p5_, p50_, p95_ = df1[col_abs].quantile([0.05, 0.50, 0.95])
                    rows_abs.append({
                        "Candidato":       cand,
                        "Mediana (votos)": _fmt_votes(p50_),
                        "IC 5%":           _fmt_votes(p5_),
                        "IC 95%":          _fmt_votes(p95_),
                    })
            st.dataframe(pd.DataFrame(rows_abs), use_container_width=True,
                         hide_index=True)
            abstencao_med = df1["abstencao_1t_pct"].median()
            turnout_med   = df1["votos_validos_1t"].median()
            st.metric("Comparecimento mediano", _fmt_votes(turnout_med),
                      f"Abstenção mediana: {abstencao_med:.1f}%")

        if not df2.empty and "margem_votos" in df2.columns:
            st.markdown("**2º Turno — distribuição da margem em votos**")
            p5m, p50m, p95m = df2["margem_votos"].quantile([0.05, 0.50, 0.95])
            col_a1, col_a2, col_a3 = st.columns(3)
            col_a1.metric("Margem mediana", _fmt_votes(p50m))
            col_a2.metric("IC 5%",  _fmt_votes(p5m))
            col_a3.metric("IC 95%", _fmt_votes(p95m))

            fig_abs, ax_abs = plt.subplots(figsize=(8, 3), facecolor="#F7F7F7")
            ax_abs.set_facecolor("#F7F7F7")
            margem_m = df2["margem_votos"] / 1_000_000
            ax_abs.hist(margem_m, bins=60, color="#2ecc71", alpha=0.75,
                        edgecolor="none")
            ax_abs.axvline(margem_m.median(), color="#1a8a4a", lw=2, ls="--",
                           label=f"Mediana {margem_m.median():.2f}M")
            ax_abs.set_xlabel("Margem (milhões de votos)", fontsize=9)
            ax_abs.set_ylabel("Frequência", fontsize=9)
            ax_abs.set_title("Distribuição da margem absoluta — 2º turno",
                             fontsize=10, fontweight="bold")
            ax_abs.legend(fontsize=8)
            for spine in ax_abs.spines.values():
                spine.set_visible(False)
            st.pyplot(fig_abs, use_container_width=True)
            plt.close(fig_abs)

    # ──────────────────────────────────────────────────────────────────────────
    with tab4:
        st.markdown("#### Arquivos gerados")
        _downloads = [
            (_OUTPUT_DIR / "resultados_1turno.csv",         "resultados_1turno.csv",         "text/csv"),
            (_OUTPUT_DIR / "resultados_2turno.csv",         "resultados_2turno.csv",         "text/csv"),
            (_OUTPUT_DIR / "simulacao_brasil_2026.png",     "simulacao_brasil_2026.png",     "image/png"),
            (_OUTPUT_DIR / "relatorio_eleicoes_brasil_2026.pdf",
             "relatorio_eleicoes_brasil_2026.pdf", "application/pdf"),
        ]
        for fpath, fname, mime in _downloads:
            if fpath.exists():
                with open(fpath, "rb") as f:
                    st.download_button(f"⬇ {fname}", f, file_name=fname, mime=mime)

    # ──────────────────────────────────────────────────────────────────────────
    with tab5:
        st.markdown("#### Evolução da previsão")

        _hist_days = st.slider(
            "Janela de histórico (dias)",
            min_value=7, max_value=365, value=90, step=7,
        )
        _use_p2v = st.toggle(
            "Exibir probabilidade do 2º turno (p2v)",
            value=True,
            help="Desative para exibir probabilidade de vitória no 1º turno (pv).",
        )

        try:
            from src.io.history import carregar_historico  # noqa: PLC0415
            df_hist = carregar_historico(_DB_PATH, days=_hist_days)

            if df_hist.empty:
                st.info(
                    "Nenhum histórico nos últimos "
                    f"{_hist_days} dias. Rode a simulação para começar a rastrear."
                )
            else:
                fig_hist = plot_forecast_history(
                    df_hist,
                    use_p2v=_use_p2v,
                    election_date=_ELECTION_DATE,
                )
                st.pyplot(fig_hist, use_container_width=True)
                plt.close(fig_hist)

                st.markdown("**Simulações recentes**")
                display_cols = ["run_at", "n_sim", "p2t", "desvio_base",
                                "margins_p50", "margins_p5", "margins_p95"]
                display_cols = [c for c in display_cols if c in df_hist.columns]
                df_display = df_hist[display_cols].copy()
                df_display["p2t"] = (df_display["p2t"] * 100).map("{:.1f}%".format)
                if "desvio_base" in df_display.columns:
                    df_display["desvio_base"] = df_display["desvio_base"].map(
                        "{:.2f}pp".format
                    )
                st.dataframe(df_display, use_container_width=True, hide_index=True)

        except FileNotFoundError:
            st.info(
                "Banco de dados de histórico ainda não criado. "
                "Execute ao menos uma simulação para inicializar."
            )
        except Exception as hist_exc:
            st.error(f"Erro ao carregar histórico: {hist_exc}")

    # ── Polymarket Edge Calculator ─────────────────────────────────────────────
    if "margem_1t" in df1.columns and polymarket_edge is not None:
        with st.expander("Polymarket Edge Calculator"):
            st.caption(
                "Calcula o edge entre o modelo e a probabilidade implícita do Polymarket "
                "para mercados de margem do 1º turno. Use half-Kelly com cautela — "
                "backtesting (v2.9): RMSE ~3.4pp, shy Bolsonaro ~4pp."
            )
            col_p1, col_p2, col_p3 = st.columns(3)
            pm_threshold = col_p1.number_input(
                "Threshold (pp)", min_value=1.0, max_value=40.0,
                value=15.0, step=1.0,
            )
            pm_market = col_p2.number_input(
                "Probabilidade Polymarket (0–1)", min_value=0.01, max_value=0.99,
                value=0.50, step=0.01,
            )
            cand_options = ["(margem absoluta)"] + list(candidatos_v)
            pm_cand = col_p3.selectbox("Candidato (opcional)", cand_options)

            if st.button("Calcular edge", key="pm_edge_btn"):
                cand_arg = None if pm_cand == "(margem absoluta)" else pm_cand
                edge_result = polymarket_edge(df1, pm_threshold, pm_market, cand_arg)
                col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                col_r1.metric("P(modelo)", f"{edge_result['model_prob']:.1%}")
                col_r2.metric("P(Polymarket)", f"{edge_result['market_prob']:.1%}")
                edge_val = edge_result["edge"]
                col_r3.metric(
                    "Edge",
                    f"{edge_val:+.1%}",
                    delta_color="normal" if edge_val > 0 else "inverse",
                )
                col_r4.metric("Half-Kelly", f"{edge_result['kelly_fraction']:.2%}")
                if edge_val <= 0:
                    st.warning("Edge negativo — modelo favorece o lado contrário.")
                elif edge_result["model_prob"] < 0.05:
                    st.info(
                        "model_prob < 5%. Recomenda-se reexecutar com N_SIM=200.000 "
                        "para reduzir ruído amostral (janela Jun–Ago 2026)."
                    )

else:
    st.info("Configure os dados na barra lateral e clique em **▶ Rodar simulação**.")