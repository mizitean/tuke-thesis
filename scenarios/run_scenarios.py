"""
run_scenarios.py
================
Generates all sensitivity-analysis network files from the parameter grid
defined in sensitivity_analysis.md.

Networks are saved to scenarios/networks/ as unsolved .nc files, ready for
Gurobi optimisation on the server.  A manifest CSV is written to
scenarios/networks/manifest.csv and updated after every build.

Run from the project root:
    python scenarios/run_scenarios.py              # core matrix only (90 runs)
    python scenarios/run_scenarios.py --extended   # + extended CO₂ matrix (270 runs)
    python scenarios/run_scenarios.py --dry-run    # print plan, build nothing
    python scenarios/run_scenarios.py --matrix duration   # duration sensitivity only
    python scenarios/run_scenarios.py --matrix invest     # investment runs only

Matrices:
    core      battery_scale(6) × gas_price(5) × climate_year(3)  = 90 runs
    extended  core + CO₂ price variation                          = 270 runs
    duration  battery_duration(4) × battery_scale(4), CY2009      = 16 runs
    invest    battery extendable, varied gas/CY                   =  5 runs

Performance note: PECD + hydro + demand loading is the expensive step (~2–5 min
per climate year).  Scenarios are batched by climate year so that load happens
once per CY, not once per scenario.
"""

from __future__ import annotations

import argparse
import copy
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_network import (
    _aggregate_storage,
    build_network,
    STORAGE_CARRIERS,
)  # noqa: E402
from load_network_data import _apply_gas_co2_prices, load_network_data  # noqa: E402

DATA_DIR = ROOT / "data" / "open-tyndp"
TYNDP_DIR = ROOT / "data" / "tyndp2024"
OUT_DIR = ROOT / "scenarios" / "networks"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ===========================================================================
# Parameter grids — values from sensitivity_analysis.md
# ===========================================================================

# Core matrix
BATTERY_SCALES = [1, 2, 4, 6, 8, 10]
GAS_PRICES = [20, 35, 50, 70, 100]  # EUR/MWh_th
CLIMATE_YEARS_CORE = [2003, 2009, 2012]

# Fixed baseline values used in the core matrix
CO2_BASE = 113.4  # EUR/tCO₂  — TYNDP 2024 / ERAA 2023 aligned assumption
LOAD_SCALE_BASE = 1.0
NTC_SCALE_BASE = 1.0

# Extended CO₂ variation (only additional levels; CO2_BASE is already in core)
CO2_PRICES_EXTENDED = [85, 150]  # EUR/tCO₂  (100 handled by core)

# Battery duration sensitivity
# (run at gas=50, CY2009, battery_scales below to keep total manageable)
BATTERY_DURATIONS = [1.0, 1.5, 2.0, 4.0]  # hours
BATTERY_SCALES_DURATION = [1, 2, 4, 6]  # subset for duration sensitivity
DURATION_GAS = 50
DURATION_CY = 2009

# Investment runs
INVESTMENT_CONFIGS = [
    dict(gas_price=20, climate_year=2009),
    dict(gas_price=50, climate_year=2009),
    dict(gas_price=100, climate_year=2009),
    dict(gas_price=50, climate_year=2003),
    dict(gas_price=50, climate_year=2012),
]


# ===========================================================================
# Helpers
# ===========================================================================


def _tag(
    battery_scale: int | float,
    gas_price: int | float,
    climate_year: int,
    co2_price: float = CO2_BASE,
    battery_duration: float | None = None,
    extendable: bool = False,
) -> str:
    """Build a short, filesystem-safe scenario identifier."""
    parts = [f"bat{battery_scale}x", f"gas{int(gas_price)}", f"cy{climate_year}"]
    if co2_price != CO2_BASE:
        parts.append(f"co2_{int(co2_price)}")
    if battery_duration is not None:
        parts.append(f"dur{battery_duration:.1f}h".replace(".", "p"))
    if extendable:
        parts.append("invest")
    return "_".join(parts)


def _battery_override_df(
    capacities: pd.DataFrame,
    battery_scale: float,
    battery_duration: float,
) -> pd.DataFrame:
    """
    Build a battery_override DataFrame for build_network() that sets every
    bus to (p_nom_mw = PEMMDB_p_nom × battery_scale, duration_h = battery_duration).
    """
    storage_raw = capacities[capacities["pypsa_carrier"].isin(STORAGE_CARRIERS)].copy()
    agg = _aggregate_storage(storage_raw)
    bat = agg[agg["carrier"] == "battery"].copy()
    if bat.empty:
        return pd.DataFrame(columns=["bus", "p_nom_mw", "duration_h"])
    return pd.DataFrame(
        {
            "bus": bat["bus"].values,
            "p_nom_mw": bat["p_nom"].values * battery_scale,
            "duration_h": battery_duration,
        }
    )


