"""
brazil-election-montecarlo — Publication step for the runoff forecast
=====================================================================
Reads outputs/resumo_2turno.json (written by simulation_2turno.py in the
default ``--base fatia`` mode), validates it and writes ready-to-post texts.

Gate (the script exits with code 1 when any check fails):
    - the summary is recent (default: at most 36 hours old);
    - required fields are present;
    - probabilities add up to 100% and the shares are in range;
    - the generated text contains the methodology disclaimer.

Usage:
    python src/publicar_2turno.py
    python src/publicar_2turno.py --resumo outputs/resumo_2turno.json --max-horas 24

Output:
    outputs/post_2turno_pt.md
    outputs/post_2turno_en.md

License: MIT
"""

import re
import sys
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path

CAMPOS = ("executado_em", "cand_a", "cand_b", "fatia_a", "p_vitoria_a", "p_vitoria_b",
          "margem_mediana_pp", "parametros", "pesquisas", "sensibilidade")

AVISO = {
    "pt": ("Projeto educacional e metodológico. As probabilidades vêm de uma simulação "
           "Monte Carlo sobre pesquisas publicadas e não constituem previsão oficial. "
           "Pesquisas reais devem ser consultadas nos institutos registrados no TSE."),
    "en": ("Educational and methodological project. Probabilities come from a Monte Carlo "
           "simulation over published polls and are not an official forecast. "
           "Consult registered pollsters for actual polling."),
}


def carregar_resumo(path: Path) -> dict:
    """Loads the summary JSON. Raises FileNotFoundError when it does not exist."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Summary not found: {path}. Run simulation_2turno.py first.")
    return json.loads(path.read_text(encoding="utf-8"))


def validar_resumo(resumo: dict, max_horas: float = 36.0, agora: datetime | None = None) -> None:
    """
    Raises ValueError when the summary cannot be published.

    Checks required fields, probability consistency, share range and age.
    """
    faltam = [c for c in CAMPOS if c not in resumo]
    if faltam:
        raise ValueError(f"Summary missing fields: {faltam}")
    soma = resumo["p_vitoria_a"] + resumo["p_vitoria_b"]
    if abs(soma - 100.0) > 0.1:
        raise ValueError(f"Win probabilities add up to {soma:.2f}, expected 100")
    if not 0.0 < resumo["fatia_a"] < 100.0:
        raise ValueError(f"fatia_a out of range: {resumo['fatia_a']}")
    agora = agora or datetime.now(timezone.utc)
    gerado = datetime.fromisoformat(resumo["executado_em"])
    idade_h = (agora - gerado).total_seconds() / 3600.0
    if idade_h > max_horas:
        raise ValueError(f"Summary is {idade_h:.1f} h old (limit {max_horas:g} h). Rerun the simulation.")
    if idade_h < -0.1:
        raise ValueError("Summary timestamp is in the future")


def _linha_sensibilidade(resumo: dict, vies: str) -> float | None:
    """P(A wins) for a bias row at the sd column closest to the run's sd."""
    tabela = resumo["sensibilidade"].get(vies)
    if not tabela:
        return None
    alvo = float(resumo["parametros"]["sd_fatia_pp"])
    col = min(tabela, key=lambda k: abs(float(k) - alvo))
    return tabela[col]


