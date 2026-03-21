try:
    from ortools.sat.python import cp_model
except ImportError:  # pragma: no cover - depends on local environment
    cp_model = None


SLOT_MINUTES = 30
MAX_CONSECUTIVE_SLOTS = 3
SOLVE_TIME_LIMIT_SECONDS = 10
SPREAD_WEIGHT = 1000
SINGLE_DUTY_WEIGHT = 220
SINGLE_REST_WEIGHT = 200
DOUBLE_DUTY_REWARD = 35
TRIPLE_DUTY_REWARD = 20
DOUBLE_REST_REWARD = 40
TRIPLE_REST_REWARD = 25


def _ensure_ortools_available():
    if cp_model is None:
        raise RuntimeError(
            "4:7 scheduling requires the 'ortools' package. "
            "Install backend dependencies again after adding ortools."
        )


def _add_exact_pattern_var(model, var, positive_literals, negative_literals):
    all_literals = list(positive_literals) + [literal.Not() for literal in negative_literals]
    model.AddBoolAnd(all_literals).OnlyEnforceIf(var)

    off_conditions = [literal.Not() for literal in positive_literals] + list(negative_literals)
    model.AddBoolOr(off_conditions).OnlyEnforceIf(var.Not())


def solve_4_7_block(
    controllers,
    positions,
    start,
    end,
    slot_len=SLOT_MINUTES,
    time_limit_s=SOLVE_TIME_LIMIT_SECONDS,
):
    _ensure_ortools_available()

    if len(controllers) != 7:
        raise ValueError("4:7 scheduling requires exactly 7 controllers.")
    if len(positions) != 4:
        raise ValueError("4:7 scheduling requires exactly 4 positions.")

    total = end - start
    if total <= 0:
        raise ValueError("End time must be greater than start time.")
    if total % slot_len != 0:
        raise ValueError(
            f"4:7 scheduling requires the block length to be divisible by {slot_len} minutes."
        )

    num_slots = total // slot_len
    if num_slots == 0:
        raise ValueError("No 30-minute slots available for 4:7 scheduling.")

    c_range = range(len(controllers))
    p_range = range(len(positions))
    t_range = range(num_slots)

    model = cp_model.CpModel()

    x = {}
    y = {}
    off = {}
    for c in c_range:
        for t in t_range:
            y[c, t] = model.NewBoolVar(f"work_c{c}_t{t}")
            off[c, t] = model.NewBoolVar(f"off_c{c}_t{t}")
            for p in p_range:
                x[c, p, t] = model.NewBoolVar(f"assign_c{c}_p{p}_t{t}")

    for p in p_range:
        for t in t_range:
            model.Add(sum(x[c, p, t] for c in c_range) == 1)

    for c in c_range:
        for t in t_range:
            model.Add(sum(x[c, p, t] for p in p_range) <= 1)
            model.Add(y[c, t] == sum(x[c, p, t] for p in p_range))
            model.Add(off[c, t] + y[c, t] == 1)

    if num_slots >= MAX_CONSECUTIVE_SLOTS + 1:
        for c in c_range:
            for t in range(num_slots - MAX_CONSECUTIVE_SLOTS):
                model.Add(
                    sum(y[c, t + offset] for offset in range(MAX_CONSECUTIVE_SLOTS + 1))
                    <= MAX_CONSECUTIVE_SLOTS
                )

    for c in c_range:
        for t in range(num_slots - 1):
            for p in p_range:
                for q in p_range:
                    if p != q:
                        model.Add(x[c, p, t] + x[c, q, t + 1] <= 1)

    load = {}
    for c in c_range:
        load[c] = model.NewIntVar(0, num_slots, f"load_c{c}")
        model.Add(load[c] == sum(y[c, t] for t in t_range))
        model.Add(load[c] >= 1)

    max_load = model.NewIntVar(0, num_slots, "max_load")
    min_load = model.NewIntVar(0, num_slots, "min_load")
    spread = model.NewIntVar(0, num_slots, "spread")
    for c in c_range:
        model.Add(max_load >= load[c])
        model.Add(min_load <= load[c])
    model.Add(spread == max_load - min_load)

    last_worked = {}
    last_at = {}
    for c in c_range:
        last_worked[c] = model.NewIntVar(0, max(0, num_slots - 1), f"last_c{c}")
        for t in t_range:
            last_at[c, t] = model.NewBoolVar(f"last_at_c{c}_t{t}")

        model.Add(sum(last_at[c, t] for t in t_range) == 1)
        model.Add(last_worked[c] == sum(t * last_at[c, t] for t in t_range))

        for t in t_range:
            model.Add(last_at[c, t] <= y[c, t])
            for later in range(t + 1, num_slots):
                model.Add(last_at[c, t] <= 1 - y[c, later])

            if t == num_slots - 1:
                model.Add(last_at[c, t] == y[c, t])
            else:
                model.Add(
                    last_at[c, t] >= y[c, t] - sum(y[c, later] for later in range(t + 1, num_slots))
                )

    openers = {c: y[c, 0] for c in c_range}
    big_m = num_slots
    for a in c_range:
        for b in c_range:
            if a == b:
                continue
            slack = model.NewIntVar(0, 2, f"open_slack_a{a}_b{b}")
            model.Add(slack == (1 - openers[a]) + openers[b])
            model.Add(last_worked[a] <= last_worked[b] + big_m * slack)

    single_duty = {}
    double_duty = {}
    triple_duty = {}
    single_rest = {}
    double_rest = {}
    triple_rest = {}

    for c in c_range:
        for t in t_range:
            positive = [y[c, t]]
            negative = []
            if t > 0:
                negative.append(y[c, t - 1])
            if t + 1 < num_slots:
                negative.append(y[c, t + 1])
            single_duty[c, t] = model.NewBoolVar(f"single_duty_c{c}_t{t}")
            _add_exact_pattern_var(model, single_duty[c, t], positive, negative)

            positive = [off[c, t]]
            negative = []
            if t > 0:
                negative.append(off[c, t - 1])
            if t + 1 < num_slots:
                negative.append(off[c, t + 1])
            single_rest[c, t] = model.NewBoolVar(f"single_rest_c{c}_t{t}")
            _add_exact_pattern_var(model, single_rest[c, t], positive, negative)

        for t in range(num_slots - 1):
            positive = [y[c, t], y[c, t + 1]]
            negative = []
            if t > 0:
                negative.append(y[c, t - 1])
            if t + 2 < num_slots:
                negative.append(y[c, t + 2])
            double_duty[c, t] = model.NewBoolVar(f"double_duty_c{c}_t{t}")
            _add_exact_pattern_var(model, double_duty[c, t], positive, negative)

            positive = [off[c, t], off[c, t + 1]]
            negative = []
            if t > 0:
                negative.append(off[c, t - 1])
            if t + 2 < num_slots:
                negative.append(off[c, t + 2])
            double_rest[c, t] = model.NewBoolVar(f"double_rest_c{c}_t{t}")
            _add_exact_pattern_var(model, double_rest[c, t], positive, negative)

        for t in range(num_slots - 2):
            positive = [y[c, t], y[c, t + 1], y[c, t + 2]]
            negative = []
            if t > 0:
                negative.append(y[c, t - 1])
            if t + 3 < num_slots:
                negative.append(y[c, t + 3])
            triple_duty[c, t] = model.NewBoolVar(f"triple_duty_c{c}_t{t}")
            _add_exact_pattern_var(model, triple_duty[c, t], positive, negative)

            positive = [off[c, t], off[c, t + 1], off[c, t + 2]]
            negative = []
            if t > 0:
                negative.append(off[c, t - 1])
            if t + 3 < num_slots:
                negative.append(off[c, t + 3])
            triple_rest[c, t] = model.NewBoolVar(f"triple_rest_c{c}_t{t}")
            _add_exact_pattern_var(model, triple_rest[c, t], positive, negative)

    model.Minimize(
        SPREAD_WEIGHT * spread
        + SINGLE_DUTY_WEIGHT * sum(single_duty.values())
        + SINGLE_REST_WEIGHT * sum(single_rest.values())
        - DOUBLE_DUTY_REWARD * sum(double_duty.values())
        - TRIPLE_DUTY_REWARD * sum(triple_duty.values())
        - DOUBLE_REST_REWARD * sum(double_rest.values())
        - TRIPLE_REST_REWARD * sum(triple_rest.values())
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_search_workers = 8

    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError(f"No feasible 4:7 schedule found ({solver.StatusName(status)}).")

    schedules = {controller: [] for controller in controllers}
    time_points = [start + i * slot_len for i in range(num_slots + 1)]

    for p in p_range:
        i = 0
        while i < num_slots:
            controller_idx = next(c for c in c_range if solver.Value(x[c, p, i]))
            j = i + 1
            while j < num_slots and solver.Value(x[controller_idx, p, j]):
                j += 1

            schedules[controllers[controller_idx]].append(
                (positions[p], time_points[i], time_points[j])
            )
            i = j

    return schedules
