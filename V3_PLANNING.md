# brazil-election-montecarlo — v3 Planning & Expansion Strategy

**Document date:** 2026-03-04  
**Current version:** v2.7.0  
**Target:** v3.0.0

---

## Part I — v3 Architecture Vision

### Why a major version bump

v2.x solved the simulation core. Every feature added since v2.2 has been an
increment on the same architecture: one CSV, one simulation file, one output.
v3 should change the structural contract, not just add another column to the CSV.

Three problems that warrant a `MAJOR` bump:

1. **The model is static between runs.** Poll data lives in a file. The user
   updates it manually. There is no concept of state over time.
2. **The simulation has no memory.** Each run is independent. There is no way
   to compare today's forecast to last week's or track how the race evolved.
3. **The output is terminal-first.** The dashboard exists but is an afterthought
   wrapped around a CLI script. The primary interface for a political forecasting
   tool should be visual and time-aware.

v3 reorients the project around these three axes: **time, history, and interface.**

---

## Part II — v3 Feature Set

### Feature 1 — Historical Forecast Tracker

**What:** Every time the simulation runs, the result is persisted to a database
(SQLite, local file). A time-series chart shows how each candidate's win
probability evolved over the campaign.

**Why:** This is the most important single feature for political forecasting
credibility. FiveThirtyEight, Nate Silver, and Politico all lead with this chart.
It answers the question every reader has: "Is this candidate going up or down?"

**Technical approach:**

```python
# outputs/forecast_history.db  (SQLite)
# Table: forecasts
# Columns: run_id, timestamp, candidato, prob_1t, prob_2t, voto_medio,
#          ci_lo, ci_hi, n_pesquisas_usadas

def salvar_historico(df1, df2, pv, p2v):
    """Appends current simulation results to forecast history database."""
    ...
```

**Visualization:** Line chart per candidate with confidence band. X axis = date,
Y axis = win probability. Vertical markers for each new poll added.

**Version:** `v3.0.0` — core feature, included in initial release.

---

### Feature 2 — Automatic Poll Ingestion

**What:** A scraper (or semi-automated pipeline) that fetches new polls from
public sources (Wikipedia electoral pages, G1 Política, Poder360) and appends
them to `pesquisas.csv` without manual editing.

**Why:** The current workflow requires the user to manually edit the CSV every
time a new poll is released. In an election year with polls every few days, this
is a bottleneck that discourages regular updates.

**Technical approach:**

```
src/
└── ingestion/
    ├── scraper_wikipedia.py   # Scrapes standard Wikipedia poll tables
    ├── scraper_poder360.py    # Poder360 has structured poll data
    └── pipeline.py            # Deduplication + CSV append + validation
```

Ingestion validates against the existing CSV schema before writing. Duplicate
detection is by `(instituto, data, candidato)` composite key.

**Version:** `v3.1.0` — separate minor after core is stable.

---

### Feature 3 — Scenario Engine

**What:** A structured way to run "what-if" scenarios and compare them.
Examples: "What if Lula's rejection drops to 38%?", "What if a third candidate
consolidates Outros voters?"

**Why:** The simulation already handles different inputs — the scenario engine
just makes this formal and comparable. It also dramatically increases the
analytical value of the tool for journalists and researchers.

**Technical approach:**

```python
# scenarios.yaml
scenarios:
  base:
    description: "Current polls, no changes"
    csv: data/pesquisas.csv

  lula_rejeicao_baixa:
    description: "Lula rejection drops 4pp after economic announcement"
    overrides:
      - candidato: Lula
        rejeicao_pct: 38.0

  terceiro_candidato:
    description: "Strong third candidate consolidates at 20%"
    overrides:
      - candidato: Outros
        intencao_voto_pct: 20.0
        desvio_padrao_pct: 3.0
```

Output: side-by-side comparison table and overlaid probability distributions.

**Version:** `v3.1.0`.

---

### Feature 4 — State-Level Simulation (Electoral College)

**What:** Model regional vote distribution across Brazilian states using
historical voting patterns as priors. Weight national results by state
electorate size.

**Why:** Brazil's presidential election is a national popular vote, but
understanding regional variance matters for campaigns and for media coverage.
Lula's dominance in the Northeast and Bolsonaro's strength in the South/Center-West
are structurally important for interpreting polls.

**Technical approach:**

```python
# data/historico_estados.csv
# Columns: estado, uf, eleitorado, lula_2022_pct, bolsonaro_2022_pct, regiao

# Model: state result = national_result + regional_bias + noise
# regional_bias calibrated from 2018 and 2022 results
# state electorate weights from TSE 2026 data

def simular_estados(validos_final, candidatos_validos):
    """
    For each simulation, projects state-level results using
    regional bias priors from 2018/2022 elections.
    Returns DataFrame with per-state win probabilities.
    """
```

**Output:** Choropleth map of Brazil showing per-state win probability.

**Version:** `v3.2.0` — significant modeling addition, separate minor.

---

### Feature 5 — API Layer

