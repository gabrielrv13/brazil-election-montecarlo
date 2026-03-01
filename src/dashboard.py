"""
brazil-election-montecarlo — Interactive Dashboard (v2.6)
==========================================================
Streamlit web application for running and visualizing the election simulation.

Usage:
    streamlit run src/dashboard.py

Requirements:
    pip install streamlit

The dashboard calls simulation_v2.inicializar() explicitly, so importing the
simulation module does NOT trigger CSV loading or console output on its own.
"""

import sys
import io
import tempfile
from pathlib import Path
from datetime import date

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# Allow running from project root or from src/
sys.path.insert(0, str(Path(__file__).parent))
import simulation_v2 as sim

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Brazil 2026 — Election Forecast",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── HELPERS ──────────────────────────────────────────────────────────────────

DEFAULT_CSV = pd.DataFrame({
    'candidato':         ['Lula', 'Flávio Bolsonaro', 'Outros', 'Brancos/Nulos'],
    'intencao_voto_pct': [35.0, 29.0, 21.0, 15.0],
    'rejeicao_pct':      [42.0, 48.0,  0.0,  0.0],
    'desvio_padrao_pct': [ 2.0,  2.0,  2.0,  2.0],
    'indecisos_pct':     [12.0, 12.0, 12.0, 12.0],
    'instituto':         ['Datafolha'] * 4,
    'data':              [str(date.today())] * 4,
})


