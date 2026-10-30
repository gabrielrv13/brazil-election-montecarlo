"""A02/P0.3: event contracts across engine, CLI, UI, reports and persistence."""
import ast
from contextlib import closing
from datetime import date
from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd
import pytest

from src import cli
from src.core.config import PollData, SimulationConfig, SimulationResult
from src.core.events import adicionar_eventos, eventos_primeiro_turno, probabilidades_vitoria_2t
from src.core.simulation import simular_primeiro_turno
from src.io.history import carregar_historico, init_db, salvar_historico, save_history
from src.io.report import _section_first_round, save_csvs
from src.viz.charts import plot_forecast_history, plot_qualify_probability

CANDIDATES = ['A', 'B', 'C']


def frame(votes):
    df = pd.DataFrame(votes, columns=[f'{c}_val' for c in CANDIDATES])
    for c in CANDIDATES:
        df[c] = df[f'{c}_val']
    df['vencedor'] = np.array(CANDIDATES)[np.argmax(votes, axis=1)]
    df['margem_1t'] = np.sort(votes, axis=1)[:, -1] - np.sort(votes, axis=1)[:, -2]
    adicionar_eventos(df, CANDIDATES)
    return df


def result(votes):
    df = frame(votes)
    return SimulationResult(df1=df, df2=pd.DataFrame(),
        pv={c: float((df.vencedor == c).mean()) for c in CANDIDATES},
        p2v={}, p2t=0., info_matchups={}, info_lim_1t={}, info_indecisos={},
        margins=df.margem_1t.to_numpy())


@pytest.mark.parametrize('votes,leader,direct,qualify,runoff', [
    ([45,35,20], [1,0,0], [0,0,0], [1,1,0], True),
    ([50,30,20], [1,0,0], [0,0,0], [1,1,0], True),
    ([50.0000001,29.9999999,20], [1,0,0], [1,0,0], [0,0,0], False),
    ([49.9999999,30.0000001,20], [1,0,0], [0,0,0], [1,1,0], True),
    ([40,40,20], [.5,.5,0], [0,0,0], [1,1,0], True),
    ([40,30,30], [1,0,0], [0,0,0], [1,.5,.5], True),
    ([100/3]*3, [1/3]*3, [0,0,0], [2/3]*3, True),
    ([0,100,0], [0,1,0], [0,1,0], [0,0,0], False),
])
def test_events_boundary_and_ties(votes, leader, direct, qualify, runoff):
    sample = np.array([votes], dtype=float)
    untouched = sample.copy()
    events = eventos_primeiro_turno(sample)
    np.testing.assert_allclose(events['lideranca'][0], leader)
    np.testing.assert_allclose(events['vitoria_1t'][0], direct)
    np.testing.assert_allclose(events['classificacao_2t'][0], qualify)
    assert events['segundo_turno'][0] == runoff
    np.testing.assert_array_equal(sample, untouched)


@pytest.mark.parametrize('votes', [[], [[100]], [[np.nan,50]], [[np.inf,0]],
    [[-1,101]], [[45,35,10]], [[0,0]]])
def test_invalid_event_inputs_raise(votes):
    with pytest.raises(ValueError, match='valid-vote'):
        eventos_primeiro_turno(votes)


def test_two_candidates_exact_tie():
    events = eventos_primeiro_turno([[50,50]])
    np.testing.assert_allclose(events['lideranca'], [[.5,.5]])
    np.testing.assert_allclose(events['classificacao_2t'], [[1,1]])
    assert events['segundo_turno'][0]


def test_probabilistic_identities_include_tied_draws():
    output = result([[45,35,20], [60,20,20], [40,30,30], [40,40,20], [50,25,25]])
    assert sum(output.p_vitoria_1t.values()) + output.p2t == pytest.approx(1)
    assert sum(output.p_lideranca.values()) == pytest.approx(1)
    assert sum(output.p_classificacao_2t.values()) == pytest.approx(2*output.p2t)
    for c in CANDIDATES:
        assert output.p_vitoria_1t[c] <= output.p_lideranca[c]
        assert output.p_classificacao_2t[c] <= output.p2t
    assert output.pv['A'] == 1.0  # deprecated argmax contract preserved
    assert output.p_lideranca['A'] < 1.0  # tie credits differ intentionally


