"""
run_baseline.py
===============
Builds the baseline TYNDP 2030 network for climate year 2009 and saves it
to networks/baseline.nc.

Run from the project root:
    python scenarios/run_baseline.py
"""

from pathlib import Path

from build_network import build_network
from load_network_data import load_network_data

# Paths
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "open-tyndp"
TYNDP_DIR = ROOT / "data" / "tyndp2024"
OUT_DIR = ROOT / "scenarios" / "networks"
OUT_DIR.mkdir(exist_ok=True)

# Load all input data for CY 2009
data = load_network_data(
    data_dir=DATA_DIR,
    tyndp_dir=TYNDP_DIR,
    climate_year=2009,
    gas_price=None,  # use values from technologies_2030.csv
    co2_price=None,  # use values from technologies_2030.csv
)

# # ---------------------------------------------------------------------------
# # Diagnostic dump — inspect loaded data before building
# # ---------------------------------------------------------------------------
# DEBUG_DIR = ROOT / "scenarios" / "debug"
# DEBUG_DIR.mkdir(exist_ok=True)

# data["wind_onshore"].describe().to_csv(DEBUG_DIR / "wind_onshore_stats.csv")
# data["wind_offshore"].describe().to_csv(DEBUG_DIR / "wind_offshore_stats.csv")
# data["solar_utility"].describe().to_csv(DEBUG_DIR / "solar_utility_stats.csv")
# data["solar_rooftop"].describe().to_csv(DEBUG_DIR / "solar_rooftop_stats.csv")
# data["electricity_demand"].describe().to_csv(DEBUG_DIR / "demand_stats.csv")
# data["hydro_ror"].describe().to_csv(DEBUG_DIR / "hydro_ror_stats.csv")

# # First week of each profile so we can see actual time-series shape
# data["wind_onshore"].head(168).to_csv(DEBUG_DIR / "wind_onshore_week1.csv")
# data["solar_rooftop"].head(168).to_csv(DEBUG_DIR / "solar_rooftop_week1.csv")
# data["solar_utility"].head(168).to_csv(DEBUG_DIR / "solar_utility_week1.csv")
# data["electricity_demand"].head(168).to_csv(DEBUG_DIR / "demand_week1.csv")

# # Technologies and capacities
# data["technologies"].to_csv(DEBUG_DIR / "technologies.csv", index=False)
# data["capacities"].to_csv(DEBUG_DIR / "capacities.csv", index=False)

# print(f"Debug CSVs written to {DEBUG_DIR}/")
# print(
#     f"  solar_rooftop mean across all buses: {data['solar_rooftop'].mean().mean():.4f}  (expect ~0.08-0.12)"
# )
# print(
#     f"  solar_utility mean across all buses: {data['solar_utility'].mean().mean():.4f}  (expect ~0.10-0.15)"
# )
# print(
#     f"  wind_onshore  mean across all buses: {data['wind_onshore'].mean().mean():.4f}  (expect ~0.25-0.35)"
# )

# Build network from loaded DataFrames
n = build_network(
    data=data,
    battery_scale=1.0,
    ntc_scale=1.0,
    load_scale=1.0,
    battery_extendable=False,
    slack_cost=3_000.0,
    output_path=str(OUT_DIR / "baseline.nc"),
)

# ---------------------------------------------------------------------------
# Consistency check
# ---------------------------------------------------------------------------
print("\nRunning consistency check...")
n.consistency_check()
print("Consistency check passed.")
