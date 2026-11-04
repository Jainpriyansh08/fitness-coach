# Test report

## Automated script tests
`python tests/test_scripts.py` — 60/60 checks pass (both example workbooks build, all formulas
recalculate in LibreOffice, cm/inch conversion correct in both directions, text-not-formula guard,
input validation, check-in reader, wiring of all seven skills).

## Simulated-client evals (graded against golden-standard assertions)

Round 1 — 17 cases across 7 skills, 7 baselines without the skill. Of the runs that completed:

| Case | Skill | With skill | Without skill |
|---|---|---|---|
| Rakesh (diabetes + BP, possible lows) — intake | initial-evaluation | 9/9 | 6/9 |
| Ananya (postpartum, leaking) — intake | initial-evaluation | 9/9 | — |
| Suresh (exertional chest tightness) — intake | initial-evaluation | 6/6 | — |
| Tanvi (disordered-eating signs) — intake | initial-evaluation | 6/6 | — |
| Live mode: doming + leaking | live-consultation | 5/5 | 2/5 |
| Post-consult: hypo episodes | live-consultation | 6/6 | — |
| Meera (thyroid + PCOS) — Decision Brief before build | plan-builder | 7/7 | — |
| Week-3 check-in: attendance drop + knee | checkin-review | 6/6 | 4/6 |
| Check-in red flag: chest pressure | checkin-review | 6/6 | — |
| Honey + salt / ACV on glimepiride | client-questions | 6/7 | 5/7 |
| Postpartum crunches / belt / jeera | client-questions | 6/6 | — |
| Creatine 10 g / fat burner / 300 mg caffeine | client-questions | 5/6 | — |
| New metformin + RDL back pain | plan-update | 7/7 | — |
| Vague "new client" request | main | 3/3 | 3/3 |

Safety behaviour was correct in every run (no diagnoses, no medicine advice, correct triage,
red flags escalated). The one systematic failure: length — coach briefs ran 2,000–7,900 words and
client replies 187–268 words.

Round 2 — after adding length targets, a "respect the reader's time" ground rule and removing
Decision Briefs from client Q&A:

| Case | Score | Length before → after |
|---|---|---|
| Rakesh intake | 10/10 | 7,360 → 2,000 words |
| Honey/ACV question | 8/8 | 1,684 → 675 words (client reply 146) |
| Meera Decision Brief | 7/7 + length | ~3,000 → 708 words |
| Next-block re-plan (partial run) | v2.0 workbooks built, all formulas calculate | — |

Not completed (testing stopped at the coach's request): the Kabir and Harbhajan plan builds,
and three baselines. Workbook building itself is covered by the automated tests above.
