# Provided Maps Structural Notes

These instances are not small textbook planar maps. They are dense benchmark graphs with strong clique structure and high local connectivity.

- `le450_5a.col` needs more than four colors because its target class count is 5 and the observed clique lower bound reaches 5. The graph is also structurally dense enough to be difficult: density=0.0566, avg_degree=25.40, max_degree=42. In this run, best variant B5 solved in 148.93s.
- `le450_15b.col` needs more than four colors because its target class count is 15 and the observed clique lower bound reaches 15. The graph is also structurally dense enough to be difficult: density=0.0809, avg_degree=36.31, max_degree=94. In this run, all variants hit the timeout limit.
- `le450_25a.col` needs more than four colors because its target class count is 25 and the observed clique lower bound reaches 25. The graph is also structurally dense enough to be difficult: density=0.0818, avg_degree=36.71, max_degree=128. In this run, best variant B1 solved in 0.04s.