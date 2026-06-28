# RTA budget — primary-source receipt

`budget_source.csv` is transcribed verbatim from the Regional Transportation
Authority's adopted budget. Every figure below is quoted exactly from the source;
no figure is estimated, interpolated, or derived. The source PDF is committed
beside this file as the literal receipt.

## Citation

- **Document:** Regional Transportation Authority, *Adopted 2025 Operating Budget,
  Two-Year Financial Plan, and Five-Year Capital Program*.
- **Table:** Table 2, "Statement of Regional Revenues and Expenses (in thousands)",
  **Service Board Expenses** rows (PDF p.18).
- **URL:** https://www.rtachicago.org/uploads/files/general/Transit-Funding/2025Budget/2025_RegionalBudgetAdopted.pdf
- **Local receipt:** `2025_RegionalBudgetAdopted.pdf`
- **Accessed:** 2026-06-27

## Quoted figures (Service Board Expenses, $ thousands)

| Service board | 2023 Actual | 2024 Estimate | 2025 Budget | 2026 Plan | 2027 Plan |
|---|--:|--:|--:|--:|--:|
| CTA | 1,710,707 | 1,916,577 | 2,156,522 | 2,233,972 | 2,313,943 |
| Metra | 911,700 | 1,005,000 | 1,135,000 | 1,165,000 | 1,150,000 |
| Pace | 267,663 | 299,805 | 339,297 | 451,810 | 473,950 |
| ADA Paratransit | 237,349 | 261,340 | 281,231 | 293,636 | 308,349 |
| **Total Service Board Expenses** | **3,127,419** | **3,482,722** | **3,912,051** | **4,144,418** | **4,246,242** |

`parse_rta_budget` reconciles the per-board rows against the printed
**Total Service Board Expenses** line each year (±2k for the document's own
rounding). **Pace operates Regional ADA Paratransit**, so the loader folds the
ADA Paratransit line into `pace`.

## Column meaning (the `kind` tag)

The RTA presents one adopted column per fiscal year: `2023 Actual`, `2024 Estimate`,
`2025 Budget`, then `2026`/`2027 Plan`. These are *not* all "budget" — only 2025 is
the adopted budget. The `kind` column preserves each year's true nature so the UI
never mislabels an estimate or a plan as an actual or a budget.
