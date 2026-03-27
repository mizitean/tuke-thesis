# Sensitivity Analysis — Review Notes

Critical review of `sensitivity_analysis.ipynb` conducted via structured adversarial debate (2 PRO agents, 2 CONTRA agents, 1 judge). Date: 2026-03-26.

## Overview

Main analysis notebook of the thesis. 22 sections, 69 cells. Covers ANOVA, OLS regression, quantile regression, SHAP/LightGBM, merit order displacement, battery arbitrage, spatial analysis, and more.

## Glossary

- **ANOVA** — Analysis of Variance. Decomposes total variance into between-group (parameter effect) and within-group (residual) components. Used here as eta-squared (SS_between / SS_total).
- **OLS** — Ordinary Least Squares regression. Linear model estimating how each parameter affects LMP/CV.
- **Quantile regression** — Estimates parameter effects at different quantiles (τ=0.1, 0.5, 0.9) rather than the mean. Shows whether batteries help more in normal vs extreme scenarios.
- **SHAP** — SHapley Additive exPlanations. Decomposes LightGBM predictions into per-feature contributions, capturing non-linear effects and interactions.
- **std** — Standard deviation. Measures absolute price volatility in EUR/MWh — how much hourly LMP prices deviate from their annual mean.
- **CV** — Coefficient of Variation (std/mean). Measures relative volatility — normalizes std by the mean so that scenarios with different price levels are comparable.
- **R²** — R-squared. How much of the variability in the dependent variable is explained by the model. R²=0.30 means the model explains 30%. R²=1.0 would be perfect prediction.
- **β (beta)** — Regression coefficient. How much the metric changes when a parameter increases. β = -0.36 for bat_scale on CV means: more batteries → CV decreases. Larger negative number = stronger effect. In standardized form, betas are comparable across parameters with different scales.
- **τ (tau)** — Quantile level in quantile regression. τ=0.1 = bottom 10% of scenarios (least volatile), τ=0.9 = top 10% (most volatile). Shows whether parameter effects differ between normal and extreme scenarios.
- **DE00** — Germany bidding zone. Used as primary zone in many sections.

## How Volatility Is Measured

For each of the 432 scenarios, volatility is computed from the 8760 hourly LMP prices of DE00:

1. **std** = standard deviation of 8760 hourly prices within that scenario
2. **mean** = average of 8760 hourly prices within that scenario
3. **CV = std / mean** — the main volatility metric used throughout the thesis

Each scenario gets one CV number. A scenario with CV=2.5 is more volatile than one with CV=1.5. The 432 CV values are then analyzed to determine which scenario parameters (bat_scale, gas_price, etc.) drive volatility up or down.

Additional metrics: **spike_hours** (count of hours where LMP > 150 EUR/MWh) and **zero_hours** (count of hours where LMP < 1 EUR/MWh) capture tail behavior that CV alone misses.

## Rating

| Criterion | Score | Notes |
|---|---|---|
| Methodological rigor | 6/10 | Triangulation is genuine but OLS R²=0.30 underexplored, SHAP hyperparams unjustified |
| Novelty | 7/10 | Quantile regression on LMP volatility in TYNDP context is uncommon, CY2012 paradox interesting |
| Presentation quality | 4/10 | 22 sections without synthesis, copy-paste redundancy, DE00 tunnel vision, fixed-param plots |

## Key Issues Identified

### 1. Notebook too long (22 sections)
Both sides agreed the notebook is bloated. Battery arbitrage sections (S7, S8, S8b, S10, S10b, S21) are dispatch analysis, not sensitivity analysis. Merit order (S22) and SOC patterns (S21) could be separate notebooks.

### 2. Copy-paste redundancy
- S8 (EU-wide battery buy/sell) + S8b (DE00 only) — identical logic, different zone filter
- S10 (EU-wide charging profiles) + S10b (DE00 only) — same issue

### 3. DE00 tunnel vision
14 out of 22 sections analyze only DE00. While DE00 is the largest zone and a reasonable starting point, the thesis claims 55-zone coverage. Key analyses (ANOVA, volatility metrics) should be shown EU-wide or at least validated on a second zone.

### 4. Fixed parameter subsets
Many sections fix gas=22.68 and co2=113.4, hiding how results change under different fuel prices. The 3×3 heatmap grids used in peak_offpeak_analysis and system_cost_analysis should be adopted here.

### 5. No concluding synthesis
Notebook ends abruptly after merit order plots. No summary tying findings together.

### 6. pip install in analysis notebook
Cells 1 and 54 run pip install — should be in requirements.txt.

### 7. SHAP not tuned
LightGBM uses hard-coded hyperparameters without GridSearchCV or justification.

## Consensus Points

- ANOVA→OLS→quantile→SHAP triangulation is genuine and valuable
- Quantile regression finding (β=-0.364 at τ=0.1 vs β=-0.121 at τ=0.9) is genuinely novel
- Gas reducing CV is a valid finding (higher gas raises mean faster than std)
- CY2012 paradox explained through slack analysis is a strong contribution
- Merit order displacement (gas -29.5 TWh, onwind +21.9 TWh) is well-identified
- Cross-validation for LightGBM is appropriate

## Implemented Improvements

### Round 1:
- [ ] Remove pip install cells
- [ ] Merge S8 + S8b into single section
- [ ] Merge S10 + S10b into single section
- [ ] Add concluding synthesis section
- [ ] Convert 5-7 key plots to 3×3 heatmap grids
- [ ] Add SHAP hyperparameter justification
- [ ] Add DE00 justification note

### Future work:
- [ ] Add robustness check on second zone (FR00 or PL00)
- [ ] Merge S4+S5
- [ ] Consider removing or simplifying Section 14 (Quantile Regression) — the per-bat_scale CV quantile plot (added after review) shows the same insight more directly without the aggregation problem of linear quantile regression treating bat_scale as continuous
- [ ] Consider removing or simplifying Section 16 (SHAP) — GBM R²=0.97 is expected (deterministic LP model, only 5 parameters change), SHAP dependence plots are hard to read and the feature importance ranking (climate_year > bat_scale) is already visible from simpler analyses

## Verdict

The notebook contains solid analytical work with genuine methodological triangulation. The problems are structural (too long, redundant, no synthesis) and presentational (DE00 focus, fixed params), not fundamental. Fixing presentation quality from 4/10 to 7/10 is achievable through merges, synthesis, and 3×3 heatmap conversions.
