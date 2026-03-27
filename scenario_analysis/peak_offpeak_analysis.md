# Peak/Off-Peak Analysis — Review Notes

Critical review of `peak_offpeak_analysis.ipynb` conducted via structured adversarial debate (2 PRO agents, 2 CONTRA agents, 1 judge). Date: 2026-03-25.

## Section Verdicts

### A. Peak-Offpeak Spread — Verdict: SOLID (with conditions)

**Strengths:**
- Inverted spread (offpeak > peak in all 432 scenarios) is a striking, policy-relevant finding
- R² = 0.752 is strong for cross-scenario regression
- bat_duration being non-significant is itself informative (capacity matters more than duration)
- Gas price as strongest predictor (β = −0.062) is well-identified

**Weaknesses:**
- No robustness check with shifted peak window (e.g. 09-21 or residual-load-based definition)
- Some overlap with spread findings already in sensitivity_analysis.ipynb
- Missing interaction terms (bat_scale × gas_price)

**Possible improvement:** Add one robustness cell testing spread with shifted window (e.g. 09-21, 10-22) to show the inversion is not an artifact of the 08-20 cutoff.

### B. Technology Capture Rates — Verdict: STRONGEST SECTION

**Strengths:**
- Solar capture rate 0.60 → 0.72 with bat_scale is a genuine, well-identified contribution
- Quantifies the anti-cannibalization mechanism that literature discusses only qualitatively
- 3×3 heatmaps per carrier show all scenario dimensions clearly

**Weaknesses:**
- Battery capture ratio of 1.8–2.3 is inflated by LP perfect foresight (real-world: 1.2–1.5)
- No confidence intervals or bootstrap bands on capture rate estimates
- No LCOE benchmark to anchor economic interpretation

**Applied fix:** Added explicit LP perfect-foresight caveat in Summary with real-world benchmark range (1.2–1.5, Staffell & Rustomji 2016).

### C. Peak vs Off-Peak Tail Dependence — REMOVED

Section C was removed from the notebook after review. While bootstrap CI confirmed that the sign reversal (peak λ_U down, offpeak λ_U up) was statistically real (CIs did not overlap), the practical significance was negligible:
- R² = 0.003 (peak) and 0.011 (offpeak) — scenario parameters explain essentially nothing
- Effect size: 2–4 percentage points across an 8× battery scaling
- 99.7% of λ_U variability is driven by corridor identity and climate year, not battery parameters

The finding was conceptually interesting (explaining the null result from price_dependence_analysis.ipynb) but did not add substantive analytical value to the thesis.

## Design Decisions

**CO₂ price not visualized:** CO₂ is a scenario parameter (80, 113.4, 140 EUR/tCO₂) and appears in regressions where it is statistically significant but small (spread β = −0.010 vs gas β = −0.062, ~6× weaker). Adding CO₂ to heatmaps would require either 27 panels (3×3×3) or tripling the number of figures, neither of which is justified by the small effect size. CO₂ is aggregated over in all visualizations.

## Consensus Points (Both Sides Agreed)

- HAC with maxlags=10 is standard and appropriate
- 08-20 peak definition is defensible for EPEX comparability with literature
- Solar capture rate is the notebook's strongest contribution
- Battery capture ratio needs LP perfect-foresight caveat (added)

## Overall Rating (after Section C removal)

| Criterion | Score | Notes |
|---|---|---|
| Methodological rigor | 7/10 | Sections A–B are solid, LP caveat addressed |
| Novelty | 7/10 | Inverted spread + solar anti-cannibalization are genuine contributions |
| Presentation quality | 7/10 | Coherent narrative, good 3×3 heatmaps showing all dimensions |

## Verdict

The notebook is **sufficient for a master's thesis** with two focused sections. Section A demonstrates that the traditional peak/offpeak price structure inverts under 2030 high-solar conditions. Section B quantifies how batteries reduce solar price cannibalization and maintain arbitrage value. Together they tell a clear story about battery impact on temporal price structure.
