# Notes: polls for the 2010 Brazilian presidential election (pt.wikipedia)

Source: pt.wikipedia "Pesquisas de opinião para a eleição presidencial no Brasil em 2010", fetched with action=raw on the run date. Raw file: `raw/page.wikitext` (899 lines).

Transclusions: the page transcludes only navboxes and notices (`{{Pesquisas de opinião...}}`, `{{Artigo principal}}`, `{{Referências}}`, `{{Eleição presidencial...}}`). None holds poll tables, so no sub-pages were fetched.

## Tables found

| wiki line | section | turno | poll rows parsed | status |
|---|---|---|---|---|
| 1-10 | (top, before first heading) | - | 0 | Skipped: candidate photo header table (Dilma, Serra, Marina), not poll data |
| 31-883 | `== Pesquisas ==` | 1 | 85 | Parsed: columns Data, Instituto, Dilma Rousseff, José Serra, Marina Silva, Ciro Gomes, Heloísa Helena, Outros, Vantagem |

Only one poll table exists. No second-round (turno 2) table or hypothetical runoff matchup appears on the page, so no turno 2 rows exist.

## Column handling

- `Outros / Nenhum / Não sabe` is written as candidato `Outros`. The header bundles three categories, so the split is not available from the page.
- `Vantagem` (lead in points) is a derived figure, not a poll result. It is skipped.
- No `Brancos`, `Nulos`, `Indecisos` or `Abstenção` columns exist in the table.
- Cells `—` (inside `<center>`) mean the candidate was not in that poll. They are skipped, not written as 0. Marina Silva is `—` in six 2008-2009 polls (lines 814-874), so she has 79 rows, not 85.

## Fields left empty (not present on the page)

- `amostra`, `margem_erro_pp`, `registro_tse`, `contratante`, `cenario`: the table has none of these.
- Prose at line 27 gives Vox Populi tracking figures (2,000 interviews a day, margin 2.2 p.p.). They apply to the tracking series from 30 September only, so they were not spread across rows.
- `tipo` is set to `estimulada` for all rows. Basis: line 25 states that the spontaneous polls were excluded, so the included polls show candidate cards. This is an inference from the text and can be reverted to empty if strictness is preferred.
- `secao` is the heading chain verbatim: `== Pesquisas ==`.

## Dates

- Accepted format variants: "28-29 de setembro de 2010", "2-5 de agosto de 2010", "24-26 de agosto 2010" (missing "de" before the year; accepted as an unambiguous variant), and "8 de setembro 2009".
- Unparseable: line 334, "10 de setembro de 20102010" (a typo in the wiki source with a doubled year). Per the rule, `data_inicio` and `data_fim` are empty and `linha_wiki` is `334; data_original=10 de setembro de 20102010`. Its 4 rows are the only ones without dates.

## Institutes

- `RESULTADO` rule implemented but no row matches "Resultado", "TSE" or "Eleição". The table contains no election-result row. The latest poll is dated 1 October 2010 (Vox Populi), two days before the first round on 3 October. The page has no result row.

## Self-check results

- Polls: 85 (turno 1), 364 CSV rows (about 4.3 values per poll, since Marina and Ciro/Heloísa are missing in some polls).
- pct sums per poll: range 94.2 to 102.0. Polls outside 90-110: 0 of 85.
- Date range (data_inicio): 2008-03-27 to 2010-10-01.
- Top institutes by polls: Vox Populi 40, Datafolha 21, Ibope 15, Sensus 9.
- Spot checks against raw lines 224, 444 and 534 matched exactly (values, institute, dates).