def _build_one(
    base_data: dict,
    gas_price: float,
    co2_price: float,
    battery_scale: float,
    load_scale: float,
    ntc_scale: float,
    battery_duration: float | None,
    nuclear_scale: float,
    battery_extendable: bool,
    out_path: Path,
) -> None:
    """Apply price adjustments, build network, export to out_path."""

    # Price-adjusted data (cheap copy — only technologies DataFrame differs)
    data = copy.copy(base_data)
    data["technologies"] = _apply_gas_co2_prices(
        base_data["technologies"].copy(), gas_price, co2_price
    )

    # Optional: battery duration override
    bat_override = None
    bat_scale_arg = battery_scale
    if battery_duration is not None:
        bat_override = _battery_override_df(
            data["capacities"], battery_scale, battery_duration
        )
        bat_scale_arg = 1.0  # p_nom already baked into override

    # Optional: nuclear availability scaling
    nuc_profiles = None
    if nuclear_scale != 1.0:
        nuc_profiles = (data["nuclear_profiles"] * nuclear_scale).clip(0.0, 1.0)

    build_network(
        data=data,
        battery_scale=bat_scale_arg,
        battery_override=bat_override,
        nuclear_p_max_pu=nuc_profiles,
        load_scale=load_scale,
        ntc_scale=ntc_scale,
        battery_extendable=battery_extendable,
        output_path=str(out_path),
    )


# ===========================================================================
# Scenario assembly
# ===========================================================================


def _assemble_scenarios(
    include_extended: bool, matrix_filter: str | None
) -> list[dict]:
    """Return the full list of scenario parameter dicts."""
    scenarios: list[dict] = []

    def add(
        tag,
        climate_year,
        gas_price,
        co2_price,
        battery_scale,
        load_scale,
        ntc_scale,
        battery_duration,
        nuclear_scale,
        battery_extendable,
        matrix,
    ):
        scenarios.append(
            dict(
                tag=tag,
                climate_year=climate_year,
                gas_price=gas_price,
                co2_price=co2_price,
                battery_scale=battery_scale,
                load_scale=load_scale,
                ntc_scale=ntc_scale,
                battery_duration=battery_duration,
                nuclear_scale=nuclear_scale,
                battery_extendable=battery_extendable,
                matrix=matrix,
            )
        )

    # Core
    if matrix_filter in (None, "core", "extended"):
        for cy in CLIMATE_YEARS_CORE:
            for gas_p in GAS_PRICES:
                for bat_s in BATTERY_SCALES:
                    add(
                        tag=_tag(bat_s, gas_p, cy),
                        climate_year=cy,
                        gas_price=gas_p,
                        co2_price=CO2_BASE,
                        battery_scale=bat_s,
                        load_scale=LOAD_SCALE_BASE,
                        ntc_scale=NTC_SCALE_BASE,
                        battery_duration=None,
                        nuclear_scale=1.0,
                        battery_extendable=False,
                        matrix="core",
                    )

    # Extended: CO₂ variation
    if include_extended or matrix_filter == "extended":
        for cy in CLIMATE_YEARS_CORE:
            for gas_p in GAS_PRICES:
                for bat_s in BATTERY_SCALES:
                    for co2_p in CO2_PRICES_EXTENDED:
                        add(
                            tag=_tag(bat_s, gas_p, cy, co2_price=co2_p),
                            climate_year=cy,
                            gas_price=gas_p,
                            co2_price=co2_p,
                            battery_scale=bat_s,
                            load_scale=LOAD_SCALE_BASE,
                            ntc_scale=NTC_SCALE_BASE,
                            battery_duration=None,
                            nuclear_scale=1.0,
                            battery_extendable=False,
                            matrix="extended_co2",
                        )

    # Duration sensitivity
    if matrix_filter in (None, "duration"):
        for dur in BATTERY_DURATIONS:
            for bat_s in BATTERY_SCALES_DURATION:
                add(
                    tag=_tag(bat_s, DURATION_GAS, DURATION_CY, battery_duration=dur),
                    climate_year=DURATION_CY,
                    gas_price=DURATION_GAS,
                    co2_price=CO2_BASE,
                    battery_scale=bat_s,
                    load_scale=LOAD_SCALE_BASE,
                    ntc_scale=NTC_SCALE_BASE,
                    battery_duration=dur,
                    nuclear_scale=1.0,
                    battery_extendable=False,
                    matrix="duration",
                )

    # Investment runs
    if matrix_filter in (None, "invest"):
        for cfg in INVESTMENT_CONFIGS:
            add(
                tag=_tag(1, cfg["gas_price"], cfg["climate_year"], extendable=True),
                climate_year=cfg["climate_year"],
                gas_price=cfg["gas_price"],
                co2_price=CO2_BASE,
                battery_scale=1,
                load_scale=LOAD_SCALE_BASE,
                ntc_scale=NTC_SCALE_BASE,
                battery_duration=None,
                nuclear_scale=1.0,
                battery_extendable=True,
                matrix="invest",
            )

    # Assign IDs and output paths; deduplicate tags
    seen_tags: set[str] = set()
    result = []
    for i, s in enumerate(scenarios):
        if s["tag"] in seen_tags:
            continue
        seen_tags.add(s["tag"])
        s["scenario_id"] = len(result)
        s["output_file"] = str(OUT_DIR / f"{s['tag']}.nc")
        s["status"] = "pending"
        result.append(s)
    return result


