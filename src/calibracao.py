"""
Phase 3 — evaluation and calibration of the election-level polling error.

Two jobs:

1. **Score the 2026 forecasts** (first round as of 2026-10-03, runoff as of
   2026-10-24) against the official TSE results with proper scoring rules
   (``src.core.scoring``).
2. **Estimate ``sd_erro_comum_pp``** — the polling error shared by every poll
   of one election — from the final-week polling averages of every election
   with usable data, with an honest uncertainty interval and leave-one-out
   checks.

The calibration works on the **two-party share** of the two leading
candidates, ``A / (A + B)``: it needs only their numbers, is comparable
between first rounds and runoffs, and is exactly the quantity that decides
the leader and the runoff winner. Under the engine's election-level shift
``mu ~ Dirichlet(p * A)`` that share is ``Beta(p_A * A, p_B * A)``, so its
sd is ``100 * sqrt(q (1 - q) / (s * A + 1))`` with ``q`` the share, ``s``
the top-two share of valid votes and ``A = 2500 / sd^2 - 1``.

Usage::

    python -m src.calibracao                     # writes outputs/calibracao/
    python -m src.calibracao --saida outra/pasta

Cases: both rounds of 2010-2022 from the Wikipedia transcription in
``data/wikipedia`` (a secondary source, see its README) plus both 2026
rounds from the project's own poll files. Each case aggregates the polls of
the last 14 days before election day with the engine's v3 aggregator (house
effects, recency weights). The legacy ``data/historico`` transcriptions of
2018/2022 are kept only for comparison. The audited catalogue in
``data/historico_v2`` has no eligible snapshot yet.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import date
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from src.core import scoring

ROOT = Path(__file__).resolve().parent.parent

# ─── Official results (% of valid votes, TSE) ────────────────────────────────

RESULTADOS_OFICIAIS: dict[tuple[str, str], dict[str, float]] = {
    ("2010", "1T"): {"Dilma": 46.91, "Serra": 32.61, "Marina": 19.33},
    ("2010", "2T"): {"Dilma": 56.05, "Serra": 43.95},
    ("2014", "1T"): {"Dilma": 41.59, "Aécio": 33.55, "Marina": 21.32},
    ("2014", "2T"): {"Dilma": 51.64, "Aécio": 48.36},
    ("2018", "1T"): {"Bolsonaro": 46.03, "Haddad": 29.28},
    ("2018", "2T"): {"Bolsonaro": 55.13, "Haddad": 44.87},
    ("2022", "1T"): {"Lula": 48.43, "Bolsonaro": 43.20},
    ("2022", "2T"): {"Lula": 50.90, "Bolsonaro": 49.10},
    ("2026", "1T"): {
        "F. Bolsonaro": 47.03, "Lula": 45.16, "Cury": 2.89, "Santos": 2.24,
        "Caiado": 2.18, "Zema": 0.27, "Outros": 0.23,
    },
    ("2026", "2T"): {"Flávio Bolsonaro": 48.21, "Lula": 51.79},
}
FONTES_RESULTADOS = {
    "2010/2014": "https://www.tse.jus.br/eleicoes/estatisticas (official totals, valid votes)",
    "2018/2022":"https://resultados.tse.jus.br (values already in src/backtesting.py GROUND_TRUTH)",
    "2026 1T": "https://www.cartacapital.com.br/politica/tse-encerra-apuracao-do-1o-turno/",
    "2026 2T": ("https://www.tse.jus.br/comunicacao/noticias/2026/Outubro/"
                "presidente-do-tse-anuncia-reeleicao-de-lula-e-faz-balanco-do-2o-turno-das-eleicoes-2026"),
}


# ─── Calibration cases ───────────────────────────────────────────────────────

@dataclass
class Caso:
    """Final-week polling average versus result, on the two-party share."""

    eleicao: str
    turno: str
    cand_a: str            # candidate whose share is tracked (right-wing lead)
    cand_b: str
    fatia_pesquisas: float  # A / (A + B) of the polling average, pp
    fatia_real: float       # A / (A + B) of the official result, pp
    s_top2: float           # top-two share of the polled candidates (0-1)
    sd_media: float         # sd of the polling average, pp
    dias: int               # days from as-of to election day
    as_of: str
    n_pesquisas: int
    ressalva: str

    @property
    def erro(self) -> float:
        """Signed error, result minus polls (positive: A under-polled)."""
        return self.fatia_real - self.fatia_pesquisas


def _caso_primeiro_turno(
    eleicao: str, csv: Path, a: str, b: str, as_of: date, dia_eleicao: date,
    aliases: dict[str, str] | None, ressalva: str,
) -> Caso:
    from src.core.aggregation import agregar_pesquisas, sd_referencia_50
    from src.core.poll_quality import validate_dates

    df = pd.read_csv(csv)
    if aliases:
        df["candidato"] = df["candidato"].replace(aliases)
    df = validate_dates(df, as_of, str(csv))
    ag = agregar_pesquisas(df, as_of)
    total = sum(x.voto for x in ag.values())
    va, vb = ag[a].voto, ag[b].voto
    real = RESULTADOS_OFICIAIS[(eleicao, "1T")]
    return Caso(
        eleicao=eleicao, turno="1T", cand_a=a, cand_b=b,
        fatia_pesquisas=100 * va / (va + vb),
        fatia_real=100 * real[a] / (real[a] + real[b]),
        s_top2=(va + vb) / total, sd_media=sd_referencia_50(ag),
        dias=(dia_eleicao - as_of).days, as_of=as_of.isoformat(),
        n_pesquisas=int(ag[a].info["n_pesquisas"]), ressalva=ressalva,
    )


def _caso_segundo_turno_2026(csv: Path, as_of: date) -> Caso:
    from src.core.aggregation import Z_MARGEM_ERRO
    from src.simulation_2turno import agregar_fatia_dois_candidatos

    df = pd.read_csv(csv)
    df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.date
    cand_a, cand_b, fatia_a, info = agregar_fatia_dois_candidatos(df, as_of)
    a = "Flávio Bolsonaro"
    fatia = fatia_a if cand_a == a else 100.0 - fatia_a
    se = float(df["desvio_padrao_pct"].median()) / Z_MARGEM_ERRO
    real = RESULTADOS_OFICIAIS[("2026", "2T")]
    return Caso(
        eleicao="2026", turno="2T", cand_a=a, cand_b="Lula",
        fatia_pesquisas=fatia, fatia_real=real[a],
        s_top2=1.0, sd_media=se / math.sqrt(info["n_efetivo"]),
        dias=(date(2026, 10, 25) - as_of).days, as_of=as_of.isoformat(),
        n_pesquisas=int(info["n_pesquisas"]),
        ressalva="Post-first-round polls only (pesquisas_only_2turno.csv).",
    )


# (year, round, tracked candidate A, B, name substrings, election day, first-round day)
# A is the main non-PT candidate, so a positive error means A was under-polled.
ELEICOES_WIKIPEDIA = (
    ("2010", "1T", "Serra", "Dilma", {"Serra": "Serra", "Dilma": "Dilma"},
     date(2010, 10, 3), None),
    ("2010", "2T", "Serra", "Dilma", {"Serra": "Serra", "Dilma": "Dilma"},
     date(2010, 10, 31), date(2010, 10, 3)),
    ("2014", "1T", "Aécio", "Dilma", {"Aécio": "Aécio", "Dilma": "Dilma"},
     date(2014, 10, 5), None),
    ("2014", "2T", "Aécio", "Dilma", {"Aécio": "Aécio", "Dilma": "Dilma"},
     date(2014, 10, 26), date(2014, 10, 5)),
    ("2018", "1T", "Bolsonaro", "Haddad", {"Bolsonaro": "Bolsonaro", "Haddad": "Haddad"},
     date(2018, 10, 7), None),
    ("2018", "2T", "Bolsonaro", "Haddad", {"Bolsonaro": "Bolsonaro", "Haddad": "Haddad"},
     date(2018, 10, 28), date(2018, 10, 7)),
    ("2022", "1T", "Bolsonaro", "Lula", {"Bolsonaro": "Bolsonaro", "Lula": "Lula"},
     date(2022, 10, 2), None),
    ("2022", "2T", "Bolsonaro", "Lula", {"Bolsonaro": "Bolsonaro", "Lula": "Lula"},
     date(2022, 10, 30), date(2022, 10, 2)),
)
JANELA_DIAS = 14


def _caso_wikipedia(
    df: pd.DataFrame, eleicao: str, turno: str, a: str, b: str, nomes: dict[str, str],
    dia_eleicao: date, dia_1t: date | None, janela: int = JANELA_DIAS,
) -> Caso:
    """One final-window case from the Wikipedia transcription (core v3 aggregator)."""
    from datetime import timedelta

    from src.core.aggregation import agregar_pesquisas, sd_referencia_50
    from src.core.runoff import agregar_fatia
    from src.io.wikipedia import pesquisas_reta_final

    as_of = dia_eleicao - timedelta(days=1)
    inicio = as_of - timedelta(days=janela - 1)
    if dia_1t is not None:
        inicio = max(inicio, dia_1t + timedelta(days=1))
    rows = pesquisas_reta_final(df, eleicao, turno[0], nomes, inicio, as_of,
                                so_dois=turno == "2T")
    real = RESULTADOS_OFICIAIS[(eleicao, turno)]
    if turno == "1T":
        ag = agregar_pesquisas(rows, as_of)
        va, vb = ag[a].voto, ag[b].voto
        fatia, s_top2 = 100 * va / (va + vb), (va + vb) / sum(x.voto for x in ag.values())
        sd_media, n = sd_referencia_50(ag), int(ag[a].info["n_pesquisas"])
    else:
        ag2 = agregar_fatia(rows, as_of)
        fatia = ag2.fatia_a if ag2.cand_a == a else 100.0 - ag2.fatia_a
        s_top2, sd_media, n = 1.0, ag2.sd_media, int(ag2.info["n_pesquisas"])
    return Caso(
        eleicao=eleicao, turno=turno, cand_a=a, cand_b=b,
        fatia_pesquisas=fatia, fatia_real=100 * real[a] / (real[a] + real[b]),
        s_top2=s_top2, sd_media=sd_media, dias=(dia_eleicao - as_of).days,
        as_of=as_of.isoformat(), n_pesquisas=n,
        ressalva=(f"Wikipedia transcription (data/wikipedia), polls ending "
                  f"{inicio.isoformat()}..{as_of.isoformat()}; secondary source."),
    )


def casos_wikipedia(caminho: Path | None = None) -> list[Caso]:
    """Both rounds of 2010-2022 from the Wikipedia transcription."""
    from src.io.wikipedia import ARQUIVO_WIKIPEDIA, carregar_wikipedia

    df = carregar_wikipedia(caminho or ARQUIVO_WIKIPEDIA)
    return [_caso_wikipedia(df, *e) for e in ELEICOES_WIKIPEDIA]


def casos_legado(raiz: Path = ROOT) -> list[Caso]:
    """The legacy 2018/2022 first-round transcriptions, kept for comparison only."""
    legado = ("Legacy final-week transcription (data/historico, file named "
              "T-7 but dated in the last days); provenance not documented.")
    return [
        _caso_primeiro_turno(
            "2018", raiz / "data/historico/2018_1t_T-7.csv", "Bolsonaro", "Haddad",
            date(2018, 10, 6), date(2018, 10, 7),
            {"Jair Bolsonaro": "Bolsonaro", "Fernando Haddad": "Haddad"}, legado),
        _caso_primeiro_turno(
            "2022", raiz / "data/historico/2022_1t_T-7.csv", "Bolsonaro", "Lula",
            date(2022, 10, 1), date(2022, 10, 2), {"Jair Bolsonaro": "Bolsonaro"}, legado),
    ]


def casos_calibracao(raiz: Path = ROOT) -> list[Caso]:
    """Every final-week case: 2010-2022 (Wikipedia) and 2026 (project data), in order."""
    return [
        *casos_wikipedia(raiz / "data/wikipedia/pesquisas_wikipedia_2010_2022.csv"),
        _caso_primeiro_turno(
            "2026", raiz / "data/pesquisas.csv", "F. Bolsonaro", "Lula",
            date(2026, 10, 3), date(2026, 10, 4), None,
            "Project poll base, validated dates."),
        _caso_segundo_turno_2026(raiz / "data/pesquisas_only_2turno.csv", date(2026, 10, 24)),
    ]


# ─── Model-implied predictive distribution of the error ──────────────────────

def sd_erro_modelo(caso: Caso, sd_comum: float, sd_deriva_30d: float = 2.0) -> float:
    """sd (pp) of the two-party-share error implied by the engine for a case."""
    deriva = sd_deriva_30d * math.sqrt(max(caso.dias, 0) / 30.0)
    sd_shift = math.hypot(sd_comum, deriva)
    q = caso.fatia_pesquisas / 100.0
    if sd_shift > 0:
        a_conc = 2500.0 / sd_shift**2 - 1.0
        var_shift = 1e4 * q * (1 - q) / (caso.s_top2 * a_conc + 1.0)
    else:
        var_shift = 0.0
    return math.sqrt(var_shift + caso.sd_media**2)


def _logpdf(erro: float, sd: float, gl: float) -> float:
    """Log density of a zero-mean normal or unit-variance-scaled t with sd ``sd``.

    Closed form instead of ``scipy.stats`` (called ~10^5 times by the grid
    search and the leave-one-out loop; scipy's per-call overhead dominated).
    """
    if math.isinf(gl):
        return -0.5 * math.log(2 * math.pi) - math.log(sd) - 0.5 * (erro / sd) ** 2
    escala = sd * math.sqrt((gl - 2.0) / gl)
    z = erro / escala
    return (math.lgamma((gl + 1) / 2) - math.lgamma(gl / 2) - 0.5 * math.log(gl * math.pi)
            - math.log(escala) - (gl + 1) / 2 * math.log1p(z * z / gl))


def _cdf(erro: float, sd: float, gl: float) -> float:
    if math.isinf(gl):
        return float(stats.norm.cdf(erro, scale=sd))
    return float(stats.t.cdf(erro, gl, scale=sd * math.sqrt((gl - 2.0) / gl)))


def log_verossimilhanca(casos: list[Caso], sd_comum: float, gl: float = 5.0,
                        sd_deriva_30d: float = 2.0) -> float:
    return sum(_logpdf(c.erro, sd_erro_modelo(c, sd_comum, sd_deriva_30d), gl) for c in casos)


def estimar_sd_comum(
    casos: list[Caso], gl: float = 5.0, sd_deriva_30d: float = 2.0,
    grade: np.ndarray | None = None,
) -> dict:
    """Maximum-likelihood ``sd_erro_comum_pp`` with a profile 95% interval.

    The interval is ``{sd : 2 (l_max - l(sd)) <= 3.84}`` on a grid; with a
    handful of cases it is wide and that width is the main result.
    """
    grade = np.arange(0.05, 12.0001, 0.01) if grade is None else grade
    ll = np.array([log_verossimilhanca(casos, s, gl, sd_deriva_30d) for s in grade])
    i = int(np.argmax(ll))
    dentro = grade[2 * (ll[i] - ll) <= stats.chi2.ppf(0.95, 1)]
    return {
        "sd_mle": float(grade[i]),
        "ic95": [float(dentro.min()), float(dentro.max())],
        "ic95_aberto_acima": bool(dentro.max() >= grade[-1] - 1e-9),
        "n_casos": len(casos),
        "gl": gl,
    }


def validacao_loo(casos: list[Caso], gl: float = 5.0, sd_padrao: float = 3.0) -> list[dict]:
    """Leave-one-out: fit on the other cases, score the held-out one."""
    out = []
    for k, caso in enumerate(casos):
        resto = casos[:k] + casos[k + 1:]
        sd_k = estimar_sd_comum(resto, gl)["sd_mle"]
        linha = {"caso": f"{caso.eleicao} {caso.turno}", "erro": caso.erro, "sd_ajustado_sem_caso": sd_k}
        for nome, sd in (("loo", sd_k), ("padrao", sd_padrao)):
            sd_tot = sd_erro_modelo(caso, sd)
            linha[f"pit_{nome}"] = _cdf(caso.erro, sd_tot, gl)
            linha[f"log_score_{nome}"] = -_logpdf(caso.erro, sd_tot, gl)
        out.append(linha)
    return out


def vies_direcional(casos: list[Caso]) -> dict:
    """Mean signed error of the right-wing lead candidate, with a t interval."""
    e = np.array([c.erro for c in casos])
    n = e.size
    se = e.std(ddof=1) / math.sqrt(n)
    tcrit = stats.t.ppf(0.975, n - 1)
    return {
        "media_pp": float(e.mean()),
        "ic95_pp": [float(e.mean() - tcrit * se), float(e.mean() + tcrit * se)],
        "erros_pp": {f"{c.eleicao} {c.turno}": float(c.erro) for c in casos},
        "so_primeiros_turnos_pp": (
            float(np.mean(primeiros)) if (primeiros := [c.erro for c in casos if c.turno == "1T"])
            else None
        ),
        "so_segundos_turnos_pp": (
            float(np.mean(segundos)) if (segundos := [c.erro for c in casos if c.turno == "2T"])
            else None
        ),
    }


# ─── Scoring the 2026 forecasts ──────────────────────────────────────────────

def pontuar_primeiro_turno_2026(n_sim: int = 100_000, seed: int = 2026, **config_kw) -> dict:
    """Score the engine's first-round forecast as of 2026-10-03."""
    from src.core.config import SimulationConfig
    from src.core.simulation import simular_primeiro_turno
    from src.io.loader import load_polls

    cfg = SimulationConfig(csv_path=ROOT / "data/pesquisas.csv", n_sim=n_sim, seed=seed,
                           as_of=date(2026, 10, 3), **config_kw)
    res = simular_primeiro_turno(cfg, load_polls(cfg))
    df = res.df
    real = RESULTADOS_OFICIAIS[("2026", "1T")]
    vencedor = max(real, key=real.get)
    p_lider = {c: float((df["vencedor"] == c).mean()) for c in res.candidatos_validos}
    por_cand = {}
    for c in res.candidatos_validos:
        x = df[f"{c}_val"].to_numpy()
        lo, hi = np.quantile(x, [0.05, 0.95])
        por_cand[c] = {
            "real": real[c], "mediana": float(np.median(x)), "ic90": [float(lo), float(hi)],
            "pit": scoring.pit(x, real[c]), "crps": scoring.crps_amostral(x, real[c]),
            "interval_score_90": scoring.interval_score(lo, hi, real[c], 0.10),
            "cobertura": {str(k): v for k, v in scoring.cobertura(x, real[c]).items()},
        }
    p2t = float(df["tem_2turno"].mean())
    return {
        "as_of": "2026-10-03",
        "parametros": {k: getattr(cfg, k) for k in (
            "sd_erro_comum_pp", "gl_erro_comum", "sd_deriva_30d_pp", "efeitos_instituto")},
        "p_lideranca": p_lider,
        "lider_real": vencedor,
        "brier_lideranca": scoring.brier_multiclasse(p_lider, vencedor),
        "log_score_lideranca": scoring.log_score(p_lider.get(vencedor, 0.0)),
        "p_segundo_turno": p2t,
        "brier_segundo_turno": scoring.brier_binario(p2t, True),
        "candidatos": por_cand,
    }


def pontuar_segundo_turno_2026(sd_fatia_pp: float = 2.5, seed: int = 2026) -> dict:
    """Score the calibrated runoff forecast as of 2026-10-24."""
    import src.simulation_2turno as s2

    df = pd.read_csv(ROOT / "data/pesquisas_only_2turno.csv")
    df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.date
    cand_a, cand_b, fatia_a, _ = s2.agregar_fatia_dois_candidatos(df, date(2026, 10, 24))
    import tempfile

    # simular() writes a CSV to OUTPUT_DIR; keep the user's outputs/ untouched.
    original = s2.OUTPUT_DIR
    estado = np.random.get_state()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            s2.OUTPUT_DIR = Path(tmp)
            np.random.seed(seed)
            sim = s2.simular_calibrado(cand_a, cand_b, fatia_a, sd_fatia_pp=sd_fatia_pp)
    finally:
        s2.OUTPUT_DIR = original
        np.random.set_state(estado)
    real = RESULTADOS_OFICIAIS[("2026", "2T")]
    x = sim["voto_a"].to_numpy()
    p_a = float((x > 50).mean())
    lo, hi = np.quantile(x, [0.05, 0.95])
    return {
        "as_of": "2026-10-24", "sd_fatia_pp": sd_fatia_pp,
        "cand_a": cand_a, "fatia_pesquisas": fatia_a, "real_a": real[cand_a],
        "p_vitoria_a": p_a, "venceu_a": bool(real[cand_a] > 50),
        "brier": scoring.brier_binario(p_a, real[cand_a] > 50),
        "log_score": scoring.log_score(p_a if real[cand_a] > 50 else 1 - p_a),
        "ic90": [float(lo), float(hi)],
        "pit": scoring.pit(x, real[cand_a]), "crps": scoring.crps_amostral(x, real[cand_a]),
        "cobertura": {str(k): v for k, v in scoring.cobertura(x, real[cand_a]).items()},
    }


def pontuar_segundo_turno_2026_nucleo(n_sim: int = 100_000, seed: int = 2026, **config_kw) -> dict:
    """Score the core runoff model (``python -m src runoff``) as of 2026-10-24."""
    from src.core.config import RunoffConfig
    from src.core.runoff import sd_deriva_runoff, simular_runoff
    from src.io.runoff import carregar_runoff

    cfg = RunoffConfig(csv_path=ROOT / "data/pesquisas_2turno.csv", as_of=date(2026, 10, 24),
                       n_sim=n_sim, seed=seed, **config_kw)
    ag = carregar_runoff(cfg)
    deriva = sd_deriva_runoff(cfg.sd_deriva_30d_pp, cfg.runoff_date, cfg.as_of)
    sim = simular_runoff(ag, n_sim, np.random.default_rng(seed), cfg.sd_erro_comum_pp,
                         cfg.gl_erro_comum, deriva)
    real = RESULTADOS_OFICIAIS[("2026", "2T")]
    x = sim["voto_a"].to_numpy()
    p_a = float((x > 50).mean())
    venceu = real[ag.cand_a] > 50
    lo, hi = np.quantile(x, [0.05, 0.95])
    return {
        "as_of": "2026-10-24", "modelo": "core_v3", "cand_a": ag.cand_a,
        "fatia_pesquisas": ag.fatia_a, "sd_media": ag.sd_media, "real_a": real[ag.cand_a],
        "p_vitoria_a": p_a, "venceu_a": bool(venceu),
        "brier": scoring.brier_binario(p_a, venceu),
        "log_score": scoring.log_score(p_a if venceu else 1 - p_a),
        "ic90": [float(lo), float(hi)],
        "pit": scoring.pit(x, real[ag.cand_a]), "crps": scoring.crps_amostral(x, real[ag.cand_a]),
        "cobertura": {str(k): v for k, v in scoring.cobertura(x, real[ag.cand_a]).items()},
    }


# ─── Report ──────────────────────────────────────────────────────────────────

def executar(saida: Path) -> dict:
    casos = casos_calibracao()
    estimativas = {f"gl={g}": estimar_sd_comum(casos, g) for g in (5.0, math.inf)}
    sd_cal = estimativas["gl=5.0"]["sd_mle"]
    relatorio = {
        "casos": [dict(asdict(c), erro=c.erro) for c in casos],
        "estimativa_sd_comum": estimativas,
        "estimativa_por_turno": {
            t: estimar_sd_comum([c for c in casos if c.turno == t], 5.0) for t in ("1T", "2T")},
        "comparacao_legado": [dict(asdict(c), erro=c.erro) for c in casos_legado()],
        "loo": validacao_loo(casos),
        "vies_direcional": vies_direcional(casos),
        "previsao_2026_1t": {
            "padrao": pontuar_primeiro_turno_2026(),
            "mle": pontuar_primeiro_turno_2026(sd_erro_comum_pp=round(sd_cal, 1)),
        },
        "previsao_2026_2t": {
            "publicado_sd_2_5": pontuar_segundo_turno_2026(2.5),
            "padrao_sd_3_0": pontuar_segundo_turno_2026(3.0),
            "mle": pontuar_segundo_turno_2026(round(math.hypot(sd_cal, casos[-1].sd_media), 1)),
            "nucleo_v3": pontuar_segundo_turno_2026_nucleo(),
        },
        "fontes_resultados": FONTES_RESULTADOS,
    }
    from src.io.manifest import caminho_manifesto, criar_manifesto, salvar_manifesto

    saida.mkdir(parents=True, exist_ok=True)
    destino = saida / "calibracao_fase3.json"
    destino.write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2, default=float), encoding="utf-8")
    entradas = [ROOT / p for p in (
        "data/wikipedia/pesquisas_wikipedia_2010_2022.csv",
        "data/historico/2018_1t_T-7.csv", "data/historico/2022_1t_T-7.csv",
        "data/pesquisas.csv", "data/pesquisas_only_2turno.csv")]
    salvar_manifesto(
        criar_manifesto("calibracao", entradas, [destino],
                        {"sementes": {"primeiro_turno": 2026, "segundo_turno": 2026}},
                        as_of=None, seed=2026, n_sim=100_000, raiz=ROOT),
        caminho_manifesto(destino))
    return relatorio


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--saida", type=Path, default=Path("outputs/calibracao"))
    rel = executar(p.parse_args(argv).saida)
    est = rel["estimativa_sd_comum"]["gl=5.0"]
    print(f"sd_erro_comum_pp (MLE, t5): {est['sd_mle']:.2f}  IC95 {est['ic95']}")
    for t, e in rel["estimativa_por_turno"].items():
        print(f"  so {t}: {e['sd_mle']:.2f}  IC95 {e['ic95']}")
    for c in rel["casos"]:
        print(f"  {c['eleicao']} {c['turno']}: polls {c['fatia_pesquisas']:.2f} "
              f"real {c['fatia_real']:.2f} erro {c['erro']:+.2f}")


if __name__ == "__main__":  # pragma: no cover
    main()
