"""
solve_scenarios.py
==================
Solves all networks listed in manifest.csv using Gurobi and saves results
to solved_networks/.

Run on the server from the project root:
    python scenarios/solve_scenarios.py
    python scenarios/solve_scenarios.py --networks-dir /path/to/networks
    python scenarios/solve_scenarios.py --tag bat2x_gas50_cy2009   # single run
    python scenarios/solve_scenarios.py --matrix core               # subset

Options:
    --networks-dir  DIR   Directory with input .nc files and manifest.csv
                          (default: scenarios/networks)
    --output-dir    DIR   Directory for solved .nc files
                          (default: solved_networks)
    --tag           TAG   Solve only the scenario with this tag
    --matrix        NAME  Solve only scenarios from this matrix
                          (core | duration | invest | extended_co2)
    --threads       N     Gurobi threads (default: 0 = auto)
    --skip-existing       Skip if solved .nc already exists (default: True)
    --force               Re-solve even if output file already exists
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd
import pypsa

ROOT = Path(__file__).resolve().parent.parent


def solve_network(
    network_path: Path,
    output_path: Path,
    threads: int = 0,
) -> dict:
    """Load, solve, and export one network. Returns a result dict."""
    result = {
        "status": "unknown",
        "termination_condition": "unknown",
        "objective": None,
        "slack_mwh": None,
        "solve_time_s": None,
    }

    # Load
    n = pypsa.Network()
    n.import_from_netcdf(str(network_path))

    # Solve
    solver_options = {
        "threads": threads,
        "Method": 2,  # Barrier (fastest for large LPs)
        "Crossover": 0,  # Skip crossover — interior-point duals are fine for LMPs
        "BarConvTol": 1e-5,  # Slightly relaxed convergence for speed
        "FeasibilityTol": 1e-5,
        "OptimalityTol": 1e-5,
        "LogToConsole": 0,  # Suppress Gurobi console output (logged to file)
        "LogFile": str(output_path.parent / f"{output_path.stem}_gurobi.log"),
    }

    t0 = time.time()
    solve_result = n.optimize(
        solver_name="gurobi",
        solver_options=solver_options,
    )
    result["solve_time_s"] = round(time.time() - t0, 1)

    # Check result
    status = n.optimization_status if hasattr(n, "optimization_status") else "unknown"
    termination = (
        n.optimization_termination_condition
        if hasattr(n, "optimization_termination_condition")
        else "unknown"
    )
    result["status"] = str(status)
    result["termination_condition"] = str(termination)

    # Objective value
    try:
        result["objective"] = float(n.objective)
    except Exception:
        result["objective"] = None

    # Slack usage — indicator of infeasibility
    if "slack" in n.generators.carrier.values:
        slack_gens = n.generators[n.generators.carrier == "slack"].index
        if slack_gens.isin(n.generators_t.p.columns).any():
            slack_p = n.generators_t.p[
                slack_gens.intersection(n.generators_t.p.columns)
            ]
            result["slack_mwh"] = round(float(slack_p.sum().sum()), 1)
        else:
            result["slack_mwh"] = 0.0

    # Export
    if str(termination).lower() in ("optimal", "suboptimal"):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        n.export_to_netcdf(str(output_path))
        result["status"] = "solved"
    else:
        result["status"] = f"failed:{termination}"

    return result


def run(
    networks_dir: Path,
    output_dir: Path,
    tag_filter: str | None,
    matrix_filter: str | None,
    threads: int,
    force: bool,
) -> None:
    manifest_path = networks_dir / "manifest.csv"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    manifest = pd.read_csv(manifest_path)

    # Apply filters
    if tag_filter:
        manifest = manifest[manifest["tag"] == tag_filter]
    if matrix_filter:
        manifest = manifest[manifest["matrix"] == matrix_filter]

    if manifest.empty:
        print("No matching scenarios found.")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    # Results tracking
    results_path = output_dir / "solve_results.csv"
    if results_path.exists():
        results_df = pd.read_csv(results_path)
    else:
        results_df = pd.DataFrame()

    total = len(manifest)
    solved = skipped = failed = 0
    t_start = time.time()

    print(f"\nSolving {total} networks")
    print(f"  Input:  {networks_dir}")
    print(f"  Output: {output_dir}")
    print(f"  Gurobi threads: {'auto' if threads == 0 else threads}")
    print()

    for i, row in manifest.iterrows():
        tag = row["tag"]
        # Ignore the path in the manifest and create a local path based on the given directory
        net_path = networks_dir / f"{tag}.nc"
        out_path = output_dir / f"{tag}.nc"

        print(f"[{solved+skipped+failed+1}/{total}]  {tag}")

        # Check input exists
        if not net_path.exists():
            print(f"  MISSING input: {net_path}")
            _record(results_df, results_path, row, {"status": "missing_input"})
            failed += 1
            continue

        # Skip if already solved
        if out_path.exists() and not force:
            print(f"  SKIP (already solved)")
            skipped += 1
            continue

        # Solve
        try:
            result = solve_network(net_path, out_path, threads=threads)
            result["tag"] = tag
            result["matrix"] = row.get("matrix", "")
            result["battery_scale"] = row.get("battery_scale", "")
            result["gas_price"] = row.get("gas_price", "")
            result["co2_price"] = row.get("co2_price", "")
            result["climate_year"] = row.get("climate_year", "")
            result["battery_duration"] = row.get("battery_duration", "")
            result["battery_extendable"] = row.get("battery_extendable", "")

            status = result["status"]
            slack = result["slack_mwh"]
            t = result["solve_time_s"]
            obj = result["objective"]

            if status == "solved":
                slack_warn = (
                    f"  ⚠ slack={slack:.0f} MWh" if slack and slack > 1000 else ""
                )
                print(f"  OK  {t}s  obj={obj:.0f}{slack_warn}")
                solved += 1
            else:
                print(f"  FAILED  status={status}")
                failed += 1

            _record(results_df, results_path, row, result)

        except Exception as exc:
            print(f"  ERROR: {exc}")
            _record(
                results_df, results_path, row, {"tag": tag, "status": f"error:{exc}"}
            )
            failed += 1

    elapsed = time.time() - t_start
    print(f"\n{'='*60}")
    print(
        f"Done in {elapsed/60:.1f} min  —  "
        f"{solved} solved, {skipped} skipped, {failed} failed"
    )
    print(f"Results: {results_path}")


def _record(results_df: pd.DataFrame, path: Path, row: pd.Series, result: dict) -> None:
    """Append or update a row in results_df and save to CSV."""
    record = {**dict(row), **result}
    new_row = pd.DataFrame([record])

    if "tag" in results_df.columns and record.get("tag") in results_df["tag"].values:
        results_df.loc[results_df["tag"] == record["tag"], list(result.keys())] = list(
            result.values()
        )
    else:
        results_df = pd.concat([results_df, new_row], ignore_index=True)

    results_df.to_csv(path, index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Solve sensitivity-analysis networks with Gurobi"
    )
    parser.add_argument(
        "--networks-dir",
        type=Path,
        default=ROOT / "scenarios" / "networks",
        help="Directory with input .nc files and manifest.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "solved_networks",
        help="Directory for solved .nc files (default: solved_networks/)",
    )
    parser.add_argument("--tag", default=None, help="Solve only this scenario tag")
    parser.add_argument(
        "--matrix",
        choices=["core", "duration", "invest", "extended_co2"],
        default=None,
        help="Solve only scenarios from this sub-matrix",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=0,
        help="Gurobi threads (0 = auto, default: 0)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-solve even if output file already exists",
    )
    args = parser.parse_args()

    run(
        networks_dir=args.networks_dir,
        output_dir=args.output_dir,
        tag_filter=args.tag,
        matrix_filter=args.matrix,
        threads=args.threads,
        force=args.force,
    )
