# 2010 Brazilian presidential election: second-round polls from English Wikipedia

## Source
- Page: https://en.wikipedia.org/wiki/Opinion_polling_for_the_2010_Brazilian_presidential_election
- Raw wikitext: `raw/page.wikitext` (1017 lines, fetched with curl, UA `election-data-research/1.0`).
- No transcluded sub-pages or templates hold the tables. The runoff table is inline on the page, so nothing else was fetched.

## Tables found (3 wikitables)
| start line | section | used |
|---|---|---|
| 2 | (none, candidates overview) | no (not a poll table) |
| 35 | Polls > First round | no (first round) |
| 852 | Polls > Second round | yes: 19 rows of polls plus the official result (21 `|-` rows including 2 header rows) |

## Output
- `polls_2010_2t.csv`: 57 rows = 19 poll/result rows x 3 categories (Dilma Rousseff, José Serra, Abstenção/Indecisos).
- Matchup: "Dilma Rousseff x José Serra" (the only runoff matchup on the page; no hypothetical runoffs such as Dilma vs Marina appear in the second-round section).

## Deviations and ambiguities
1. **Combined column.** The header is "Abst. / Undec." (one column). It is labelled `Abstenção/Indecisos`, not `Abstenção` or `Indecisos`, because the source does not separate them. There are no separate Blank/Null columns.
2. **Missing fields.** The table has no sample size (`amostra`), margin of error, contratante, tipo or TSE registration, so those columns are empty for every row.
3. **Years.** Dates in the table have no year ("29–30 Oct"). Year 2010 is assumed from the page's title and election. Ranges are read as same-month ranges (for example "29–30 Oct" -> 2010-10-29 to 2010-10-30). No date was unparseable.
4. **Result row.** The "2010 election" row is kept with `instituto = RESULTADO`, dated 2010-10-31 (election day). Its figures are 56.05 / 43.95 / 6.70. The 6.70 abstention figure is on a different base (share of electorate), so its row sums to 106.7, which is still inside 90–110.
5. **Lead column** ignored, as specified.
6. **Unit.** The CNT/Sensus row for 11–13 Oct gives its abstention figure as "10.5" with no % sign. It is taken as 10.5.
7. **linha_wiki** is the line of the `|-` that starts each row. The first data cell is on the line after it.
8. **Section heading chain** is written as "Polls > Second round" (joined with " > ").

## Self-check (`check.py`)
- Sums per poll (all three categories): 18 polls sum to exactly 100.00; the RESULTADO row sums to 106.70. None are outside 90–110.
- Polls per matchup: 19 (one matchup).
- Date range (data_inicio): 2010-10-08 to 2010-10-31. Unparseable dates: 0.
- Institutes by poll count: Datafolha 6, Vox Populi 4, CNT/Sensus 4, Ibope 4, RESULTADO 1.
- Spot checks (random seed 7) matched the raw lines: CNT/Sensus 23–25 Oct at line 918 (51.9 / 36.7 / 11.4); Datafolha 28 Oct at line 890 (Serra 40); Datafolha 21 Oct at line 932 (Abst/Ind 10). The line numbers point at the `|-` line that starts each row.

## Known limits
- The table itself gives only fieldwork dates and percentages. Rows were not cross-checked against any external source.
- The Ibope "17–20 Oct" poll (line 946) overlaps the 20 Oct cut-off. It is kept in the late-October list because its fieldwork ends on 20 Oct.
