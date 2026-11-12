# Notes: 2014 presidential polls (pt.wikipedia) -> polls_2014.csv

## Sources fetched (action=raw, UA election-data-research/1.0)
- `raw/page.wikitext` (81 lines): main page "Pesquisas de opinião para a eleição presidencial no Brasil em 2014". It contains no wikitable. It transcludes two templates under `== Primeiro turno ==` (line 67) and `== Segundo turno ==` (line 70).
- `raw/t1.wikitext` (816 lines): template "Pesquisas de opinião da Eleição presidencial no Brasil em 2014 (1º turno)", fetched as `Predefinição:` title. Holds the first-round table.
- `raw/t2.wikitext` (151 lines): template "... (2º turno)", fetched the same way. Holds the second-round table.
- `linha_wiki` therefore points to `t1.wikitext:N` or `t2.wikitext:N` (line of the `!N` row cell in the template file), not to page.wikitext. Refs were blanked with their newlines kept, so these line numbers match the raw files exactly (spot-checked).

## Tables parsed
| file | secao | turno | body rows (= polls) | candidate columns | cenario |
|---|---|---|---|---|---|
| t1 | Primeiro turno | 1 | 44 | 11 (Dilma, Marina, Aécio, Everaldo, Genro, Eduardo Jorge, Eymael, Levy, Iasi, José Maria, Rui Costa) + Brancos/Nulos + Indecisos | "" (one ballot) |
| t2 | Segundo turno | 2 | 15 | 2 (Dilma Rousseff, Aécio Neves) + Brancos/Nulos + Indecisos | "Dilma Rousseff x Aécio Neves" |

Output: 526 rows for turno 1 (44 polls) and 60 rows for turno 2 (15 polls), 586 rows total. Poll dates run 2014-02-13 to 2014-10-25. Only four institutes appear: Datafolha 21, Ibope 19, Vox Populi 12, CNT/MDA 7.

No table or row was skipped. The 46 cells with `{{n/a}}` were not emitted, since they are not values.

## Column decisions
- `tipo`, `contratante`, `amostra`, `registro_tse`: empty. The tables have no such columns; no TSE numbers appear in the table cells.
- `margem_erro_pp`: "±2,2%" -> 2.2. The margin is the same for all candidates in a poll.
- `candidato`: column header kept verbatim, including the party in parentheses (e.g. "Dilma Rousseff (PT)").
- "Branco ou Nulo" (combined column in both tables) -> `Brancos/Nulos`.
- "NS ou NR" (Não soube ou não respondeu) -> `Indecisos`. This is a judgement call: it is the non-response/undecided share, not literally indecisos. Rename in the CSV if you prefer "NS/NR".
- Templates `{{yes1|}}`, `{{yes2|}}`, `{{no1|}}`, `{{no2|}}` are unwrapped to their value. Their CSS classes were ignored, and columns were matched by position only.
- Dates: no year in the tables, all polls are 2014 (2014 assumed). Cross-month ranges handled ("29 de setembro a 01 de outubro" -> 2014-09-29 to 2014-10-01). Every date parsed; none left empty.
- The 'N' poll-number column (wiki row index !1..!44 / !1..!15) is not an output column. It is recoverable from the `linha_wiki` line.

## Ambiguities and known problems
1. Values are intention figures as shown in the table. Several citations in the wiki (e.g. Ibope 3-4 Oct: "votos válidos: Dilma 46%") quote valid-vote shares, while the table uses different values (40/21/24 for the same poll). The table does not state the base, so the CSV does not state it either.
2. Sums outside 90-110 (self-check, 7 of 59 poll groups; range 85-115):
   - Five pre-August polls sum to 85-89 (Ibope 13-15 Jun, Ibope 4-7 Jun, Datafolha 3-5 Jun, Ibope 15-19 May, Datafolha 7-8 May; lines 598, 616, 634, 670, 688). In these polls Marina is NA, and no other column covers that share. The table has no column for Eduardo Campos (the PSB candidate before his replacement by Marina Silva). Inference, not stated on the page: the missing share is likely Campos's.
   - Two polls sum above 110: Datafolha 2-3 Apr (line 742, sum 115) and Datafolha 19-20 Feb (line 778, sum 112). In both, the Marina column is populated (27% and 23%) while the others are unchanged. I could not explain these from the wiki; the values are reported as written.
3. Scenarios: the wiki does not label them. Marina's column is blank in rows before about 14 Aug and filled after, which looks like the Campos/Marina switch, but no scenario label exists. Left empty, as instructed.
4. The second-round table has only one matchup, so `cenario` holds it.
5. No `Resultado`/TSE/official-result row exists in either table. No `RESULTADO` rows were emitted.

## Self-check
- Sums per poll (turno + linha_wiki): 59 groups; 52 within 90-110; 7 outside (see point 2). All second-round sums are within range.
- Spot checks against raw files (random sample): `t1.wikitext:472` Ibope 23-25 Aug, Eymael 0%; `t1.wikitext:220` Vox Populi 23-24 Sep, Brancos/Nulos 7%; `t1.wikitext:580` Datafolha 1-2 Jul, Eduardo Jorge 1%. All matched the raw lines.
