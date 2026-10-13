# NimbusAI GPU FinOps — Short Write-up

## 1. Baseline vs. optimized

The deterministic June 2026 simulation starts at **$27,133/month** and ends at
**$14,626/month**, for **$12,507/month saved (46.1%)**. For inference traffic,
the unit cost drops from **$6.488 to $1.126 per 1M tokens**, an **82.6%**
reduction. This makes `$ / 1M-token` a better operating metric than GPU-hour
alone: the optimized stack serves more useful output per rented hour.

## 2. Contribution of each lever

- Inference cascade, cache, and batch: **$1,212/month** saved. Cascade is the
  largest part of this bucket because 80% of traffic is suitable for the small
  model; caching and batch compound the reduction.
- Spot/reserved purchasing: **$10,040/month** saved. Interruptible jobs use
  spot with checkpoint rework, while steady 24-hour jobs use reserved capacity.
- Right-sizing utilization lies: **$655/month** saved by moving flagged GPUs one
  tier down in the simulation.
- Killing idle GPUs: **$600/month** saved from the overnight idle H100.

## 3. GPU-Util lie

`gpu-h100-4` reports roughly 98% GPU-Util but only about 20% MFU. GPU-Util is a
busy-clock signal: memory stalls, synchronization, or kernel-launch overhead can
keep the device active without producing near-peak FLOPs. The financial impact
is paying the full H100 hourly rate for a fraction of its compute, so MFU/MBU
must be checked before purchasing more capacity.

## 4. Extensions implemented

1. **Cache economics.** Added `cache_break_even_reads()` and
   `cache_is_worth_it()`. With the documented simulation assumption of 3 average
   reads and a write cost equal to 0.5 full-price reads, the break-even point is
   0.56 reads, so caching is enabled. The policy is evaluated before cached
   tokens are used in M2.
2. **Reasoning budget.** M2 now reports reasoning traffic's share of requests,
   optimized dollars, and energy. It also estimates the dollar and Wh reduction
   from capping reasoning traffic at 10%, replacing excess reasoning calls with
   normal calls. The generated dataset is already at 8.4%, so the measured
   incremental saving at a 10% cap is $0 and 0 Wh; the important finding is that
   this small request share still consumes 94.0% of energy and 16.5% of cost.
3. **Carbon-aware scheduling.** Interruptible jobs are compared between
   `us-east-1` and the cleanest simulated region, `europe-north1`, while holding
   GPU hours and power constant. The report includes gCO2e saved and calls out
   the latency/data-transfer trade-off.

## 5. Recommendations for NimbusAI

1. Make `$ / 1M-token`, MFU, and MBU part of the weekly FinOps dashboard; do not
   use GPU-Util as the sole efficiency signal.
2. Route easy traffic to the small model, enable cache/batch only when their
   economics clear the break-even checks, and cap expensive reasoning traffic.
3. Use spot for checkpointable workloads, reserved capacity only above the
   utilization break-even, and schedule interruptible jobs in low-carbon regions
   when latency requirements allow it.
