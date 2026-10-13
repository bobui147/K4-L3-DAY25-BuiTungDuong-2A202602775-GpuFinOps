"""M3 — Purchasing Strategy: break-even, tier choice, spot-checkpoint sim (deck §4).

Run: python missions/m3_purchasing.py
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from missions._common import load_csv, num, catalog_by_type
from finops import pricing
from finops import sustainability

DAYS = 30


def carbon_aware_schedule(jobs: list[dict], catalog: dict,
                          baseline_region: str = "us-east-1") -> dict:
    """Estimate carbon savings from moving interruptible jobs to the cleanest region.

    Workload duration, GPU count, and GPU wattage stay fixed; only the grid
    location changes. This keeps the result a scheduling estimate rather than
    an unsupported claim about model performance.
    """
    target_region = min(
        sustainability.REGION_CARBON,
        key=sustainability.REGION_CARBON.get,
    )
    rows = []
    for job in jobs:
        if int(num(job["interruptible"])) != 1:
            continue
        gpu_hours = (
            num(job["hours_per_day"])
            * num(job["days"])
            * int(num(job["num_gpus"]))
        )
        watts = num(catalog[job["gpu_type"]]["watts"])
        energy_kwh = gpu_hours * watts / 1000.0
        baseline_carbon = energy_kwh * sustainability.REGION_CARBON[baseline_region]
        target_carbon = energy_kwh * sustainability.REGION_CARBON[target_region]
        rows.append({
            "job_id": job["job_id"],
            "gpu_type": job["gpu_type"],
            "energy_kwh": round(energy_kwh, 2),
            "baseline_carbon_g": round(baseline_carbon, 2),
            "target_carbon_g": round(target_carbon, 2),
            "carbon_saved_g": round(baseline_carbon - target_carbon, 2),
        })
    baseline = sum(r["baseline_carbon_g"] for r in rows)
    target = sum(r["target_carbon_g"] for r in rows)
    saved = baseline - target
    return {
        "baseline_region": baseline_region,
        "target_region": target_region,
        "rows": rows,
        "baseline_carbon_g": round(baseline, 2),
        "target_carbon_g": round(target, 2),
        "carbon_saved_g": round(saved, 2),
        "carbon_reduction_pct": round(saved / baseline * 100, 1) if baseline else 0.0,
    }


def run(verbose: bool = True) -> dict:
    jobs = load_csv("workloads.csv")
    cat = catalog_by_type()
    on_demand_monthly = optimized_monthly = 0.0
    recs = []
    for j in jobs:
        gtype = j["gpu_type"]
        ngpu = int(num(j["num_gpus"]))
        hpd = num(j["hours_per_day"])
        interruptible = bool(int(num(j["interruptible"])))
        c = cat[gtype]
        gpu_hours = hpd * DAYS * ngpu
        od = num(c["on_demand_hr"])
        on_demand_cost = gpu_hours * od

        tier = pricing.recommend_tier(hpd, interruptible)
        if tier == "spot":
            sim = pricing.spot_checkpoint_cost(gpu_hours, num(c["spot_hr"]), od)
            opt_cost = sim["spot_cost"]
        elif tier == "reserved":
            opt_cost = gpu_hours * num(c["reserved_3yr_hr"])
        else:
            opt_cost = on_demand_cost

        on_demand_monthly += on_demand_cost
        optimized_monthly += opt_cost
        recs.append({"job_id": j["job_id"], "gpu_type": gtype, "tier": tier,
                     "on_demand": round(on_demand_cost), "optimized": round(opt_cost)})

    savings = on_demand_monthly - optimized_monthly
    savings_pct = savings / on_demand_monthly * 100 if on_demand_monthly else 0.0
    carbon_schedule = carbon_aware_schedule(jobs, cat)

    if verbose:
        print("== M3 Purchasing Strategy ==")
        print(f"break-even utilization @ 45% reserved discount = {pricing.break_even_utilization(0.45):.0%}")
        print(f"{'job':18}{'gpu':7}{'tier':11}{'on-demand':>12}{'optimized':>12}")
        for r in recs:
            print(f"{r['job_id']:18}{r['gpu_type']:7}{r['tier']:11}${r['on_demand']:>11,}${r['optimized']:>11,}")
        print(f"\nmonthly: on-demand ${on_demand_monthly:,.0f} -> optimized ${optimized_monthly:,.0f}  ({savings_pct:.1f}% saved)")
        print(
            f"carbon-aware scheduling: {carbon_schedule['baseline_region']} -> "
            f"{carbon_schedule['target_region']}, "
            f"{carbon_schedule['carbon_saved_g']:,.0f} gCO2e saved "
            f"({carbon_schedule['carbon_reduction_pct']:.1f}%)"
        )

    return {"recommendations": recs, "on_demand_monthly": round(on_demand_monthly),
            "optimized_monthly": round(optimized_monthly), "savings_pct": round(savings_pct, 1),
            "carbon_scheduling": carbon_schedule}


if __name__ == "__main__":
    run()