**What:** A FastAPI wrapper that exposes the simulation as a REST endpoint.
External consumers (websites, bots, other scripts) can request a forecast
without running the full simulation locally.

**Why:** Enables the project to power external integrations — a Twitter/X bot
that posts daily forecasts, a journalism embed, a Google Sheets add-on.

```
GET /forecast/current
→ { "lula_prob_2t": 62.3, "flavio_prob_2t": 37.7, "prob_2turno": 94.1,
    "timestamp": "2026-03-04T08:00:00Z", "n_pesquisas": 12 }

GET /forecast/history?days=30
→ [ { "date": "2026-02-03", "lula_prob_2t": 59.1, ... }, ... ]
```

**Version:** `v3.2.0`.

---

### Feature 6 — Calibration & Backtesting

**What:** Run the model against historical Brazilian election data (2018, 2022)
and measure how well the simulation would have predicted the actual results
at various points in the campaign (90 days out, 60 days out, 30 days out, 7 days out).

**Why:** Methodological credibility. Any forecasting model should be able to answer
"how accurate has this been historically?" Without this, the win probabilities are
interesting but unverifiable.

**Technical approach:**

```
data/historico/
├── pesquisas_2022_lula_bolsonaro.csv
└── pesquisas_2018_bolsonaro_haddad.csv

src/
└── backtesting.py
    # For each historical election:
    # 1. Load polls as-of date T
    # 2. Run simulation
    # 3. Compare forecast to actual result
    # 4. Compute Brier score and calibration curve
```

**Version:** `v3.3.0`.

---

## Part III — v3 Structural Changes

### Breaking changes from v2

| Change | Reason |
|--------|--------|
| `simulation_v2.py` renamed to `simulation.py` (no suffix) | Version suffix in filename is an antipattern at v3 |
| `inicializar()` replaced by `SimulationConfig` dataclass | Eliminates global mutable state |
| Output filenames no longer include version string | Version belongs in `CHANGELOG.md`, not filenames |
| `construir_modelo()` (PyMC MCMC) moved behind `--bayesian` flag | MCMC takes 20-30s; most runs don't need it |

### `SimulationConfig` replaces globals

```python
@dataclass
class SimulationConfig:
    csv_path: Path = Path("data/pesquisas.csv")
    n_sim: int = 40_000
    seed: int | None = None
    use_bayesian: bool = False
    scenario_overrides: dict = field(default_factory=dict)

def run(config: SimulationConfig) -> SimulationResult:
    """Single entry point. No global state."""
    ...
```

This makes the codebase testable without monkey-patching module-level variables,
eliminates BUG-007 (global seed) permanently, and makes the dashboard import clean.

---

## Part IV — Release Timeline

```
March 2026
├── v2.7    simulation_2turno standalone
├── v2.8    First-round margin distribution + polymarket_edge() + --n-sim flag
└── v2.9    Backtesting module (promoted from v3.3.0 — operational priority)

April 2026
└── v3.0.0  Historical tracker + SimulationConfig refactor + clean filenames

June 2026
└── v3.1.0  Scenario engine + automatic poll ingestion

August 2026 (pre-election stretch)
└── v3.2.0  State-level simulation + API layer

October 2026 (post-1st round)
└── v3.3.0  Post-election retrospective: calibration report against 2026 results
    v3.4.0  Academic preprint — methodology + backtesting results
```

---

## Part V — Expansion & Dissemination

### Target audiences

The project currently serves one audience: the developer. v3 should serve three:

| Audience | What they want | How to reach them |
|----------|---------------|-------------------|
| Data journalists | Embeddable forecast, source-able methodology | Press kit, media outreach |
| Political scientists | Reproducible methodology, historical data | Academic preprint, GitHub |
| General public | Simple "who's winning" interface | Twitter/X bot, newsletter |

---

### Channel 1 — r/dataisbeautiful and r/brasil

The project was directly inspired by a post on r/dataisbeautiful. A well-timed
post with a high-quality visualization — particularly the semicircle chart —
has a realistic path to front page. Brazilian election content reaches both
r/dataisbeautiful and r/brasil simultaneously.

**What to post:** The main visualization image + a comment explaining the methodology.
Link to GitHub. Post after a significant poll release (Datafolha or Quaest) to
ride the news cycle.

**Timing:** Post when a major poll drops, not on a random day.

---

### Channel 2 — Twitter/X automated bot

A daily bot that posts the current forecast using the API layer from v3.2.0.
Format: the semicircle chart + three numbers (Lula 2T prob, Flávio 2T prob,
probability of going to a runoff).

The bot should also post when a new poll is added and how it moved the needle.
"Quaest poll added: Lula +1.3pp, now at 62.4% win probability" is shareable content.

**Stack:** Python + GitHub Actions (runs daily at 08:00 BRT) + Twitter API v2.

---

### Channel 3 — Poder360 and Piauí

