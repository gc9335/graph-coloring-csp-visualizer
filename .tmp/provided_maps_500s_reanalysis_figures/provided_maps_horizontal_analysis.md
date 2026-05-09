# Provided Maps Horizontal Comparison

Each dataset is compared under the same color limit, using only the variants that were actually executed for that dataset.

## le450_5a (5 colors)
- Evaluated variants: `B0-B5`.
- Fastest completed variant: `B5` in 148.93s.
- Smallest search tree: `B4` with 45277 node expansions.
- The 5-color instance sits close to the feasibility boundary, and LCV brings the clearest search reduction.

## le450_15b (15 colors)
- Evaluated variants: `B3-B5`.
- No executed variant finished within the current timeout, so this dataset is better compared through search-space reduction than solve time.
- Smallest search tree: `B4` with 261776 node expansions.
- For the 15-color instance, the useful signal is the drop in node expansions and backtracks; the MRV + Degree + LCV stack remains the strongest combination in the 500s budget.

## le450_25a (25 colors)
- Evaluated variants: `B0-B5`.
- Fastest completed variant: `B1` in 0.04s.
- Smallest search tree: `B2` with 450 node expansions.
- The 25-color instance has many feasible colorings, so differences mostly reflect heuristic overhead rather than solvability.
