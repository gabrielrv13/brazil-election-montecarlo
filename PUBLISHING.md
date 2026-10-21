# Publishing the Runoff Forecast

Checklist for publishing the second-round forecast. Runoff date: 2026-10-25.

## Timeline

| Date | Step |
|---|---|
| Oct 21-22 | Run `python src/retrospectiva_1t.py`; record the suggested bias in the PR description |
| Oct 23 | Add the latest runoff polls to `data/pesquisas_2turno.csv`; open the PR with the v2.10 changes |
| Oct 24 (morning) | Final run, gate, tag, post |
| Oct 25 | No new forecast; answer questions about methodology only |
| Oct 26 onward | Retrospective against the official result (calibration report) |

## 1. Final run

```bash
python src/simulation_2turno.py --csv data/pesquisas_2turno.csv
```

Defaults: all polls, tau = 7 days, sd of the two-party share = 2.5 pp, bias = 0.

Record in the PR description:

- number of polls and effective sample size (printed under "SECOND ROUND POLL AGGREGATION");
- P(win) for the base case and for `--data-min 2026-10-08` (post-first-round polls only);
- the suggested bias from `retrospectiva_1t.py`, shown as a sensitivity row. The base case keeps `--vies 0`: it comes from a single election.

## 2. Publication gate

```bash
python src/publicar_2turno.py
```

The command exits with code 1 and writes nothing when:

- `outputs/resumo_2turno.json` is older than 36 hours (`--max-horas` changes the limit);
- required fields are missing, or the win probabilities do not add up to 100%;
- the methodology disclaimer is absent from the generated text.

Outputs: `outputs/post_2turno_pt.md` and `outputs/post_2turno_en.md`.

## 3. Review before posting

- [ ] `pytest` passes (CI green on the release branch)
- [ ] Probabilities in the text match the console report
- [ ] Image attached: `outputs/simulacao_2turno.png`
- [ ] Texts state the sd, the number of polls and the date of the run
- [ ] Wording describes what the data shows. No endorsement, no "will win"
- [ ] The post links to the repository and to the methodology section of the README

## 4. Release (hotfix path)

The runoff model lives in the legacy `src/` layout, so the release goes through `main` and is merged back into `develop`.

```bash
git checkout main && git pull origin main
git checkout -b feat/runoff-calibrated-sd
# copy the v2.10 files, then:
git add src/simulation_2turno.py src/retrospectiva_1t.py src/publicar_2turno.py \
        tests/test_runoff_calibration.py tests/test_retrospectiva_1t.py \
        tests/test_publicar_2turno.py README.md PUBLISHING.md CHANGELOG.md
git commit -m "feat(runoff): aggregate runoff polls on two-party share with explicit sd"
git push origin HEAD
# open PR to main; after merge:
git checkout main && git pull origin main
git tag -a v2.10.0 -m "v2.10.0 - Calibrated runoff and publication step"
git push origin v2.10.0
git checkout develop && git merge main
```

## 5. Channels

1. r/brasil and r/dataisbeautiful: the semicircle image plus the methodology comment (the generated text). Post after a major poll release.
2. GitHub release notes for `v2.10.0`: paste the English text.

## 6. After the result

1. Compare the published probability and share with the official result.
2. Run the 1T retrospective logic on the runoff: error of the two-party share by averaging window.
3. Add the 2026 first and second rounds to `data/historico/` for the v3.4.0 calibration report.

## Rules

- Never post a forecast without the disclaimer.
- Do not post if the gate fails. Rerun the simulation instead of editing the JSON.
- Do not engage with partisan framing. The model outputs probabilities, not endorsements.