Poder360 is Brazil's most cited political data outlet and already aggregates polls
manually. A pitch offering them the model as a methodological reference — or a
co-branded embed — is realistic. Piauí magazine covers data and methodology stories.

**What to offer:** A methodology explainer written for a non-technical audience,
plus an embeddable iframe of the dashboard. No exclusivity required.

---

### Channel 4 — Academic preprint (SSRN or OSF)

A short methods paper (8–12 pages) describing the Dirichlet model, temporal
weighting, rejection ceiling, and backtesting results against 2018/2022.
This gives the project a citable reference and positions it as methodology,
not just a visualization.

**Title candidate:** *"Monte Carlo Forecasting of Brazilian Presidential Elections:
A Dirichlet-Based Approach with Rejection Ceiling and Temporal Weighting"*

The backtesting feature (v3.3.0) is the prerequisite — the paper needs the
calibration results to be credible.

---

### Channel 5 — GitHub ecosystem

Three actions that increase GitHub visibility at zero cost:

1. **Topics:** Add `brazil`, `election-forecast`, `monte-carlo`, `political-science`,
   `2026-elections` to the repository topics. GitHub search surfaces these.
2. **GitHub Pages:** Deploy the dashboard as a static page. Streamlit Community Cloud
   offers free hosting — the dashboard can be live at a public URL with one click.
3. **Awesome lists:** Submit to `awesome-brazil`, `awesome-monte-carlo`, and
   `awesome-political-science` lists on GitHub. These drive sustained organic traffic.

---

### What not to do

- Do not post forecasts without the methodology disclaimer visible. The project
  is educational; presenting it as a definitive prediction invites criticism that
  damages credibility.
- Do not engage with partisan framing. The model outputs probabilities, not
  endorsements. Any post should be framed as "here is what the data shows"
  and never "here is who will win."
- Do not launch the bot before the API layer is stable. An automated account
  posting wrong numbers is worse than no bot.

---

## Part VI — v3 Success Metrics

| Metric | Current | v3 Target |
|--------|---------|-----------|
| GitHub stars | Unknown | 200+ |
| Test coverage | ~30% (6 tests) | 80%+ |
| Time to update with new poll | ~5 min manual | <1 min automated |
| Public URL (dashboard) | None | Streamlit Cloud |
| Documented methodology | README only | Preprint + README |
| Historical forecast record | None | Full 2026 campaign |

---

## Part VII — Polymarket Integration Strategy

### Markets currently open (March 2026)

| Market | Model output required | Available from |
|--------|----------------------|----------------|
| Vencedor final (presidente eleito) | `p2v` — prob. vitória 2T | Now |
| Flávio Bolsonaro termina em 2º | `info_matchups` — prob. chegar ao 2T | Now |
| Renan Santos termina em 3º | `pv` 1T, posição ordinal | Now |
| Lula vence 1T por >Xpp | `P(margem_1t > X)` | After v2.8 |

### Prerequisites before operating

1. **v2.9 backtesting completed** with Brier score documented — without
   demonstrated calibration, any calculated edge may be model noise, not
   market inefficiency.
2. **v2.8 margin output implemented** — required for the threshold market.
3. **Edge calculated** for each market at current Polymarket odds.

### Entry criteria (moderate risk profile)

- Minimum edge: 12pp (model probability minus market implied probability)
- Model uncertainty: `desvio_base` ≤ 8pp at time of entry
- Edge must persist across two consecutive weekly model runs before entry

### Timing framework

| Period | Rationale | Action |
|--------|-----------|--------|
| March–May 2026 | High uncertainty, odds open | Monitor only; enter if edge > 20pp |
| June–August 2026 | Polls converging, model stabilizing | Primary entry window |
| September–October 2026 | Maximum precision, odds tight | Margin and position markets only |

The ">15pp margin" market is only reliably forecastable from August onward
when dedicated 2nd-round poll data begins to appear. Before that,
`margem_1t` from v2.8 is a proxy — correlated with but not identical to
the 2nd-round margin.

### Position vs winner markets

Position markets (Flávio 2º, Renan 3º) tend to be less liquid and less
efficiently priced than the winner market. `info_matchups` (prob. of each
pair reaching the runoff) is the direct input for the 2nd-place market.
3rd-place probability is read directly from the 1st-round simulation output.

### Kelly sizing

Use `polymarket_edge()` output (`kelly_fraction`) with a **half-Kelly
multiplier**. Full Kelly is not appropriate with a backtesting sample of
only two elections.

### N_SIM note

The default `N_SIM = 40_000` is adequate for all win probability markets.
For threshold markets where `model_prob < 0.05`, rerun with `--n-sim 200000`
before sizing a position. This flag is implemented in v2.8.

### Model risk

The Brier score from two historical elections (2018, 2022) is a small-sample
estimate. Systematic poll bias (shy Bolsonaro effect, 2022: ~7pp underestimate)
is inherited by the model and will be quantified in v2.9. Any edge in favor
of "leading candidate wins by large margin" should be discounted until
backtesting confirms the model's calibration on margin markets specifically.