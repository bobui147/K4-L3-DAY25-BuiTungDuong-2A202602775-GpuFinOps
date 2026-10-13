"""M2 — Inference Cost Levers: $/1M-token, batch x cache x cascade (deck §7).

Run: python missions/m2_inference_levers.py
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from missions._common import load_csv, num
from finops import pricing
from finops import sustainability

# $/1M tokens (input, output) — illustrative 2026.
MODEL_PRICES = {"small": (0.20, 0.40), "large": (3.00, 15.00)}

# The dataset contains cached token volume, but not cache-prefix IDs or read
# counts. Keep the measurement assumption explicit instead of implying that
# missing source data is more precise than it is.
CACHE_AVG_READS = 3.0
CACHE_WRITE_COST_PER_M = 0.5


def run(verbose: bool = True) -> dict:
    rows = load_csv("token_usage.csv")
    base_cost = opt_cost = 0.0
    total_tokens = 0
    reasoning_cost = normal_cost = 0.0
    reasoning_wh = normal_wh = 0.0
    reasoning_requests = normal_requests = 0
    cacheable_rows = cache_applied_rows = 0
    cache_enabled = pricing.cache_is_worth_it(
        CACHE_AVG_READS, CACHE_WRITE_COST_PER_M, read_discount=0.10
    )
    for r in rows:
        inp, out = int(num(r["input_tokens"])), int(num(r["output_tokens"]))
        cached = int(num(r["cached_input_tokens"]))
        is_batch = bool(int(num(r["is_batch"])))
        is_reasoning = bool(int(num(r["is_reasoning"])))
        total_tokens += inp + out
        # BASELINE: naive deployment — everything on the large model, no cache, no batch
        lin, lout = MODEL_PRICES["large"]
        base_cost += pricing.request_cost(inp, out, lin, lout)
        # OPTIMIZED: cascade (route_tier), prompt caching, batch API
        pin, pout = MODEL_PRICES[r["route_tier"]]
        if cached > 0:
            cacheable_rows += 1
        cached_for_request = cached if cache_enabled else 0
        if cached_for_request > 0:
            cache_applied_rows += 1
        row_cost = pricing.request_cost(
            inp, out, pin, pout, cached_in=cached_for_request, batch=is_batch
        )
        opt_cost += row_cost

        row_wh = sustainability.wh_per_query(inp + out, is_reasoning=is_reasoning)
        if is_reasoning:
            reasoning_requests += 1
            reasoning_cost += row_cost
            reasoning_wh += row_wh
        else:
            normal_requests += 1
            normal_cost += row_cost
            normal_wh += row_wh

    base_pm = pricing.dollars_per_million(base_cost, total_tokens)
    opt_pm = pricing.dollars_per_million(opt_cost, total_tokens)
    savings_pct = (1 - opt_cost / base_cost) * 100 if base_cost else 0.0

    total_requests = len(rows)
    target_reasoning_requests = round(total_requests * 0.10)
    excess_reasoning = max(0, reasoning_requests - target_reasoning_requests)
    avg_reasoning_cost = reasoning_cost / reasoning_requests if reasoning_requests else 0.0
    avg_normal_cost = normal_cost / normal_requests if normal_requests else 0.0
    avg_reasoning_wh = reasoning_wh / reasoning_requests if reasoning_requests else 0.0
    avg_normal_wh = normal_wh / normal_requests if normal_requests else 0.0
    reasoning_budget = {
        "reasoning_requests": reasoning_requests,
        "normal_requests": normal_requests,
        "reasoning_traffic_pct": round(reasoning_requests / total_requests * 100, 1) if total_requests else 0.0,
        "reasoning_cost": round(reasoning_cost, 2),
        "normal_cost": round(normal_cost, 2),
        "reasoning_cost_pct": round(reasoning_cost / opt_cost * 100, 1) if opt_cost else 0.0,
        "reasoning_wh": round(reasoning_wh, 2),
        "normal_wh": round(normal_wh, 2),
        "reasoning_wh_pct": round(reasoning_wh / (reasoning_wh + normal_wh) * 100, 1)
        if (reasoning_wh + normal_wh) else 0.0,
        "target_reasoning_pct": 10.0,
        "estimated_cap_savings_usd": round(
            excess_reasoning * max(0.0, avg_reasoning_cost - avg_normal_cost), 2
        ),
        "estimated_cap_savings_wh": round(
            excess_reasoning * max(0.0, avg_reasoning_wh - avg_normal_wh), 2
        ),
    }
    cache_economics = {
        "avg_cache_reads": CACHE_AVG_READS,
        "write_cost_per_m": CACHE_WRITE_COST_PER_M,
        "break_even_reads": round(
            pricing.cache_break_even_reads(CACHE_WRITE_COST_PER_M, 0.10), 2
        ),
        "cache_enabled": cache_enabled,
        "cacheable_rows": cacheable_rows,
        "cache_applied_rows": cache_applied_rows,
    }

    if verbose:
        print("== M2 Inference Cost Levers ==")
        print(f"requests={len(rows)}  tokens={total_tokens:,}")
        print(f"baseline  : ${base_cost:,.2f}/day   ${base_pm:.3f}/1M-token")
        print(f"optimized : ${opt_cost:,.2f}/day   ${opt_pm:.3f}/1M-token")
        print(f"savings   : {savings_pct:.1f}%  (cascade + caching + batch)")
        print(f"discount stack (batch + 100% cache): {pricing.discount_stack(batch=True, cache_hit_frac=1.0):.3f} of naive")
        print(
            f"cache economics: {cache_applied_rows}/{cacheable_rows} rows enabled "
            f"(break-even {cache_economics['break_even_reads']} reads)"
        )
        print(
            f"reasoning: {reasoning_budget['reasoning_traffic_pct']:.1f}% of requests, "
            f"{reasoning_budget['reasoning_cost_pct']:.1f}% of optimized cost, "
            f"{reasoning_budget['reasoning_wh_pct']:.1f}% of energy"
        )

    return {
        "baseline_daily": round(base_cost, 2), "optimized_daily": round(opt_cost, 2),
        "baseline_per_m": round(base_pm, 3), "optimized_per_m": round(opt_pm, 3),
        "savings_pct": round(savings_pct, 1), "total_tokens": total_tokens,
        "cache_economics": cache_economics,
        "reasoning_budget": reasoning_budget,
    }


if __name__ == "__main__":
    run()