def test_cli_453520_actual_engine(capsys):
    cfg = SimulationConfig(n_sim=10000, seed=42, election_date=date(2020,1,1))
    polls = PollData(candidatos=CANDIDATES, votos_media=np.array([45.,35.,20.]),
                    rejeicao=np.zeros(3), desvio_base=2., indecisos=0.)
    output = cli._run_simulation(cfg, polls)
    assert output.p_lideranca['A'] == 1.0
    assert output.p_vitoria_1t == dict.fromkeys(CANDIDATES, 0.)
    assert output.p2t == 1.0
    assert output.p2v == {}  # not simulated, not zero probability
    text = capsys.readouterr().out
    assert 'direct victory (>50% valid)=0.00%' in text
    assert 'leadership=100.00%' in text
    assert 'Second round occurs: 100.00%' in text


def extract_function(path, name, namespace):
    """Execute the real UI/legacy function without importing its UI/MCMC side effects."""
    tree = ast.parse(Path(path).read_text(encoding='utf-8-sig'))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    module = ast.Module(body=[function], type_ignores=[])
    exec(compile(module, path, 'exec'), namespace)
    return namespace[name]


def test_dashboard_uses_same_contract_as_cli(monkeypatch, tmp_path):
    polls = PollData(candidatos=CANDIDATES, votos_media=np.array([45.,35.,20.]),
                    rejeicao=np.zeros(3), desvio_base=2., indecisos=0.)
    cfg = SimulationConfig(n_sim=1000, seed=4, election_date=date(2020,1,1))
    first = simular_primeiro_turno(cfg, polls)
    namespace = dict(Path=Path, date=date, pd=pd, SimulationConfig=SimulationConfig,
        SimulationResult=SimulationResult, load_polls=lambda _: polls,
        simular_primeiro_turno=lambda *_: first, _ELECTION_DATE=date(2020,1,1))
    build = extract_function('src/viz/dashboard.py', '_build_result', namespace)
    ui, _ = build(str(tmp_path / 'polls.csv'), 1000)
    monkeypatch.setattr('src.core.simulation.simular_primeiro_turno', lambda *_: first)
    command_line = cli._run_simulation(cfg, polls)
    for key in ('p_lideranca','p_vitoria_1t','p_classificacao_2t','p2t'):
        assert getattr(ui,key) == getattr(command_line,key)


def test_csv_pdf_sections_and_sqlite_share_events(tmp_path):
    from reportlab.lib.styles import getSampleStyleSheet
    output = result([[45,35,20]]*3)
    p1, _ = save_csvs(output, tmp_path)
    csv = pd.read_csv(p1)
    assert csv.vencedor_1t.isna().all()
    assert csv.tem_2turno.all()
    assert csv.event_contract_version.eq(2).all()
    assert csv.evento_vitoria_1t_A.eq(False).all()
    summary = pd.read_csv(next(tmp_path.glob('*_probabilidades.csv')))
    assert summary.p_lideranca.tolist() == [1,0,0]
    assert summary.p_vitoria_1t.eq(0).all()
    assert summary.p2t.eq(1).all()
    story = _section_first_round(output, getSampleStyleSheet())
    assert story[1]._cellvalues[1][-3:] == ['100.0%', '0.0%', '100.0%']
    db = tmp_path/'history.db'
    save_history(output,db)
    row = carregar_historico(db,days=0).iloc[0]
    for key in ('p_lideranca','p_vitoria_1t','p_classificacao_2t','p2t'):
        assert row[key] == getattr(output,key)
    assert row.event_contract_version == 2


