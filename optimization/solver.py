"""
M-TSP Solver for Smart Travel Itinerary Optimizer (Balanced objective)

This version maximizes total fun but includes a small distance penalty (alpha)
so the solver prefers spatially compact routes when fun gains are comparable.

Objective:
    maximize sum(fun_i * y_id) - alpha * sum(dist_ij * x_ijd)

Constraints:
    - Each attraction visited at most once across all days.
    - Daily time and budget limits.
    - Flow connectivity: each visited node must have at least one connecting edge.
    - MTZ subtour elimination per day (connectivity consistency).

Returns:
    itinerary (list of lists of attraction names per day),
    total_cost (entry + travel cost),
    total_fun,
    total_distance (km)
"""

from ortools.linear_solver import pywraplp
import numpy as np


def solve_mtsp(
    attractions,            # pandas.DataFrame (must contain: name, avg_time_hr, entry_fee, fun_score, category optional)
    distances,              # pandas.DataFrame distance matrix (rows & cols same order as attractions)
    days=3,
    budget_day=1500,
    time_day=8.0,
    weights=None,          # dict mapping category -> weight to scale fun_score
    avg_speed_kmph=20.0,   # used to convert km -> hours
    travel_cost_per_km=20.0,  # ₹ per km for travel
    alpha=0.01,            # small distance penalty weight (per km)
    time_limit_seconds=60  # MILP solver time limit
):
    # --- prepare data ---
    names = list(attractions["name"].values)
    n = len(names)

    # Distance matrix to numpy
    if hasattr(distances, "to_numpy"):
        dist = distances.to_numpy(dtype=float)
    else:
        dist = np.array(distances, dtype=float)

    # Convert distance to travel time (hours) if avg_speed_kmph provided
    travel_time = dist / float(avg_speed_kmph) if avg_speed_kmph else dist.copy()

    visit_time = attractions["avg_time_hr"].to_numpy(dtype=float)
    fee = attractions["entry_fee"].to_numpy(dtype=float)

    # Weighted fun score
    if weights is not None and "category" in attractions.columns:
        fun = []
        for i in range(n):
            cat = attractions.iloc[i]["category"]
            w = weights.get(cat, 1.0)
            fun.append(float(attractions.iloc[i].get("fun_score", 0.0)) * w)
        fun = np.array(fun, dtype=float)
    else:
        fun = attractions["fun_score"].to_numpy(dtype=float)

    # --- create solver ---
    solver = pywraplp.Solver.CreateSolver("CBC")
    if solver is None:
        raise RuntimeError("Cannot create OR-Tools solver.")
    solver.SetTimeLimit(int(time_limit_seconds * 1000))

    # --- decision variables ---
    x = {}  # binary: x[i,j,d] = 1 if on day d we go i -> j
    for d in range(days):
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                x[i, j, d] = solver.BoolVar(f"x_{i}_{j}_{d}")

    y = {}  # binary: y[i,d] = 1 if attraction i visited on day d
    for d in range(days):
        for i in range(n):
            y[i, d] = solver.BoolVar(f"y_{i}_{d}")

    u = {}  # MTZ ordering integer var
    for d in range(days):
        for i in range(n):
            u[i, d] = solver.IntVar(0, n, f"u_{i}_{d}")

    # --- objective: maximize fun - alpha * distance ---
    obj = solver.Objective()
    # fun terms
    for d in range(days):
        for i in range(n):
            obj.SetCoefficient(y[i, d], fun[i])
    # minus alpha * dist for arcs
    if alpha is not None and alpha != 0:
        for d in range(days):
            for i in range(n):
                for j in range(n):
                    if i == j:
                        continue
                    obj.SetCoefficient(x[i, j, d], -alpha * dist[i, j])
    obj.SetMaximization()

    # --- constraints ---

    # (1) Flow connectivity: visited => at least one in or out; also limit to max 2 (in+out)
    for d in range(days):
        for i in range(n):
            in_sum = solver.Sum([x[j, i, d] for j in range(n) if j != i])
            out_sum = solver.Sum([x[i, j, d] for j in range(n) if j != i])
            solver.Add(in_sum + out_sum >= y[i, d])           # if visited, must appear in some arc
            solver.Add(in_sum + out_sum <= 2 * y[i, d])       # at most one in + one out

    # (2) Each attraction visited at most once across days
    for i in range(n):
        solver.Add(solver.Sum([y[i, d] for d in range(days)]) <= 1)

    # (3) Daily time constraint (visit time + travel time)
    for d in range(days):
        visit_expr = solver.Sum([visit_time[i] * y[i, d] for i in range(n)])
        travel_expr = solver.Sum([travel_time[i, j] * x[i, j, d]
                                  for i in range(n) for j in range(n) if i != j])
        solver.Add(visit_expr + travel_expr <= time_day)

    # (4) Hard daily budget on entry fees
    for d in range(days):
        solver.Add(solver.Sum([fee[i] * y[i, d] for i in range(n)]) <= budget_day)

    # (5) MTZ subtour elimination (per-day)
    for d in range(days):
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                solver.Add(u[i, d] - u[j, d] + n * x[i, j, d] <= n - 1)

    # (6) Bounds on u
    for d in range(days):
        for i in range(n):
            solver.Add(u[i, d] >= y[i, d])
            solver.Add(u[i, d] <= n * y[i, d])

    # --- solve ---
    status = solver.Solve()
    print("\n🔧 Solver status:", status)

    if status not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        print("⚠️ No feasible solution found.")
        itinerary = [[] for _ in range(days)]
        return itinerary, 0.0, 0.0, 0.0

    # --- extract adjacency per day ---
    adj_per_day = [dict() for _ in range(days)]
    for d in range(days):
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                if x[i, j, d].solution_value() > 0.5:
                    adj_per_day[d].setdefault(i, []).append(j)

    # --- reconstruct day-wise routes (ordered chains) ---
    itinerary = []
    for d in range(days):
        assigned = [i for i in range(n) if y[i, d].solution_value() > 0.5]
        succ = {}
        for i, succs in adj_per_day[d].items():
            if succs:
                succ[i] = succs[0]
        visited = set()
        day_routes = []

        for start in assigned:
            if start in visited:
                continue
            cur = start
            chain = []
            while cur not in visited and cur in range(n):
                visited.add(cur)
                chain.append(names[cur])
                if cur in succ:
                    cur = succ[cur]
                else:
                    break
            day_routes.append(chain)

        # flatten multiple chains for display (keeps order within chains)
        flat = []
        for c in day_routes:
            flat.extend(c)
        itinerary.append(flat)

    # --- totals: entry cost, fun, distance, travel cost, combined cost ---
    total_entry_cost = sum(
        fee[i]
        for d in range(days)
        for i in range(n)
        if y[i, d].solution_value() > 0.5
    )

    total_fun = sum(
        fun[i]
        for d in range(days)
        for i in range(n)
        if y[i, d].solution_value() > 0.5
    )

    total_dist = sum(
        dist[i, j]
        for d in range(days)
        for i in range(n)
        for j in range(n)
        if i != j and x[i, j, d].solution_value() > 0.5
    )

    total_travel_cost = total_dist * travel_cost_per_km
    total_cost = total_entry_cost + total_travel_cost

    # --- debug summary ---
    print("\n✅ Optimization Results:")
    print(f"Total Fun Score: {round(total_fun, 2)}")
    print(f"Total Distance: {round(total_dist, 2)} km")
    print(f"Entry Cost: ₹{round(total_entry_cost, 2)}")
    print(f"Travel Cost (@₹{travel_cost_per_km}/km): ₹{round(total_travel_cost, 2)}")
    print(f"Total Combined Cost: ₹{round(total_cost, 2)}")
    print(f"Visited Attractions: {sum(y[i, d].solution_value() > 0.5 for d in range(days) for i in range(n))}")
    print(f"Arcs Used: {sum(x[i, j, d].solution_value() > 0.5 for d in range(days) for i in range(n) for j in range(n) if i != j)}")
    print(f"Distance penalty alpha: {alpha}")

    return itinerary, float(total_cost), float(total_fun), float(total_dist)
