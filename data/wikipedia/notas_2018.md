# 2018 presidential polls (pt.wikipedia) - extraction notes

Source: https://pt.wikipedia.org/wiki/Pesquisas_de_opini%C3%A3o_para_a_elei%C3%A7%C3%A3o_presidencial_no_Brasil_em_2018
Raw wikitext: `raw/page.wikitext` (10,563 lines), fetched with `action=raw` (revision not recorded).
Parser: `parser.py` (standard library only), run as `python -I parser.py raw/page.wikitext`.
Output: `polls_2018.csv` (UTF-8, 4,680 rows, 15 columns as specified).

## Transclusions
None. The page contains no `{{:...}}` transclusions and no sub-pages; all five tables are inline. Only the cell-colour templates (`{{Partido .../meta/cor}}`) and citation templates appear, and they were ignored. No other pages were fetched.

## Tables found

| # | secao (verbatim chain) | turno | body rows | poll groups | CSV rows |
|---|---|---|---|---|---|
| 1 | Primeiro turno > Pesquisa boca-de-urna | 1 | 1 | 1 | 10 |
| 2 | Primeiro turno > Pesquisas | 1 | 332 | 129 (128 kept) | 2,805 |
| 3 | Segundo turno > Pesquisas > Pesquisa boca-de-urna | 2 | 1 | 1 | 2 |
| 4 | Segundo turno > Pesquisas > Depois do primeiro turno | 2 | 25 | 25 | 75 |
| 5 | Segundo turno > Pesquisas > Antes do primeiro turno | 2 | 597 | 98 (97 kept) | 1,788 |

Totals: 4,680 CSV rows. turno 1: 2,815 rows, 129 polls. turno 2: 1,865 rows, 123 polls. 252 poll groups in total, none mixing turnos.

## Skipped
- Colspan annotation rows (4): wikitext lines 766, 969, 6901, 7429. These are editorial notes such as "Em 31 de agosto de 2018, o TSE indeferiu a candidatura de Lula". They are not poll data.
- 2014 election results (2 rows): lines 4496 ("5 de outubro de 2014") and 10522 ("26 de outubro de 2014"), labelled "Eleições de 2014" with Rousseff and Neves values. They are results of a different election, so they would be wrong under ano=2018. Not included. The page has no 2018 result row, so no RESULTADO rows were emitted.

## Parsing decisions and ambiguities
- **Rowspan.** A grid honours rowspan and colspan. A value in a rowspan cell is repeated in each scenario row it covers, which is the HTML rendering. This affects 70 cells in table 2. Some blocks use two rows to show one replaced candidate (for example Meirelles becomes Temer), so these repeats are needed.
- **candidato.** The candidate name in the cell's parenthesis is used when present (e.g. "(Lula)", "(Gomes)"). Otherwise the column header is used (e.g. "Haddad", "Sem filiação"). Party-only headers (PT, PDT, PSB...) therefore appear only when a cell names no candidate. Names are as written in the table, so "Silva" is Marina Silva and "Dias" is Álvaro Dias, but the CSV keeps the table's own name. "Haddad, apoiado por Lula" and "algum candidato apoiado por Lula" are kept as written.
- **Categories.** "Outros" and "Brancos/Nulos" are used as specified. The combined column "Abst./Não decid." is kept verbatim as "Abst./Não decid." rather than split into "Abstenção" and "Indecisos", since splitting would be a guess.
- **turno.** Rows with exactly two candidate values are runoff matchups (turno 2). Rows with three or more are first-round (turno 1). Table 5 sits under "Segundo turno" and every row in it is a two-candidate matchup, so all of it is turno 2. The first-round rows of table 2 include 2015 hypothetical scenarios.
- **cenario.** Runoff rows get "A x B" in column order (e.g. "Haddad x Bolsonaro"). Other multi-row polls get "Cenário k", where k is positional within the poll block, because the wiki does not name scenarios. A single-row poll gets an empty cenario.
- **tipo.** Always empty. The wiki never states estimulada or espontânea in table cells; the words appear only in article URLs and prose.
- **Swapped source cells.** Line 7301 (3–5 set 2018, XP/Ipespe, 2,000 respondents, MoE 2.2): the Total and Margem cells are in swapped columns (decimal in Total, thousands count in Margem). The parser swaps them back. This is the only such group.
- **Dates.** Parsed to ISO. Month-only or two-range dates are not parseable and are left empty. Their original text is appended to linha_wiki as `N; data_original=...`. Affected groups: "15–18 e 21–23 de maio de 2018" (3 scenario rows, 2018), "junho de 2016" (1 row), "outubro de 2015" (2 rows), "agosto de 2015" (2 rows). These are 4 poll groups, 45 CSV rows with empty data_inicio/data_fim. No dates were guessed.
- **Registration.** `BR-NNNNN/AAAA` is normalised to ASCII. Some cells use a Unicode hyphen ("BR‐05003/2018") or a space ("BR 08510/2018"). Cells listing two registrations keep both, comma-separated (e.g. "BR-09600/2018, BR-05699/2018"). Blank where the wiki has none (3,081 rows have one).
- **Institute / contratante.** Split on the last "/" in "Contratante/Instituto". Where there is no slash, contratante is empty (e.g. "#PESQUISA365", "Paraná Pesquisas").
- **Numbers.** Portuguese decimals (comma) and thousands separators (dot) are converted. "–" and empty cells are skipped, not written as 0. 34 rows have no sample size and 12 rows have no margin (wiki "–").
- **linha_wiki.** 1-based line number of the `|-` row marker where the scenario row starts (954 distinct values).
- **secao.** Heading titles joined with " > ", without the "=" markers.
- **Years.** Dates run from 2015-03-26 to 2018-10-28. Pre-campaign polls from 2015–2017 are on this page, so they are included. ano is 2018 for all rows, as specified.

## Self-check (run on the output)
- Scenario sums (pct per linha_wiki, 954 scenario rows): 952 lie within 90–110. Two are outside: line 2263 (sum 79.5, turno 1, Cenário 2) and line 3246 (sum 80.7, turno 1, Cenário 2). In both, the printed values do not reach 100 and the scenario seems to omit candidates; the values are kept as printed, not adjusted.
- Distinct polls: turno 1 = 129; turno 2 = 123; total 252.
- Date range: 2015-03-26 to 2018-10-28 (parsed dates only).
- Top 10 institutes by distinct polls: Datafolha 46, Ipespe 42, MDA 28, IBOPE 26, Vox Populi 25, Paraná Pesquisas 24, DataPoder360 23, RealTime Big Data 13, FSB Pesquisa 11, Brasilis 4.
- Spot checks against raw lines:
  - Line 4172: Lula 16,8 / Gomes 4,7 / Silva 18,2 / Dias 2,7 / Neves 27,6 / Bolsonaro 8,4 / Outros 4,9 / Abst. 16,7 (sums to 100). CSV matches.
  - Line 2053 (table 2, first round): n = 10500, MoE 1.8, registro BR-09186/2018, Haddad 6 / Gomes 11 / Silva 7 / Meirelles 1 / Dias 5 / Alckmin 6 / Bolsonaro 21. CSV matches.
  - Line 6189: Haddad 31 / Gomes 42, runoff, turno 2. CSV matches.
