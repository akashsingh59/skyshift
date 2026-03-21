import re
from collections import defaultdict

from .constants import NIGHT_POSITION_LABELS, POSITIONS

try:
    from ortools.sat.python import cp_model
except ImportError:  # pragma: no cover - depends on local environment
    cp_model = None

NIGHT_START = 15 * 60
NIGHT_END = 26 * 60
SLOT_MINUTES = 30
MAX_CONSECUTIVE_SLOTS = 4

BLOCKS = {
    "first_half_block_1": (15 * 60, 16 * 60 + 30),
    "second_half_block_1": (16 * 60 + 30, 18 * 60),
    "first_half_block_2": (18 * 60, 22 * 60),
    "second_half_block_2": (22 * 60, 26 * 60),
}

REST_WINDOW = (15 * 60, 18 * 60)
FIRST_HALF_ONLY_WINDOW = BLOCKS["first_half_block_2"]
SECOND_HALF_ONLY_WINDOW = BLOCKS["second_half_block_2"]
SOLVE_TIME_LIMIT_SECONDS = 10
OBJECTIVE_USED_CONTROLLER_WEIGHT = 100000
OBJECTIVE_HALF_GAP_WEIGHT = 5000
OBJECTIVE_OVERALL_GAP_WEIGHT = 3000
OBJECTIVE_FOURTH_SLOT_WEIGHT = 600
OBJECTIVE_SINGLETON_WEIGHT = 200
OBJECTIVE_RUN_START_WEIGHT = 25
OBJECTIVE_MAX_WORK_WEIGHT = 10

TIME_RE = re.compile(r"^(\d{2}):(\d{2})$")


def _ensure_ortools_available():
    if cp_model is None:
        raise RuntimeError(
            "Night scheduling requires the 'ortools' package. "
            "Install backend dependencies again after adding ortools."
        )


def _parse_hhmm_to_night_minutes(value):
    if not isinstance(value, str):
        raise ValueError("Time must be a string in HH:MM format")
    match = TIME_RE.match(value.strip())
    if not match:
        raise ValueError(f"Invalid time format: {value}")

    hours = int(match.group(1))
    mins = int(match.group(2))
    if hours > 23 or mins > 59:
        raise ValueError(f"Invalid time value: {value}")

    total = hours * 60 + mins
    if total < NIGHT_START:
        total += 24 * 60
    return total


