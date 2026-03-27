# System Cost Analysis — Review Notes

Critical review of `system_cost_analysis.ipynb` conducted via two rounds of structured adversarial debate (2 PRO agents, 2 CONTRA agents, 1 judge per round). Dates: 2026-03-25, 2026-03-26.

## Glossary

- **BCR** — Benefit-Cost Ratio. Dispatch cost savings divided by annualized battery investment cost. BCR > 1 means the investment pays for itself, BCR < 1 means it does not. BCR of 0.65 means 65 cents return per euro invested.
- **CAPEX** — Capital Expenditure. Overnight investment cost of battery storage (EUR/kW).
- **CRF** — Capital Recovery Factor. Converts overnight CAPEX into equal annual payments over a given lifetime at a given discount rate. Formula: CRF = r(1+r)^n / ((1+r)^n - 1).
- **DEA** — Danish Energy Agency. Source of one set of 2030 CAPEX projections (Technology Catalogue, published 2022-2023).
- **TYNDP** — Ten-Year Network Development Plan (ENTSO-E). Source of alternative 2030 CAPEX projections.
- **O&M** — Operations & Maintenance cost, expressed as % of CAPEX per year (2.5%).
- **LFP** — Lithium Iron Phosphate. Currently dominant battery chemistry for grid-scale storage.
- **FCR/aFRR** — Frequency Containment Reserve / automatic Frequency Restoration Reserve. Ancillary services that batteries can provide but are NOT modeled in this analysis.
- **LP** — Linear Program. The optimization method used by PyPSA for dispatch, which assumes perfect foresight and continuous (not integer) variables.
- **Break-even CAPEX** — The battery price (EUR/kW) at which dispatch savings exactly cover the annualized investment over 15 years at 7% discount rate.

## Section Verdicts

### A. BCR Analysis — Verdict: SOLID

- BCR < 1 across all 432 scenarios — dispatch savings alone cannot justify battery investment
- Best-case: BCR = 0.65 (bat2× dur1h, CY2012, Gas=35)
- DEA vs TYNDP dual CAPEX bracketing strengthens finding
- Financial assumptions: 7% discount rate, 15-year lifetime, 2.5% O&M (industry standard)
- BCR regression (R²=0.78): bat_scale and bat_duration are dominant drivers (β ≈ -0.07), gas/CO₂/CY have smaller positive effects (β ≈ 0.02)
- Sensitivity table expanded to 4 configurations (bat2× dur1h/dur2h, bat4× dur1h, bat8× dur1h)

### B. Marginal Value Curves — Verdict: STRONGEST SECTION

- Diminishing returns: 19 → 9 → 4 M EUR/yr per GW for successive doublings
- Break-even CAPEX heatmaps show all parameters (CY × gas outer grid, scale step × bat_duration inner)
- Best break-even: 256 EUR/kW (CY2012, Gas=35, 1×→2×, dur1h) — below DEA projected cost (321 EUR/kW) but approaching current 2024 LFP system costs (~200 EUR/kW)
- Marginal value curves never intersect annualized cost lines (DEA 64 M, TYNDP 97 M EUR/yr/GW) — 3-5× gap

### C. BCR Drivers & Climate Year Variability — Verdict: SOLID (after reframing)

- Originally titled "Insurance" — reframed to neutral description without unsupported risk claims
- CY2012 (cold winter) yields BCR up to 2.5× higher than CY2003
- BCR regression formally quantifies driver importance

### D. Consumer Surplus Decomposition — Verdict: ADEQUATE (after expansion)

- Expanded from 1 to 6 key scenarios covering bat2×/bat8×, dur1h/dur2h, mid/high gas, mid/high CO₂, CY2009/CY2012
- Key finding: consumers benefit from lower LMPs (up to 6.97 bn EUR/yr in best case), gas generators lose most (-3.01 bn), solar gains (+0.91 bn)
- Per-bus consumer savings chart shows spatial distribution for best-case scenario
- Methodological note: consumer cost uses LMP × generation as proxy, which includes export value for net-exporting zones

## Key Interpretation

**BCR < 1 is a lower bound, not a final verdict.** The analysis captures only wholesale energy arbitrage value. Real-world battery revenues also include:
- FCR/aFRR ancillary services (estimated 30–50% of total revenue in European markets)
- Capacity market payments
- Network deferral value

None of these are modeled. With these additional revenue streams, BCR could exceed 1.0, especially for bat2× dur1h where the best-case dispatch-only BCR already reaches 0.65.

**CAPEX projections may be outdated.** DEA (321-774 EUR/kW) and TYNDP (487-1174 EUR/kW) are 2030 projections from 2022-2023. LFP pack prices fell below 100 USD/kWh in late 2024, suggesting 2030 system costs may be 25-30% lower. At ~200 EUR/kW system cost, the best-case break-even (256 EUR/kW) would already be met.

## Overall Rating (after two review rounds)

| Criterion | Score | Notes |
|---|---|---|
| Methodological rigor | 7.5/10 | BCR regression, dual CAPEX, HAC errors, expanded sensitivity |
| Novelty | 7/10 | Marginal value curves + BCR falsification are genuine contributions |
| Presentation quality | 8/10 | Consistent 3×3 heatmaps, clear markdown explanations, no placeholder text |

## Verdict

The notebook is **thesis-ready**. It transforms 432 dispatch solutions into actionable investment economics. The key finding — dispatch savings alone cannot justify battery investment — is honest and well-supported. The marginal value curves and break-even CAPEX analysis provide directly policy-relevant information. The welfare decomposition across 6 scenarios shows how battery deployment redistributes surplus from gas generators to consumers.