def test_history_migration_preserves_legacy_values(tmp_path):
    from src.io.history import _DDL
    db = tmp_path/'legacy.db'
    with closing(sqlite3.connect(db)) as conn:
        conn.executescript(_DDL)
        conn.execute('INSERT INTO schema_version VALUES (1)')
        conn.execute('INSERT INTO forecasts (run_at,n_sim,p2t,pv_json,p2v_json) '
                     'VALUES (?,?,?,?,?)', ('2022-01-01',1000,.8,'{"A":1.0}','{"A":0.9}'))
        conn.commit()
    legacy = carregar_historico(db, days=0).iloc[0]
    assert legacy.pv == {'A':1.}
    assert legacy.p_vitoria_1t == {}
    assert legacy.event_contract_version == 1
    init_db(db)
    init_db(db)
    salvar_historico(result([[45,35,20]]),db)
    history = carregar_historico(db,days=0)
    assert history.iloc[0].pv == {'A':1.}
    assert history.iloc[0].p2v == {'A':.9}
    assert history.iloc[0].p_vitoria_1t == {}
    assert history.iloc[1].p_vitoria_1t == dict.fromkeys(CANDIDATES,0.)
    assert history.event_contract_version.tolist() == [1,2]


def test_history_chart_never_substitutes_leadership_for_victory(tmp_path):
    import matplotlib.pyplot as plt
    db = tmp_path/'history.db'
    save_history(result([[45,35,20]]),db)
    history = carregar_historico(db, days=0)
    fig = plot_forecast_history(history, event='p_vitoria_1t')
    try:
        line = next(line for line in fig.axes[0].lines if line.get_label() == 'A')
        assert line.get_ydata().tolist() == [0.]
        assert 'direta' in fig.axes[0].get_legend().get_title().get_text()
    finally:
        plt.close(fig)
    fig = plot_forecast_history(history, event='p2v')
    try:
        assert not any(line.get_label() == 'A' for line in fig.axes[0].lines)
    finally:
        plt.close(fig)


def test_qualify_chart_excludes_direct_wins():
    import matplotlib.pyplot as plt
    fig = plot_qualify_probability(frame([[60,25,15]]),CANDIDATES,['r','b','g'])
    try:
        bars = fig.axes[0].patches[1::2]
        assert [bar.get_width() for bar in bars] == [0.,0.,0.]
    finally:
        plt.close(fig)


def test_sampling_regression_against_pre_a02_engine():
    # Baseline captured from HEAD:src/core/simulation.py before this correction.
    polls = PollData(candidatos=['A','B','C','Brancos/Nulos'],
        votos_media=np.array([45.,35.,20.,10.]), rejeicao=np.array([55.,60.,75.,0.]),
        desvio_base=2., indecisos=3.)
    first = simular_primeiro_turno(SimulationConfig(n_sim=512,seed=314,
        election_date=date(2020,1,1)),polls)
    np.testing.assert_allclose(first.validos_final[:3], [
        [44.822653791008776,35.235652580961286,19.941693628029945],
        [45.28774882576468,34.19323936015946,20.519011814075856],
        [45.2775845483795,35.37690173112766,19.34551372049284]], rtol=0,atol=1e-10)
    np.testing.assert_allclose(first.validos_final.sum(axis=0),
        [23026.375831364865,17988.890444293604,10184.73372434153],rtol=0,atol=1e-8)
    np.testing.assert_allclose(first.df.abstencao_1t_pct[:3],
        [18.50209900149219,17.653394550722215,21.437503463394624],rtol=0,atol=1e-10)
    np.testing.assert_allclose(first.df[['A','B','C','Brancos/Nulos']].sum(),
        [20990.032709184983,16266.365811848253,9209.646942113175,4733.954536853587],rtol=0,atol=1e-8)


