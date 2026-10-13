# NimbusAI — GPU Cost Optimization Report

**Period:** monthly  
**Baseline spend:** $27,133  
**Optimized spend:** $14,626  
**Projected savings:** $12,507  (**46%**)

## Savings by lever

| Lever | Savings (USD) |
|---|---|
| Inference (cascade/cache/batch) | $1,212 |
| Purchasing (spot/reserved) | $10,040 |
| Right-size util-lies | $655 |
| Kill idle GPUs | $600 |

## Sustainability

- Energy per query: 0.24 Wh
- Carbon per query: 0.091 gCO2e
- Cheapest+cleanest region: europe-north1

### Extension: cache economics

- Average cache reads assumed: 3.0
- Break-even: 0.56 reads
- Cache policy: enabled (2400/2400 eligible rows)

### Extension: reasoning budget

- Reasoning traffic: 8.4% of requests
- Reasoning share: 16.5% of optimized cost and 94.0% of energy
- Estimated savings when capped at 10% traffic: $0.00 and 0.00 Wh

### Extension: carbon-aware scheduling

- Interruptible jobs: us-east-1 -> europe-north1
- Estimated carbon saved: 626,150.00 gCO2e (92.1%)
- Trade-off: the cleanest region may increase latency or data-transfer cost.

_Figures are June-2026 as-of snapshots; re-baseline before acting._