def gerar_post(resumo: dict, idioma: str = "pt") -> str:
    """Builds the post text in ``pt`` or ``en`` and appends the disclaimer."""
    if idioma not in AVISO:
        raise ValueError(f"Unsupported language: {idioma}")
    a, b = resumo["cand_a"], resumo["cand_b"]
    pa, pb = resumo["p_vitoria_a"], resumo["p_vitoria_b"]
    n, ne = resumo["pesquisas"]["n"], resumo["pesquisas"]["n_efetivo"]
    ni = resumo["pesquisas"]["n_institutos"]
    sd = resumo["parametros"]["sd_fatia_pp"]
    ic = resumo["fatia_a_ic90"]
    v1, v2 = _linha_sensibilidade(resumo, "1.0"), _linha_sensibilidade(resumo, "-1.0")
    data = resumo["executado_em"][:10]
    margem_mi = resumo["margem_votos_mediana"] / 1_000_000

    if idioma == "pt":
        linhas = [
            f"Segundo turno 2026: simulação Monte Carlo ({data})", "",
            f"Probabilidade de vitória: {a} {pa:.1f}% | {b} {pb:.1f}%", "",
            f"Fatia média entre os dois candidatos: {a} {resumo['fatia_a']:.1f}% "
            f"(intervalo de 90%: {ic[0]:.1f}% a {ic[1]:.1f}%).",
            f"Margem mediana simulada: {resumo['margem_mediana_pp']:.1f} pontos "
            f"(cerca de {margem_mi:.1f} milhões de votos).", "",
            f"Base: {n} pesquisas de {ni} institutos, ponderadas por data "
            f"(tamanho efetivo da amostra: {ne}). Cada pesquisa é convertida na fatia entre "
            "os dois candidatos antes da média.",
            f"Incerteza: desvio efetivo de {sd:.1f} pontos na fatia, calibrado com o erro de "
            "margem observado nos backtests de 2018 e 2022.",
        ]
        if v1 is not None:
            linhas.append(f"Sensibilidade: se as pesquisas subestimarem {a} em 1 ponto, "
                          f"a probabilidade de {a} vai a {v1:.1f}%.")
        if v2 is not None:
            linhas.append(f"Se superestimarem em 1 ponto, vai a {v2:.1f}%.")
        linhas += ["", AVISO["pt"], "Código e metodologia: github.com/gabrielrv13/brazil-election-montecarlo"]
    else:
        linhas = [
            f"2026 runoff: Monte Carlo simulation ({data})", "",
            f"Win probability: {a} {pa:.1f}% | {b} {pb:.1f}%", "",
            f"Average two-party share: {a} {resumo['fatia_a']:.1f}% "
            f"(90% interval: {ic[0]:.1f}% to {ic[1]:.1f}%).",
            f"Median simulated margin: {resumo['margem_mediana_pp']:.1f} points "
            f"(about {margem_mi:.1f} million votes).", "",
            f"Data: {n} polls from {ni} pollsters, time-weighted (effective sample size: {ne}). "
            "Each poll is reduced to the share between the two candidates before averaging.",
            f"Uncertainty: effective sd of {sd:.1f} points on the share, calibrated to the margin "
            "error seen in the 2018 and 2022 backtests.",
        ]
        if v1 is not None:
            linhas.append(f"Sensitivity: if polls under-measure {a} by 1 point, "
                          f"{a}'s probability goes to {v1:.1f}%.")
        if v2 is not None:
            linhas.append(f"If they over-measure by 1 point, it goes to {v2:.1f}%.")
        linhas += ["", AVISO["en"], "Code and methodology: github.com/gabrielrv13/brazil-election-montecarlo"]
    texto = "\n".join(linhas) + "\n"
    if idioma == "pt":
        texto = re.sub(r"(?<=\d)\.(?=\d)", ",", texto)  # decimal comma
    if AVISO[idioma] not in texto:
        raise ValueError("Disclaimer missing from generated text")
    return texto


def main(argv=None) -> int:
    """CLI entry point. Returns 0 on success, 1 when the gate fails."""
    p = argparse.ArgumentParser(description="Generate runoff forecast posts")
    p.add_argument("--resumo", default="outputs/resumo_2turno.json")
    p.add_argument("--saida", default="outputs")
    p.add_argument("--max-horas", type=float, default=36.0)
    a = p.parse_args(argv)
    try:
        resumo = carregar_resumo(Path(a.resumo))
        validar_resumo(resumo, a.max_horas)
        saida = Path(a.saida)
        saida.mkdir(parents=True, exist_ok=True)
        for idioma in ("pt", "en"):
            (saida / f"post_2turno_{idioma}.md").write_text(gerar_post(resumo, idioma), encoding="utf-8")
    except (FileNotFoundError, ValueError) as exc:
        print(f"Publication gate failed: {exc}")
        return 1
    print(f"Posts written to {saida}/ (post_2turno_pt.md, post_2turno_en.md)")
    print("Next: attach outputs/simulacao_2turno.png and follow PUBLISHING.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