@pytest.mark.parametrize('votes,expected_rows', [
    ([[60,25,15],[45,35,20],[50,30,20]], [1,2]),
    ([[60,25,15]], []),
    ([[40,30,30]], []),
])
def test_legacy_second_round_conditions_after_sampling(tmp_path, votes, expected_rows):
    calls = []
    def confrontation(a,b,others,ra,rb,n):
        calls.append(n)
        return np.full(n,60.), np.full(n,40.)
    namespace = dict(np=np,pd=pd,CANDIDATOS=CANDIDATES, REJEICAO=np.zeros(3),
        OUTPUT_DIR=tmp_path,ABSTENCAO_2T_MU=.22,ABSTENCAO_2T_SIGMA=.03,
        ELEITORADO=100000,_simular_confronto=confrontation,
        eventos_primeiro_turno=eventos_primeiro_turno,
        probabilidades_vitoria_2t=probabilidades_vitoria_2t)
    simulate = extract_function('src/simulation_v2.py','simular_segundo_turno',namespace)
    output, matchups = simulate(np.array(votes,dtype=float), CANDIDATES)
    assert sum(calls) == len(votes)  # all original hypothetical draws still sampled
    assert output.index.tolist() == expected_rows
    if expected_rows:
        assert output.tem_2turno.all()
        assert sum(m['prob_matchup'] for m in matchups.values()) == pytest.approx(100.)
        assert output.voto_a.tolist() == [60.]*len(expected_rows)


def test_conditional_second_round_win_includes_qualification_and_splits_ties():
    df = pd.DataFrame(dict(finalista_a=['A','A','B'], finalista_b=['B','C','C'],
                           voto_a=[60.,50.,0.], voto_b=[40.,50.,100.],
                           tem_2turno=[True,True,False]))
    probs = probabilidades_vitoria_2t(df,CANDIDATES)
    assert probs == {'A':.75,'B':0.,'C':.25}
    assert sum(probs.values()) == 1.
    assert probabilidades_vitoria_2t(df.loc[[2]],CANDIDATES) == {}

def test_cli_full_pipeline_persists_and_exports_consistent_events(tmp_path, monkeypatch):
    from argparse import Namespace
    polls = PollData(candidatos=CANDIDATES, votos_media=np.array([45.,35.,20.]),
                    rejeicao=np.zeros(3), desvio_base=2., indecisos=0.)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli,'load_polls',lambda _: polls)
    cfg = SimulationConfig(n_sim=1000,seed=42,election_date=date(2020,1,1))
    assert cli._run_pipeline(cfg,Namespace(no_history=False)) == 0
    row = carregar_historico(tmp_path/'outputs/forecast_history.db',days=0).iloc[0]
    assert row.p_vitoria_1t == dict.fromkeys(CANDIDATES,0.)
    assert row.p_lideranca['A'] == 1.
    assert row.p2t == 1.
    assert row.p2v == {}
    summary = pd.read_csv(next((tmp_path/'outputs').glob('*_probabilidades.csv')))
    assert summary.p_vitoria_1t.eq(0).all()
    assert summary.p2t.eq(1).all()
    assert len(list((tmp_path/'outputs').glob('*.pdf'))) == 1