def _fmt_night(minutes):
    day_offset = minutes // (24 * 60)
    hh = (minutes // 60) % 24
    mm = minutes % 60
    suffix = " (+1)" if day_offset > 0 else ""
    return f"{hh:02d}:{mm:02d}{suffix}"


def _slot_edges():
    return list(range(NIGHT_START, NIGHT_END + SLOT_MINUTES, SLOT_MINUTES))


def _slot_range_to_indexes(start_mins, end_mins):
    start_idx = (start_mins - NIGHT_START) // SLOT_MINUTES
    end_idx = (end_mins - NIGHT_START) // SLOT_MINUTES
    return list(range(start_idx, end_idx))


def _normalize_closures(raw_closures):
    normalized = defaultdict(list)
    for item in raw_closures or []:
        channel = item.get("channel")
        close_from_raw = item.get("closeFrom")
        close_to_raw = item.get("closeTo")

        if channel not in POSITIONS:
            raise ValueError(f"Unknown channel in closure: {channel}")

        close_from = _parse_hhmm_to_night_minutes(close_from_raw)
        close_to = _parse_hhmm_to_night_minutes(close_to_raw)
        if close_to <= close_from:
            close_to += 24 * 60

        clamped_from = max(NIGHT_START, close_from)
        clamped_to = min(NIGHT_END, close_to)
        if clamped_from < clamped_to:
            normalized[channel].append((clamped_from, clamped_to))

    return normalized


def _build_open_channels_by_slot(closures):
    edges = _slot_edges()
    open_by_slot = []

    for slot_idx in range(len(edges) - 1):
        slot_start = edges[slot_idx]
        slot_end = edges[slot_idx + 1]
        open_channels = []

        for channel in POSITIONS:
            is_closed = False
            for close_from, close_to in closures.get(channel, []):
                if slot_start < close_to and slot_end > close_from:
                    is_closed = True
                    break
            if not is_closed:
                open_channels.append(channel)

        open_by_slot.append(open_channels)

    return edges, open_by_slot


def _window_slots(window):
    return _slot_range_to_indexes(window[0], window[1])


def _sum_bool_vars(model, vars_list, name):
    total = model.NewIntVar(0, len(vars_list), name)
    model.Add(total == sum(vars_list))
    return total


def _build_solver_model(
    total_controllers,
    open_by_slot,
    requested_first_half=None,
    requested_second_half=None,
    require_all_used=False,
):
    _ensure_ortools_available()

    model = cp_model.CpModel()
    slot_count = len(open_by_slot)
    controllers = list(range(total_controllers))

    rest_slots = _window_slots(REST_WINDOW)
    first_half_only_slots = _window_slots(FIRST_HALF_ONLY_WINDOW)
    second_half_only_slots = _window_slots(SECOND_HALF_ONLY_WINDOW)

    x = {}
    work = {}
    half = {ctrl: model.NewBoolVar(f"half_{ctrl}") for ctrl in controllers}
    used = {ctrl: model.NewBoolVar(f"used_{ctrl}") for ctrl in controllers}
    work_totals = {}
    first_half_used = {}
    second_half_used = {}
    run_starts = {}
    singleton_runs = {}
    fourth_plus_slots = {}
    first_half_selected_work = {}
    second_half_selected_work = {}
    first_half_adjusted_work = {}
    second_half_adjusted_work = {}
    tower_mn_used = {}
    tower_s_used = {}

    tower_mn_channels = {1, 2}
    tower_s_channels = {6, 8}

    for ctrl in controllers:
        slot_work_vars = []
        tower_mn_slot_vars = []
        tower_s_slot_vars = []
        for slot_idx in range(slot_count):
            slot_vars = []
            for channel in open_by_slot[slot_idx]:
                var = model.NewBoolVar(f"x_c{ctrl}_s{slot_idx}_ch{channel}")
                x[(ctrl, slot_idx, channel)] = var
                slot_vars.append(var)
                if channel in tower_mn_channels:
                    tower_mn_slot_vars.append(var)
                if channel in tower_s_channels:
                    tower_s_slot_vars.append(var)

            work_var = model.NewBoolVar(f"work_c{ctrl}_s{slot_idx}")
            model.Add(work_var == sum(slot_vars))
            work[(ctrl, slot_idx)] = work_var
            slot_work_vars.append(work_var)

        work_totals[ctrl] = _sum_bool_vars(model, slot_work_vars, f"work_total_{ctrl}")
        model.AddMaxEquality(used[ctrl], slot_work_vars)

        tower_mn_used[ctrl] = model.NewBoolVar(f"tower_mn_used_{ctrl}")
        if tower_mn_slot_vars:
            model.AddMaxEquality(tower_mn_used[ctrl], tower_mn_slot_vars)
        else:
            model.Add(tower_mn_used[ctrl] == 0)

        tower_s_used[ctrl] = model.NewBoolVar(f"tower_s_used_{ctrl}")
        if tower_s_slot_vars:
            model.AddMaxEquality(tower_s_used[ctrl], tower_s_slot_vars)
        else:
            model.Add(tower_s_used[ctrl] == 0)

        model.Add(tower_mn_used[ctrl] + tower_s_used[ctrl] <= 1)

        first_half_used[ctrl] = model.NewBoolVar(f"first_used_{ctrl}")
        second_half_used[ctrl] = model.NewBoolVar(f"second_used_{ctrl}")

        model.Add(first_half_used[ctrl] <= used[ctrl])
        model.Add(first_half_used[ctrl] + half[ctrl] <= 1)
        model.Add(first_half_used[ctrl] >= used[ctrl] - half[ctrl])

        model.Add(second_half_used[ctrl] <= used[ctrl])
        model.Add(second_half_used[ctrl] <= half[ctrl])
        model.Add(second_half_used[ctrl] >= used[ctrl] + half[ctrl] - 1)

        first_half_selected_work[ctrl] = model.NewIntVar(0, slot_count, f"first_work_{ctrl}")
        model.Add(first_half_selected_work[ctrl] == work_totals[ctrl]).OnlyEnforceIf(first_half_used[ctrl])
        model.Add(first_half_selected_work[ctrl] == 0).OnlyEnforceIf(first_half_used[ctrl].Not())

        second_half_selected_work[ctrl] = model.NewIntVar(0, slot_count, f"second_work_{ctrl}")
        model.Add(second_half_selected_work[ctrl] == work_totals[ctrl]).OnlyEnforceIf(second_half_used[ctrl])
        model.Add(second_half_selected_work[ctrl] == 0).OnlyEnforceIf(second_half_used[ctrl].Not())

        first_half_adjusted_work[ctrl] = model.NewIntVar(0, slot_count * 3, f"first_adj_work_{ctrl}")
        model.Add(
            first_half_adjusted_work[ctrl]
            == work_totals[ctrl] + slot_count * half[ctrl] + slot_count * (1 - used[ctrl])
        )

        second_half_adjusted_work[ctrl] = model.NewIntVar(0, slot_count * 3, f"second_adj_work_{ctrl}")
        model.Add(
            second_half_adjusted_work[ctrl]
            == work_totals[ctrl] + slot_count * (1 - half[ctrl]) + slot_count * (1 - used[ctrl])
        )

        for slot_idx in range(slot_count):
            start_var = model.NewBoolVar(f"start_c{ctrl}_s{slot_idx}")
            prev_work = work[(ctrl, slot_idx - 1)] if slot_idx > 0 else None
            if prev_work is None:
                model.Add(start_var == work[(ctrl, slot_idx)])
            else:
                model.Add(start_var >= work[(ctrl, slot_idx)] - prev_work)
                model.Add(start_var <= work[(ctrl, slot_idx)])
                model.Add(start_var <= 1 - prev_work)
            run_starts[(ctrl, slot_idx)] = start_var

        for slot_idx in range(slot_count):
            singleton_var = model.NewBoolVar(f"singleton_c{ctrl}_s{slot_idx}")
            prev_work = work[(ctrl, slot_idx - 1)] if slot_idx > 0 else None
            next_work = work[(ctrl, slot_idx + 1)] if slot_idx < slot_count - 1 else None

            terms = [work[(ctrl, slot_idx)]]
            if prev_work is not None:
                terms.append(prev_work.Not())
            if next_work is not None:
                terms.append(next_work.Not())
            model.AddBoolAnd(terms).OnlyEnforceIf(singleton_var)

            off_conditions = [work[(ctrl, slot_idx)].Not()]
            if prev_work is not None:
                off_conditions.append(prev_work)
            if next_work is not None:
                off_conditions.append(next_work)
            model.AddBoolOr(off_conditions).OnlyEnforceIf(singleton_var.Not())
            singleton_runs[(ctrl, slot_idx)] = singleton_var

        for slot_idx in range(slot_count):
            fourth_var = model.NewBoolVar(f"fourth_plus_c{ctrl}_s{slot_idx}")
            if slot_idx < 3:
                model.Add(fourth_var == 0)
            else:
                prev_chain = [
                    work[(ctrl, slot_idx - 3)],
                    work[(ctrl, slot_idx - 2)],
                    work[(ctrl, slot_idx - 1)],
                    work[(ctrl, slot_idx)],
                ]
                model.AddBoolAnd(prev_chain).OnlyEnforceIf(fourth_var)
                model.AddBoolOr(
                    [
                        work[(ctrl, slot_idx - 3)].Not(),
                        work[(ctrl, slot_idx - 2)].Not(),
                        work[(ctrl, slot_idx - 1)].Not(),
                        work[(ctrl, slot_idx)].Not(),
                    ]
                ).OnlyEnforceIf(fourth_var.Not())
            fourth_plus_slots[(ctrl, slot_idx)] = fourth_var

    for slot_idx, open_channels in enumerate(open_by_slot):
        for channel in open_channels:
            model.Add(sum(x[(ctrl, slot_idx, channel)] for ctrl in controllers) == 1)

    for ctrl in controllers:
        for slot_idx in second_half_only_slots:
            model.Add(work[(ctrl, slot_idx)] == 0).OnlyEnforceIf(half[ctrl].Not())

        for slot_idx in first_half_only_slots:
            model.Add(work[(ctrl, slot_idx)] == 0).OnlyEnforceIf(half[ctrl])

        model.Add(
            sum(work[(ctrl, slot_idx)] for slot_idx in rest_slots) <= len(rest_slots) - 1
        ).OnlyEnforceIf(half[ctrl].Not())

        for start_idx in range(slot_count - MAX_CONSECUTIVE_SLOTS):
            model.Add(
                sum(work[(ctrl, start_idx + offset)] for offset in range(MAX_CONSECUTIVE_SLOTS + 1))
                <= MAX_CONSECUTIVE_SLOTS
            )

        for slot_idx in range(slot_count - 1):
            current_open = open_by_slot[slot_idx]
            next_open = open_by_slot[slot_idx + 1]
            for current_channel in current_open:
                for next_channel in next_open:
                    if current_channel != next_channel:
                        model.Add(
                            x[(ctrl, slot_idx, current_channel)] + x[(ctrl, slot_idx + 1, next_channel)] <= 1
                        )

    if requested_first_half is not None:
        model.Add(sum(half[ctrl] for ctrl in controllers) == total_controllers - requested_first_half)
    if requested_second_half is not None:
        model.Add(sum(half[ctrl] for ctrl in controllers) == requested_second_half)
    if require_all_used:
        for ctrl in controllers:
            model.Add(used[ctrl] == 1)

    used_total = _sum_bool_vars(model, list(used.values()), "used_total")
    first_used_total = _sum_bool_vars(model, list(first_half_used.values()), "first_used_total")
    second_used_total = _sum_bool_vars(model, list(second_half_used.values()), "second_used_total")

    max_work = model.NewIntVar(0, slot_count, "max_work")
    model.AddMaxEquality(max_work, list(work_totals.values()))

    split_gap = model.NewIntVar(0, total_controllers, "split_gap")
    model.AddAbsEquality(split_gap, first_used_total - second_used_total)

    used_adjusted_work = {}
    for ctrl in controllers:
        used_adjusted_work[ctrl] = model.NewIntVar(0, slot_count * 2, f"used_adj_work_{ctrl}")
        model.Add(used_adjusted_work[ctrl] == work_totals[ctrl] + slot_count * (1 - used[ctrl]))

    min_used_work = model.NewIntVar(0, slot_count * 2, "min_used_work")
    model.AddMinEquality(min_used_work, list(used_adjusted_work.values()))
    overall_work_gap = model.NewIntVar(0, slot_count, "overall_work_gap")
    model.Add(overall_work_gap == max_work - min_used_work)
    model.Add(overall_work_gap <= 1)

    first_half_max_work = model.NewIntVar(0, slot_count, "first_half_max_work")
    model.AddMaxEquality(first_half_max_work, list(first_half_selected_work.values()))
    first_half_min_work = model.NewIntVar(0, slot_count * 3, "first_half_min_work")
    model.AddMinEquality(first_half_min_work, list(first_half_adjusted_work.values()))
    first_half_gap = model.NewIntVar(0, slot_count, "first_half_gap")
    model.Add(first_half_gap == first_half_max_work - first_half_min_work)

    second_half_max_work = model.NewIntVar(0, slot_count, "second_half_max_work")
    model.AddMaxEquality(second_half_max_work, list(second_half_selected_work.values()))
    second_half_min_work = model.NewIntVar(0, slot_count * 3, "second_half_min_work")
    model.AddMinEquality(second_half_min_work, list(second_half_adjusted_work.values()))
    second_half_gap = model.NewIntVar(0, slot_count, "second_half_gap")
    model.Add(second_half_gap == second_half_max_work - second_half_min_work)

    singleton_total = _sum_bool_vars(model, list(singleton_runs.values()), "singleton_total")
    fourth_plus_total = _sum_bool_vars(model, list(fourth_plus_slots.values()), "fourth_plus_total")
    run_start_total = _sum_bool_vars(model, list(run_starts.values()), "run_start_total")

    # Prefer fewer controllers first, then smaller workload spread, then fewer fragmented duties.
    model.Minimize(
        used_total * OBJECTIVE_USED_CONTROLLER_WEIGHT
        + (first_half_gap + second_half_gap) * OBJECTIVE_HALF_GAP_WEIGHT
        + overall_work_gap * OBJECTIVE_OVERALL_GAP_WEIGHT
        + fourth_plus_total * OBJECTIVE_FOURTH_SLOT_WEIGHT
        + singleton_total * OBJECTIVE_SINGLETON_WEIGHT
        + run_start_total * OBJECTIVE_RUN_START_WEIGHT
        + max_work * OBJECTIVE_MAX_WORK_WEIGHT
        + split_gap
    )

    return {
        "model": model,
        "x": x,
        "work": work,
        "half": half,
        "used": used,
        "workTotals": work_totals,
        "firstHalfUsed": first_half_used,
        "secondHalfUsed": second_half_used,
        "runStarts": run_starts,
        "singletonRuns": singleton_runs,
        "fourthPlusSlots": fourth_plus_slots,
    }


def _solve_night_cp_sat(
    total_controllers,
    open_by_slot,
    requested_first_half=None,
    requested_second_half=None,
    require_all_used=False,
):
    if total_controllers <= 0:
        raise ValueError("Controller count must be positive")

    model_data = _build_solver_model(
        total_controllers,
        open_by_slot,
        requested_first_half=requested_first_half,
        requested_second_half=requested_second_half,
        require_all_used=require_all_used,
    )
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = SOLVE_TIME_LIMIT_SECONDS
    solver.parameters.random_seed = 0

    status = solver.Solve(model_data["model"])
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        if status == cp_model.UNKNOWN:
            reason = "Solver timed out before finding a feasible night schedule"
        else:
            reason = "No feasible night schedule found for the given controller counts and closures"
        return {
            "status": "infeasible",
            "reason": reason,
        }

    raw_assignments = []
    for (ctrl, slot_idx, channel), var in model_data["x"].items():
        if solver.Value(var):
            raw_assignments.append(
                {
                    "controllerIndex": ctrl,
                    "slot": slot_idx,
                    "channel": channel,
                }
            )

    return {
        "status": "ok",
        "assignments": raw_assignments,
        "halfByController": {ctrl: solver.Value(model_data["half"][ctrl]) for ctrl in range(total_controllers)},
        "usedByController": {ctrl: solver.Value(model_data["used"][ctrl]) for ctrl in range(total_controllers)},
        "workTotals": {ctrl: solver.Value(model_data["workTotals"][ctrl]) for ctrl in range(total_controllers)},
    }


def _choose_best_total_solution(total_controllers, open_by_slot):
    lower_bounds = _minimum_required_lower_bounds(open_by_slot)
    first_lower = lower_bounds["firstHalf"]
    second_lower = lower_bounds["secondHalf"]

    if total_controllers < first_lower + second_lower:
        return {
            "status": "infeasible",
            "reason": (
                f"No feasible night split for totalControllers={total_controllers}. "
                f"Minimum required with current channel timings is {first_lower + second_lower} "
                f"({first_lower} first-half + {second_lower} second-half)."
            ),
        }

    best = None
    last_reason = "No feasible night schedule found for the given controller counts and closures"

    for first_count in range(first_lower, total_controllers - second_lower + 1):
        second_count = total_controllers - first_count
        attempt = _solve_night_cp_sat(
            total_controllers,
            open_by_slot,
            requested_first_half=first_count,
            requested_second_half=second_count,
            require_all_used=True,
        )
        if attempt["status"] != "ok":
            last_reason = attempt["reason"]
            continue

        renamed = _rename_controllers(attempt, explicit_halves=False)
        metrics = _spread_metrics(renamed)
        used_total = len(renamed["controllerPools"]["firstHalf"]) + len(renamed["controllerPools"]["secondHalf"])
        key = (
            metrics["overallGap"],
            metrics["halfInternalGap"],
            metrics["overallMax"],
            metrics["halfAverageGap"],
            abs(first_count - second_count),
            first_count,
            used_total,
        )
        candidate = {
            "status": "ok",
            "solution": attempt,
            "renamed": renamed,
            "selectedSplit": (first_count, second_count),
            "key": key,
        }
        if best is None or candidate["key"] < best["key"]:
            best = candidate

    if best is None:
        return {
            "status": "infeasible",
            "reason": last_reason,
        }

    return best


def _rename_controllers(solution, explicit_halves=False):
    half_by_controller = solution["halfByController"]
    used_by_controller = solution["usedByController"]

    def include_controller(ctrl):
        return explicit_halves or bool(used_by_controller[ctrl])

    first_raw = [ctrl for ctrl in sorted(half_by_controller) if half_by_controller[ctrl] == 0 and include_controller(ctrl)]
    second_raw = [ctrl for ctrl in sorted(half_by_controller) if half_by_controller[ctrl] == 1 and include_controller(ctrl)]

    rename_map = {}
    first_pool = []
    second_pool = []

    for idx, ctrl in enumerate(first_raw, start=1):
        label = f"f{idx}"
        rename_map[ctrl] = label
        first_pool.append(label)

    for idx, ctrl in enumerate(second_raw, start=1):
        label = f"s{idx}"
        rename_map[ctrl] = label
        second_pool.append(label)

    renamed_assignments = []
    for item in solution["assignments"]:
        controller_label = rename_map.get(item["controllerIndex"])
        if controller_label is None:
            continue
        renamed_assignments.append(
            {
                "controller": controller_label,
                "slot": item["slot"],
                "channel": item["channel"],
            }
        )

    workload_by_label = {}
    for ctrl, label in rename_map.items():
        workload_by_label[label] = solution["workTotals"].get(ctrl, 0)

    return {
        "assignments": renamed_assignments,
        "controllerPools": {
            "firstHalf": first_pool,
            "secondHalf": second_pool,
        },
        "workloadByController": workload_by_label,
    }


def _collapse_block_assignments(assignments, block_slots):
    slot_to_items = defaultdict(list)
    for item in assignments:
        if item["slot"] in block_slots:
            slot_to_items[item["slot"]].append(item)

    collapsed = []
    controllers = sorted({item["controller"] for item in assignments})
    ordered_block_slots = sorted(block_slots)

    for controller in controllers:
        current_channel = None
        run_start = None
        previous_slot = None

        for slot_idx in ordered_block_slots:
            slot_items = slot_to_items.get(slot_idx, [])
            channel = None
            for item in slot_items:
                if item["controller"] == controller:
                    channel = item["channel"]
                    break

            if channel is None:
                if current_channel is not None:
                    collapsed.append(
                        {
                            "controller": controller,
                            "channel": current_channel,
                            "slotStart": run_start,
                            "slotEnd": previous_slot + 1,
                        }
                    )
                    current_channel = None
                    run_start = None
                previous_slot = slot_idx
                continue

            if current_channel == channel and previous_slot is not None and slot_idx == previous_slot + 1:
                previous_slot = slot_idx
                continue

            if current_channel is not None:
                collapsed.append(
                    {
                        "controller": controller,
                        "channel": current_channel,
                        "slotStart": run_start,
                        "slotEnd": previous_slot + 1,
                    }
                )

            current_channel = channel
            run_start = slot_idx
            previous_slot = slot_idx

        if current_channel is not None:
            collapsed.append(
                {
                    "controller": controller,
                    "channel": current_channel,
                    "slotStart": run_start,
                    "slotEnd": previous_slot + 1,
                }
            )

    return collapsed


def _assignments_to_time_ranges(assignments, edges):
    result = []
    for item in assignments:
        result.append(
            {
                "controller": item["controller"],
                "channel": item["channel"],
                "start": _fmt_night(edges[item["slotStart"]]),
                "end": _fmt_night(edges[item["slotEnd"]]),
            }
        )
    return result


def _uncovered_to_time_ranges(uncovered, edges):
    result = []
    for item in uncovered:
        idx = item["slot"]
        result.append(
            {
                "start": _fmt_night(edges[idx]),
                "end": _fmt_night(edges[idx + 1]),
                "channels": item["openChannels"],
            }
        )
    return result


def _workload_gap_hours(pool, workload_by_controller):
    if not pool:
        return 0
    slot_counts = [workload_by_controller.get(controller, 0) for controller in pool]
    return ((max(slot_counts) - min(slot_counts)) * SLOT_MINUTES) / 60


def _controller_hours(pool, workload_by_controller):
    return [(workload_by_controller.get(controller, 0) * SLOT_MINUTES) / 60 for controller in pool]


def _average(values):
    return sum(values) / len(values) if values else 0


def _spread_metrics(renamed):
    first_hours = _controller_hours(renamed["controllerPools"]["firstHalf"], renamed["workloadByController"])
    second_hours = _controller_hours(renamed["controllerPools"]["secondHalf"], renamed["workloadByController"])
    all_hours = first_hours + second_hours

    if not all_hours:
        return {
            "overallGap": 0,
            "overallMax": 0,
            "halfAverageGap": 0,
            "halfInternalGap": 0,
        }

    return {
        "overallGap": max(all_hours) - min(all_hours),
        "overallMax": max(all_hours),
        "halfAverageGap": abs(_average(first_hours) - _average(second_hours)),
        "halfInternalGap": max(
            (max(first_hours) - min(first_hours)) if first_hours else 0,
            (max(second_hours) - min(second_hours)) if second_hours else 0,
        ),
    }


def _minimum_required_lower_bounds(open_by_slot):
    return {
        "firstHalf": max((len(open_by_slot[idx]) for idx in _window_slots(FIRST_HALF_ONLY_WINDOW)), default=0),
        "secondHalf": max((len(open_by_slot[idx]) for idx in _window_slots(SECOND_HALF_ONLY_WINDOW)), default=0),
    }


def _block_results_from_assignments(assignments):
    block_results = []
    for block_name, (start_mins, end_mins) in BLOCKS.items():
        block_slots = _slot_range_to_indexes(start_mins, end_mins)
        block_results.append(
            {
                "block": block_name,
                "status": "ok",
                "reason": "",
                "assignments": _collapse_block_assignments(assignments, block_slots),
                "uncovered": [],
            }
        )
    return block_results


def _infeasible_result(reason, closures, edges):
    closures_echo = []
    for channel in POSITIONS:
        for close_from, close_to in closures.get(channel, []):
            closures_echo.append(
                {
                    "channel": channel,
                    "closeFrom": _fmt_night(close_from),
                    "closeTo": _fmt_night(close_to),
                }
            )

    block_results = []
    for block_name in BLOCKS:
        block_results.append(
            {
                "block": block_name,
                "status": "infeasible",
                "reason": reason,
                "assignments": [],
                "uncovered": [],
            }
        )

    return {
        "status": "infeasible",
        "edges": edges,
        "controllerPools": {
            "firstHalf": [],
            "secondHalf": [],
        },
        "optimization": {
            "selectionMode": "unresolved",
            "requestedControllers": {
                "firstHalf": 0,
                "secondHalf": 0,
            },
            "requestedTotalControllers": 0,
            "selectedSplitAvailable": {
                "firstHalf": 0,
                "secondHalf": 0,
            },
            "minimumRequiredLowerBound": {
                "firstHalf": 0,
                "secondHalf": 0,
            },
            "minimumFeasibleControllers": {
                "firstHalf": 0,
                "secondHalf": 0,
            },
            "optimizedControllersUsed": {
                "firstHalf": 0,
                "secondHalf": 0,
            },
            "workloadGapHours": {
                "firstHalf": 0,
                "secondHalf": 0,
            },
        },
        "closuresEcho": closures_echo,
        "blockResults": block_results,
    }


def _run_night_schedule(payload):
    total_controllers_raw = payload.get("totalControllers")
    first_half_controllers = payload.get("firstHalfControllers")
    second_half_controllers = payload.get("secondHalfControllers")
    channel_closures = payload.get("channelClosures", [])

    closures = _normalize_closures(channel_closures)
    edges, open_by_slot = _build_open_channels_by_slot(closures)
    lower_bounds = _minimum_required_lower_bounds(open_by_slot)

    if total_controllers_raw is not None:
        total_controllers = int(total_controllers_raw)
        if total_controllers < 15 or total_controllers > 17:
            raise ValueError("Total night controllers must be between 15 and 17")

        chosen = _choose_best_total_solution(total_controllers, open_by_slot)
        if chosen["status"] != "ok":
            result = _infeasible_result(chosen["reason"], closures, edges)
            result["optimization"]["selectionMode"] = "totalControllers"
            result["optimization"]["requestedTotalControllers"] = total_controllers
            result["optimization"]["minimumRequiredLowerBound"] = lower_bounds
            return result

        solution = chosen["solution"]
        renamed = chosen["renamed"]
        first_pool = renamed["controllerPools"]["firstHalf"]
        second_pool = renamed["controllerPools"]["secondHalf"]
        selected_split = chosen["selectedSplit"]
        requested_counts = {
            "firstHalf": selected_split[0],
            "secondHalf": selected_split[1],
        }
        minimum_feasible = {
            "firstHalf": len(first_pool),
            "secondHalf": len(second_pool),
        }
    else:
        first_count = int(first_half_controllers or 0)
        second_count = int(second_half_controllers or 0)
        total_controllers = first_count + second_count
        if total_controllers <= 0:
            raise ValueError("Provide either totalControllers or both half controller counts")

        solution = _solve_night_cp_sat(
            total_controllers,
            open_by_slot,
            requested_first_half=first_count,
            requested_second_half=second_count,
            require_all_used=True,
        )
        if solution["status"] != "ok":
            result = _infeasible_result(solution["reason"], closures, edges)
            result["optimization"]["selectionMode"] = "halfControllers"
            result["optimization"]["requestedControllers"] = {
                "firstHalf": first_count,
                "secondHalf": second_count,
            }
            result["optimization"]["requestedTotalControllers"] = total_controllers
            result["optimization"]["selectedSplitAvailable"] = {
                "firstHalf": first_count,
                "secondHalf": second_count,
            }
            result["optimization"]["minimumRequiredLowerBound"] = lower_bounds
            return result

        renamed = _rename_controllers(solution, explicit_halves=True)
        first_pool = renamed["controllerPools"]["firstHalf"]
        second_pool = renamed["controllerPools"]["secondHalf"]
        selected_split = (len(first_pool), len(second_pool))
        requested_counts = {
            "firstHalf": first_count,
            "secondHalf": second_count,
        }
        minimum_feasible = requested_counts.copy()

    block_results = _block_results_from_assignments(renamed["assignments"])

    closures_echo = []
    for channel in POSITIONS:
        for close_from, close_to in closures.get(channel, []):
            closures_echo.append(
                {
                    "channel": channel,
                    "closeFrom": _fmt_night(close_from),
                    "closeTo": _fmt_night(close_to),
                }
            )

    return {
        "status": "ok",
        "edges": edges,
        "controllerPools": {
            "firstHalf": first_pool,
            "secondHalf": second_pool,
        },
        "optimization": {
            "selectionMode": "totalControllers" if total_controllers_raw is not None else "halfControllers",
            "requestedControllers": requested_counts,
            "requestedTotalControllers": int(total_controllers),
            "selectedSplitAvailable": {
                "firstHalf": selected_split[0],
                "secondHalf": selected_split[1],
            },
            "minimumRequiredLowerBound": lower_bounds,
            "minimumFeasibleControllers": minimum_feasible,
            "optimizedControllersUsed": {
                "firstHalf": len(first_pool),
                "secondHalf": len(second_pool),
            },
            "workloadGapHours": {
                "firstHalf": _workload_gap_hours(first_pool, renamed["workloadByController"]),
                "secondHalf": _workload_gap_hours(second_pool, renamed["workloadByController"]),
            },
        },
        "closuresEcho": closures_echo,
        "blockResults": block_results,
    }


def preview_night_schedule(payload):
    result = _run_night_schedule(payload)
    edges = result["edges"]

    formatted_blocks = []
    for item in result["blockResults"]:
        formatted_blocks.append(
            {
                "block": item["block"],
                "status": item["status"],
                "reason": item["reason"],
                "assignments": _assignments_to_time_ranges(item["assignments"], edges),
                "uncovered": _uncovered_to_time_ranges(item["uncovered"], edges),
            }
        )

    return {
        "status": result["status"],
        "slotSizeMinutes": SLOT_MINUTES,
        "nightWindow": {
            "start": _fmt_night(NIGHT_START),
            "end": _fmt_night(NIGHT_END),
        },
        "optimization": result["optimization"],
        "controllerPools": result["controllerPools"],
        "channelClosures": result["closuresEcho"],
        "blocks": formatted_blocks,
    }


def build_night_schedule_for_pdf(payload):
    result = _run_night_schedule(payload)
    if result["status"] != "ok":
        reasons = [item["reason"] for item in result["blockResults"] if item["status"] != "ok" and item["reason"]]
        reason_text = reasons[0] if reasons else "Night schedule is infeasible for given inputs"
        raise ValueError(reason_text)

    edges = result["edges"]
    controller_order = result["controllerPools"]["firstHalf"] + result["controllerPools"]["secondHalf"]
    schedule = {controller: [] for controller in controller_order}

    for block in result["blockResults"]:
        for assignment in block["assignments"]:
            schedule[assignment["controller"]].append(
                (
                    NIGHT_POSITION_LABELS[assignment["channel"]],
                    edges[assignment["slotStart"]],
                    edges[assignment["slotEnd"]],
                )
            )

    for controller in controller_order:
        schedule[controller].sort(key=lambda item: item[1])
        merged = []
        for position, start, end in schedule[controller]:
            if merged and merged[-1][0] == position and merged[-1][2] == start:
                merged[-1] = (position, merged[-1][1], end)
            else:
                merged.append((position, start, end))
        schedule[controller] = merged

    return schedule, controller_order, NIGHT_START, NIGHT_END