def _fmt_votes(n: float) -> str:
    """Formats an integer vote count as 'X.XM' or 'X,XXX'."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    return f"{n:,.0f}"


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
            df_input = DEFAULT_CSV.copy()
    else:
        df_input = DEFAULT_CSV.copy()

    st.markdown("**Editar pesquisas**")
    df_edited = st.data_editor(
        df_input,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            'intencao_voto_pct': st.column_config.NumberColumn("Intenção (%)", min_value=0, max_value=100),
            'rejeicao_pct':      st.column_config.NumberColumn("Rejeição (%)",  min_value=0, max_value=100),
            'desvio_padrao_pct': st.column_config.NumberColumn("Desvio (%)",    min_value=0, max_value=20),
            'indecisos_pct':     st.column_config.NumberColumn("Indecisos (%)", min_value=0, max_value=50),
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
        "**brazil-election-montecarlo v2.6**  \n"
        "Monte Carlo · Dirichlet · PyMC  \n"
        "[GitHub](https://github.com/gabrielrv13/brazil-election-montecarlo)"
    )


# ─── HEADER ───────────────────────────────────────────────────────────────────

st.markdown("# 🗳️ Brazil 2026 — Previsão Eleitoral")
col_h1, col_h2, col_h3 = st.columns(3)
col_h1.metric("Eleitorado", f"{sim.ELEITORADO:,}")
col_h2.metric("Data da eleição", "04/10/2026")
dias = (date(2026, 10, 4) - date.today()).days
col_h3.metric("Dias até a eleição", dias)


# ─── RUN SIMULATION ───────────────────────────────────────────────────────────

if run_btn:
    with st.spinner("Inicializando e rodando simulação…"):
        # Save edited dataframe to a temp CSV so carregar_pesquisas() can read it
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False,
                                         encoding='utf-8') as f:
            df_edited.to_csv(f, index=False)
            tmp_path = f.name

        try:
            sim.inicializar(csv_path=tmp_path)
            sim.N_SIM = n_sim

            trace = sim.construir_modelo()
            df1, info_lim_1t, info_indecisos, validos_final, candidatos_validos = (
                sim.simular_primeiro_turno()
            )
            df2, info_matchups = sim.simular_segundo_turno(validos_final, candidatos_validos)
            pv, p2v, p2t = sim.relatorio(df1, df2, info_lim_1t, info_matchups, info_indecisos)

            # Generate visualization and PDF
            sim.graficos(df1, df2, trace, pv, p2v, p2t,
                         info_lim_1t, info_matchups, info_indecisos)
            pdf_path = sim.gerar_relatorio_pdf(
                df1, df2, pv, p2v, p2t, info_matchups, info_indecisos
            )

            st.session_state.update({
                'df1': df1, 'df2': df2, 'pv': pv, 'p2v': p2v, 'p2t': p2t,
                'info_matchups': info_matchups, 'info_indecisos': info_indecisos,
                'candidatos_validos': candidatos_validos,
                'pdf_path': str(pdf_path),
                'ran': True,
            })
            st.success("Simulação concluída!")

        except Exception as e:
            st.error(f"Erro na simulação: {e}")
            st.exception(e)


# ─── RESULTS ──────────────────────────────────────────────────────────────────

if st.session_state.get('ran'):
    df1           = st.session_state['df1']
    df2           = st.session_state['df2']
    pv            = st.session_state['pv']
    p2v           = st.session_state['p2v']
    p2t           = st.session_state['p2t']
    info_matchups = st.session_state['info_matchups']
    candidatos_v  = st.session_state['candidatos_validos']

    # ── Key metrics ────────────────────────────────────────────────────────────
    st.divider()
    st.markdown("### Resultados")

    cols_metric = st.columns(len(p2v) + 1)
    for col, (cand, prob) in zip(cols_metric, p2v.items()):
        col.metric(f"🏆 {cand[:18]}", f"{prob:.1f}%", help="Vitória no 2º turno")
    cols_metric[-1].metric("Probabilidade de 2º turno", f"{p2t:.1f}%")

    # ── Main visualization ─────────────────────────────────────────────────────
    img_path = sim.OUTPUT_DIR / "simulacao_eleicoes_brasil_2026_v2.5.png"
    if img_path.exists():
        st.image(str(img_path), use_column_width=True)

    # ── Tabs: First round / Second round / Absolute votes / Downloads ──────────
    tab1, tab2, tab3, tab4 = st.tabs(
        ["1º Turno", "2º Turno", "Votos Absolutos", "Downloads"]
    )

    with tab1:
        st.markdown("#### Intenção de voto — 1º turno (votos válidos, IC 90%)")
        rows = []
        for cand in candidatos_v:
            col_v = f"{cand}_val"
            serie = df1[col_v] if col_v in df1.columns else df1[cand]
            rows.append({
                "Candidato": cand,
                "Média (%)": f"{serie.mean():.2f}",
                "IC 5%": f"{serie.quantile(0.05):.2f}",
                "IC 95%": f"{serie.quantile(0.95):.2f}",
                "Rejeição (%)": f"{sim.REJEICAO[sim.CANDIDATOS.index(cand)]:.1f}"
                                if sim.REJEICAO[sim.CANDIDATOS.index(cand)] > 0 else "N/A",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        pv_str = pv.reset_index()
        pv_str.columns = ["Candidato", "Prob. vitória no 1T (%)"]
        pv_str["Prob. vitória no 1T (%)"] = pv_str["Prob. vitória no 1T (%)"].map("{:.2f}".format)
        st.markdown("**Probabilidade de vitória no 1º turno**")
        st.dataframe(pv_str, use_container_width=True, hide_index=True)

    with tab2:
        st.markdown("#### Confrontos no 2º turno")
        if info_matchups:
            matchup_rows = []
            for mu, info in sorted(info_matchups.items(),
                                   key=lambda x: x[1]['prob_matchup'], reverse=True):
                matchup_rows.append({
                    "Confronto": mu,
                    "% das simulações": f"{info['prob_matchup']:.1f}%",
                    f"Vitória {info['cand_a'][:14]}": f"{info['prob_a']:.1f}%",
                    f"Vitória {info['cand_b'][:14]}": f"{info['prob_b']:.1f}%",
                })
            st.dataframe(pd.DataFrame(matchup_rows), use_container_width=True, hide_index=True)

        if not df2.empty:
            st.metric(
                "Corrida apertada (<3pp)",
                f"{(df2['diferenca'] < 3).mean() * 100:.1f}% dos cenários",
            )

            # Margin distribution chart
            fig_m, ax_m = plt.subplots(figsize=(8, 3), facecolor='#F7F7F7')
            ax_m.set_facecolor('#F7F7F7')
            ax_m.hist(df2['diferenca'], bins=60, color='#3498db', alpha=0.75, edgecolor='none')
            ax_m.axvline(3, color='#e74c3c', ls='--', lw=1.5, label='Margem apertada (3pp)')
            ax_m.set_xlabel("Margem de vitória (pp)", fontsize=9)
            ax_m.set_ylabel("Frequência", fontsize=9)
            ax_m.set_title("Distribuição da margem — 2º turno", fontsize=10, fontweight='bold')
            ax_m.legend(fontsize=8)
            for spine in ax_m.spines.values():
                spine.set_visible(False)
            st.pyplot(fig_m, use_container_width=True)
            plt.close(fig_m)

    with tab3:
        st.markdown("#### Projeção de votos absolutos")
        st.caption(f"Eleitorado: {sim.ELEITORADO:,} · Abstenção 1T: Normal(20%, σ=2%) · Abstenção 2T: Normal(22%, σ=3%)")

        if 'votos_validos_1t' in df1.columns:
            st.markdown("**1º Turno**")
            rows_abs = []
            for cand in candidatos_v:
                col_abs = f"{cand}_abs"
                if col_abs in df1.columns:
                    p5, p50, p95 = df1[col_abs].quantile([0.05, 0.50, 0.95])
                    rows_abs.append({
                        "Candidato": cand,
                        "Mediana (votos)": _fmt_votes(p50),
                        "IC 5%": _fmt_votes(p5),
                        "IC 95%": _fmt_votes(p95),
                    })
            st.dataframe(pd.DataFrame(rows_abs), use_container_width=True, hide_index=True)
            abstencao_med = df1['abstencao_1t_pct'].median()
            turnout_med   = df1['votos_validos_1t'].median()
            st.metric("Comparecimento mediano", _fmt_votes(turnout_med),
                      f"Abstenção mediana: {abstencao_med:.1f}%")

        if not df2.empty and 'margem_votos' in df2.columns:
            st.markdown("**2º Turno — distribuição da margem em votos**")
            p5m, p50m, p95m = df2['margem_votos'].quantile([0.05, 0.50, 0.95])
            col_a1, col_a2, col_a3 = st.columns(3)
            col_a1.metric("Margem mediana", _fmt_votes(p50m))
            col_a2.metric("IC 5%",  _fmt_votes(p5m))
            col_a3.metric("IC 95%", _fmt_votes(p95m))

            fig_abs, ax_abs = plt.subplots(figsize=(8, 3), facecolor='#F7F7F7')
            ax_abs.set_facecolor('#F7F7F7')
            margem_m = df2['margem_votos'] / 1_000_000
            ax_abs.hist(margem_m, bins=60, color='#2ecc71', alpha=0.75, edgecolor='none')
            ax_abs.axvline(margem_m.median(), color='#1a8a4a', lw=2, ls='--',
                           label=f"Mediana {margem_m.median():.2f}M")
            ax_abs.set_xlabel("Margem (milhões de votos)", fontsize=9)
            ax_abs.set_ylabel("Frequência", fontsize=9)
            ax_abs.set_title("Distribuição da margem absoluta — 2º turno", fontsize=10, fontweight='bold')
            ax_abs.legend(fontsize=8)
            for spine in ax_abs.spines.values():
                spine.set_visible(False)
            st.pyplot(fig_abs, use_container_width=True)
            plt.close(fig_abs)

    with tab4:
        st.markdown("#### Arquivos gerados")

        # CSV 1T
        csv_1t_path = sim.OUTPUT_DIR / "resultados_1turno_v2.6.csv"
        if csv_1t_path.exists():
            with open(csv_1t_path, 'rb') as f:
                st.download_button(
                    "⬇ resultados_1turno_v2.6.csv",
                    f, file_name="resultados_1turno_v2.6.csv", mime="text/csv",
                )

        # CSV 2T
        csv_2t_path = sim.OUTPUT_DIR / "resultados_2turno_v2.6.csv"
        if csv_2t_path.exists():
            with open(csv_2t_path, 'rb') as f:
                st.download_button(
                    "⬇ resultados_2turno_v2.6.csv",
                    f, file_name="resultados_2turno_v2.6.csv", mime="text/csv",
                )

        # PNG
        img_out = sim.OUTPUT_DIR / "simulacao_eleicoes_brasil_2026_v2.5.png"
        if img_out.exists():
            with open(img_out, 'rb') as f:
                st.download_button(
                    "⬇ Visualização principal (PNG)",
                    f, file_name="simulacao_eleicoes_brasil_2026.png", mime="image/png",
                )

        # PDF
        pdf_out = sim.OUTPUT_DIR / "relatorio_eleicoes_brasil_2026.pdf"
        if pdf_out.exists():
            with open(pdf_out, 'rb') as f:
                st.download_button(
                    "⬇ Relatório completo (PDF)",
                    f, file_name="relatorio_eleicoes_brasil_2026.pdf",
                    mime="application/pdf",
                )

else:
    st.info("Configure os dados na barra lateral e clique em **▶ Rodar simulação**.")