def test_streamlit_displays_direct_victory_separately(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    # No button is clicked: the real UI consumes an injected completed result,
    # avoiding writes to the user's outputs and any Bayesian imports.
    source = Path(__file__).resolve().parents[1]/'src/viz/dashboard.py'
    polls = PollData(candidatos=CANDIDATES, votos_media=np.array([45.,35.,20.]),
                    rejeicao=np.zeros(3), desvio_base=2., indecisos=0.)
    monkeypatch.chdir(tmp_path)
    app = AppTest.from_file(str(source),default_timeout=30)
    app.session_state['ran'] = True
    app.session_state['result'] = result([[45,35,20]]*3)
    app.session_state['poll_data'] = polls
    app.session_state['candidatos_validos'] = CANDIDATES
    app.session_state['download_paths'] = []
    app.run()
    assert not app.exception
    metrics = {metric.label:metric.value for metric in app.metric}
    assert metrics['A'] == '0.0%'
    assert metrics['Probabilidade de 2º turno'] == '100.0%'
    assert any('maioria absoluta' in element.value for element in app.markdown)

def test_second_round_chart_does_not_assign_other_matchup_mass_to_runner_up():
    import matplotlib.pyplot as plt
    from src.viz.charts import _render_second_round_semicircle
    df = pd.DataFrame(dict(finalista_a=['A','A','B','B'], finalista_b=['B','C','C','C'],
                           voto_a=[60.,40.,60.,40.], voto_b=[40.,60.,40.,60.],
                           tem_2turno=[True]*4))
    fig, ax = plt.subplots()
    try:
        _render_second_round_semicircle(ax,df,CANDIDATES,dict(zip(CANDIDATES,['r','b','g'])),'white')
        labels = [t.get_text() for t in ax.texts]
        assert 'A: 25.0%' in labels
        assert 'B: 25.0%' in labels
        assert 'C: 50.0%' in labels
        assert not ax.patches
    finally:
        plt.close(fig)

@pytest.mark.parametrize('representation', ['finalists', 'credits'])
def test_p2v_denominator_includes_runoffs_without_candidate(representation):
    df = pd.DataFrame(dict(finalista_a=['A','B','B','B','A'],
        finalista_b=['B','C','C','C','C'], voto_a=[60.,60.,40.,60.,60.],
        voto_b=[40.,40.,60.,40.,40.], tem_2turno=[True,True,True,True,False]))
    if representation == 'credits':
        df = pd.DataFrame(dict(A_win=[1.,0.,0.,0.,1.], B_win=[0.,1.,0.,1.,0.],
            C_win=[0.,0.,1.,0.,0.], tem_2turno=df.tem_2turno))
    assert probabilidades_vitoria_2t(df,CANDIDATES) == {'A':.25,'B':.5,'C':.25}


def test_p2v_rejects_missing_credits_instead_of_candidate_specific_denominator():
    df = pd.DataFrame(dict(A_win=[1.,np.nan],B_win=[0.,1.],C_win=[0.,0.],
                           tem_2turno=[True,True]))
    with pytest.raises(ValueError, match='explicit zero'):
        probabilidades_vitoria_2t(df,CANDIDATES)

def test_p2v_common_denominator_survives_reports_charts_and_history(tmp_path):
    from dataclasses import replace
    import matplotlib.pyplot as plt
    from reportlab.lib.styles import getSampleStyleSheet
    from src.io.report import _section_second_round
    df = pd.DataFrame(dict(finalista_a=['A','B','B','B','A'],
        finalista_b=['B','C','C','C','C'], voto_a=[60.,60.,40.,60.,60.],
        voto_b=[40.,40.,60.,40.,40.], tem_2turno=[True,True,True,True,False]))
    output = replace(result([[45,35,20],[20,45,35],[20,35,45],[20,45,35],[60,20,20]]),
        df2=df, info_matchups={'B vs C':dict(cand_a='B',cand_b='C',prob_matchup=75.,
                                            prob_a=200/3,prob_b=100/3)})
    assert output.p2t == .8
    assert output.p2v == {'A':.25,'B':.5,'C':.25}
    save_history(output,tmp_path/'history.db')
    history = carregar_historico(tmp_path/'history.db',days=0)
    assert history.iloc[0].p2v == output.p2v
    save_csvs(output,tmp_path)
    summary = pd.read_csv(next(tmp_path.glob('*_probabilidades.csv'))).set_index('candidate')
    assert summary.p2v.to_dict() == output.p2v
    story = _section_second_round(output,getSampleStyleSheet())
    probability_table = next(t for t in story if hasattr(t,'_cellvalues')
                             and t._cellvalues[0] == ['Candidate','P(2nd-round win)'])
    assert probability_table._cellvalues[1:] == [['B','50.00%'],['A','25.00%'],['C','25.00%']]
    fig = plot_forecast_history(history,event='p2v')
    try:
        values = {line.get_label():line.get_ydata().tolist() for line in fig.axes[0].lines
                  if line.get_label() in CANDIDATES}
        assert values == {'A':[25.],'B':[50.],'C':[25.]}
    finally:
        plt.close(fig)