# ===========================================================================
# Main builder
# ===========================================================================


def run(
    dry_run: bool = False,
    include_extended: bool = False,
    matrix_filter: str | None = None,
) -> None:
    scenarios = _assemble_scenarios(include_extended, matrix_filter)

    manifest_path = OUT_DIR / "manifest.csv"
    manifest_df = pd.DataFrame(scenarios)

    # Summary
    print("\nScenario plan:")
    print(manifest_df.groupby("matrix").size().rename("count").to_string())
    print(f"Total: {len(scenarios)} scenarios")
    print(f"Output dir: {OUT_DIR}")
    print(f"Manifest:   {manifest_path}")

    manifest_df.to_csv(manifest_path, index=False)

    if dry_run:
        print("\n[DRY RUN] Manifest written. No networks built.")
        return

    built = skipped = failed = 0
    t_start = time.time()

    # Batch by climate year to load PECD/hydro/demand data only once per CY
    for cy in sorted({s["climate_year"] for s in scenarios}):
        cy_group = [s for s in scenarios if s["climate_year"] == cy]

        print(f"\n{'='*64}")
        print(f"Climate year {cy}  —  loading PECD + hydro + demand...")
        t_load = time.time()
        try:
            base_data = load_network_data(
                data_dir=DATA_DIR,
                tyndp_dir=TYNDP_DIR,
                climate_year=cy,
            )
        except Exception as exc:
            print(f"  ERROR loading CY{cy}: {exc}")
            for s in cy_group:
                s["status"] = f"load_error: {exc}"
                failed += len(cy_group)
            continue
        print(
            f"  Loaded in {time.time() - t_load:.0f}s  ({len(cy_group)} scenarios queued)"
        )

        for s in cy_group:
            out_path = Path(s["output_file"])

            if out_path.exists():
                print(f"  SKIP  {s['tag']}")
                s["status"] = "skipped"
                skipped += 1
                manifest_df.loc[manifest_df["tag"] == s["tag"], "status"] = "skipped"
                manifest_df.to_csv(manifest_path, index=False)
                continue

            print(f"  BUILD {s['tag']}  ...", end="", flush=True)
            t1 = time.time()
            try:
                _build_one(
                    base_data=base_data,
                    gas_price=s["gas_price"],
                    co2_price=s["co2_price"],
                    battery_scale=s["battery_scale"],
                    load_scale=s["load_scale"],
                    ntc_scale=s["ntc_scale"],
                    battery_duration=s["battery_duration"],
                    nuclear_scale=s["nuclear_scale"],
                    battery_extendable=s["battery_extendable"],
                    out_path=out_path,
                )
                s["status"] = "built"
                built += 1
                print(f"  {time.time() - t1:.0f}s")
            except Exception as exc:
                s["status"] = f"error: {exc}"
                failed += 1
                print(f"  ERROR: {exc}")

            manifest_df.loc[manifest_df["tag"] == s["tag"], "status"] = s["status"]
            manifest_df.to_csv(manifest_path, index=False)

    elapsed = time.time() - t_start
    print(f"\n{'='*64}")
    print(
        f"Finished in {elapsed/60:.1f} min  —  "
        f"{built} built, {skipped} skipped, {failed} failed"
    )
    print(f"Manifest: {manifest_path}")


# ===========================================================================
# CLI
# ===========================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build TYNDP 2030 sensitivity-analysis networks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scenarios/run_scenarios.py --dry-run
  python scenarios/run_scenarios.py --matrix core
  python scenarios/run_scenarios.py --matrix duration
  python scenarios/run_scenarios.py --matrix invest
  python scenarios/run_scenarios.py --extended
        """,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print scenario plan and write manifest without building",
    )
    parser.add_argument(
        "--extended",
        action="store_true",
        help="Include extended CO₂ price matrix (adds 270 runs to core 90)",
    )
    parser.add_argument(
        "--matrix",
        choices=["core", "extended", "duration", "invest"],
        default=None,
        help="Build only a specific sub-matrix (default: core + duration + invest)",
    )
    args = parser.parse_args()

    run(
        dry_run=args.dry_run,
        include_extended=args.extended,
        matrix_filter=args.matrix,
    )
