import re
from collections import defaultdict

from .constants import NIGHT_POSITION_LABELS, POSITIONS

NIGHT_START = 15 * 60
NIGHT_END = 26 * 60
SLOT_MINUTES = 30

BLOCKS = {
    "first_half_block_1": (15 * 60, 16 * 60 + 30),
    "second_half_block_1": (16 * 60 + 30, 18 * 60),
    "first_half_block_2": (18 * 60, 22 * 60),
    "second_half_block_2": (22 * 60, 26 * 60),
}

TIME_RE = re.compile(r"^(\d{2}):(\d{2})$")


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


def _build_controller_ids(prefix, count):
    count_int = int(count)
    if count_int < 0:
        raise ValueError("Controller count cannot be negative")
    return [f"{prefix}{idx + 1}" for idx in range(count_int)]


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


def _slot_range_to_indexes(start_mins, end_mins):
    start_idx = (start_mins - NIGHT_START) // SLOT_MINUTES
    end_idx = (end_mins - NIGHT_START) // SLOT_MINUTES
    return list(range(start_idx, end_idx))


def _schedule_block1(block_name, block_slots, open_by_slot, controllers):
    if not controllers:
        return {
            "block": block_name,
            "status": "infeasible",
            "reason": "No controllers available for block",
            "assignments": [],
            "uncovered": [
                {
                    "slot": idx,
                    "openChannels": open_by_slot[idx],
                }
                for idx in block_slots
                if open_by_slot[idx]
            ],
        }

    # Block 1 assignments are fixed for 1.5h; any channel open at any moment
    # in the block needs one dedicated controller for the whole block.
    union_open = set()
    for idx in block_slots:
        union_open.update(open_by_slot[idx])

    ordered_union = [channel for channel in POSITIONS if channel in union_open]
    if len(ordered_union) > len(controllers):
        return {
            "block": block_name,
            "status": "infeasible",
            "reason": "Insufficient controllers to cover all open channels in block 1",
            "assignments": [],
            "uncovered": [
                {
                    "slot": idx,
                    "openChannels": open_by_slot[idx],
                }
                for idx in block_slots
                if open_by_slot[idx]
            ],
        }

    assignments = []
    for ctrl, channel in zip(controllers, ordered_union):
        assignments.append(
            {
                "controller": ctrl,
                "channel": channel,
                "slotStart": block_slots[0],
                "slotEnd": block_slots[-1] + 1,
            }
        )

    return {
        "block": block_name,
        "status": "ok",
        "reason": "",
        "assignments": assignments,
        "uncovered": [],
    }


def _allowed_to_work(state):
    if not state["everWorked"]:
        return True
    if state["workedPrev"]:
        return state["consecutive"] < 4
    return state["restSlots"] >= 1


def _schedule_block2(block_name, block_slots, open_by_slot, controllers, initial_worked_slots=None):
    if not controllers:
        return {
            "block": block_name,
            "status": "infeasible",
            "reason": "No controllers available for block",
            "assignments": [],
            "uncovered": [],
        }

    base_worked = initial_worked_slots or {}
    states = {
        ctrl: {
            "workedPrev": False,
            "consecutive": 0,
            "restSlots": 0,
            "everWorked": False,
            "totalWorked": int(base_worked.get(ctrl, 0)),
            "prevChannel": None,
        }
        for ctrl in controllers
    }

    slot_assignments = {}

    for slot_idx in block_slots:
        open_channels = open_by_slot[slot_idx]
        last_slot_idx = block_slots[-1]
        if len(open_channels) > len(controllers):
            return {
                "block": block_name,
                "status": "infeasible",
                "reason": f"Open channels exceed controller count at slot {slot_idx}",
                "assignments": [],
                "uncovered": [{"slot": slot_idx, "openChannels": open_channels}],
            }

        chosen = {}
        used = set()

        # Enforce minimum 1-hour duty stints where possible:
        # if a controller just started a stint in previous slot (consecutive == 1),
        # keep them on the same channel this slot unless that channel is closed.
        for ctrl in controllers:
            st = states[ctrl]
            if st["workedPrev"] and st["consecutive"] == 1 and st["prevChannel"] in open_channels:
                channel = st["prevChannel"]
                if channel in chosen and chosen[channel] != ctrl:
                    return {
                        "block": block_name,
                        "status": "infeasible",
                        "reason": f"Conflicting mandatory continuation at slot {slot_idx}",
                        "assignments": [],
                        "uncovered": [{"slot": slot_idx, "openChannels": open_channels}],
                    }
                chosen[channel] = ctrl
                used.add(ctrl)

        def score(ctrl, channel):
            st = states[ctrl]
            same_channel = st["prevChannel"] == channel and st["workedPrev"]
            starting_new = not st["workedPrev"]
            next_slot_idx = slot_idx + 1
            prefers_rest_after_90 = st["workedPrev"] and st["consecutive"] >= 3
            closes_next = (
                starting_new
                and slot_idx < last_slot_idx
                and channel not in open_by_slot[next_slot_idx]
            )
            starts_on_last_slot = starting_new and slot_idx == last_slot_idx
            return (
                # Avoid starting a fresh 30-minute stint on last slot unless necessary.
                0 if not starts_on_last_slot else 1,
                # Prefer starts that can continue into next slot (>= 1 hour).
                0 if not closes_next else 1,
                0 if not st["workedPrev"] else 1,
                # Prefer giving rest after 1.5 hours when coverage allows.
                0 if not prefers_rest_after_90 else 1,
                st["totalWorked"],
                st["consecutive"],
                0 if same_channel else 1,
                ctrl,
            )

        pending_channels = [channel for channel in open_channels if channel not in chosen]

        def backtrack(channel_pos):
            if channel_pos >= len(pending_channels):
                return True

            channel = pending_channels[channel_pos]
            candidates = []
            for ctrl in controllers:
                if ctrl in used:
                    continue

                st = states[ctrl]
                if not _allowed_to_work(st):
                    continue

                # Hard rule: controller cannot switch to a different position
                # in consecutive duty slots without rest.
                if st["workedPrev"] and st["prevChannel"] != channel:
                    continue

                candidates.append(ctrl)

            candidates.sort(key=lambda ctrl: score(ctrl, channel))

            for ctrl in candidates:
                used.add(ctrl)
                chosen[channel] = ctrl
                if backtrack(channel_pos + 1):
                    return True
                used.remove(ctrl)
                chosen.pop(channel, None)

            return False

        if not backtrack(0):
            return {
                "block": block_name,
                "status": "infeasible",
                "reason": f"No feasible assignment under rest/consecutive constraints at slot {slot_idx}",
                "assignments": [],
                "uncovered": [{"slot": slot_idx, "openChannels": open_channels}],
            }

        worked_this_slot = set(chosen.values())
        for ctrl in controllers:
            st = states[ctrl]
            if ctrl in worked_this_slot:
                assigned_channel = next(channel for channel, c in chosen.items() if c == ctrl)
                if st["workedPrev"]:
                    st["consecutive"] += 1
                else:
                    st["consecutive"] = 1
                st["workedPrev"] = True
                st["restSlots"] = 0
                st["everWorked"] = True
                st["totalWorked"] += 1
                st["prevChannel"] = assigned_channel
            else:
                if st["workedPrev"] or st["everWorked"]:
                    st["restSlots"] += 1
                st["workedPrev"] = False
                st["consecutive"] = 0
                st["prevChannel"] = None

        slot_assignments[slot_idx] = chosen

    collapsed = []
    for ctrl in controllers:
        run_channel = None
        run_start = None

        for slot_idx in block_slots:
            current_channel = None
            for channel, assigned_ctrl in slot_assignments[slot_idx].items():
                if assigned_ctrl == ctrl:
                    current_channel = channel
                    break

            if current_channel == run_channel and current_channel is not None:
                continue

            if run_channel is not None:
                collapsed.append(
                    {
                        "controller": ctrl,
                        "channel": run_channel,
                        "slotStart": run_start,
                        "slotEnd": slot_idx,
                    }
                )

            run_channel = current_channel
            run_start = slot_idx if current_channel is not None else None

        if run_channel is not None:
            collapsed.append(
                {
                    "controller": ctrl,
                    "channel": run_channel,
                    "slotStart": run_start,
                    "slotEnd": block_slots[-1] + 1,
                }
            )

    return {
        "block": block_name,
        "status": "ok",
        "reason": "",
        "assignments": collapsed,
        "uncovered": [],
    }


def _workload_slots_from_assignments(assignments):
    totals = defaultdict(int)
    for item in assignments:
        totals[item["controller"]] += item["slotEnd"] - item["slotStart"]
    return totals


def _max_open_in_slots(block_slots, open_by_slot):
    return max((len(open_by_slot[idx]) for idx in block_slots), default=0)


def _required_block1_controllers(block_slots, open_by_slot):
    union_open = set()
    for idx in block_slots:
        union_open.update(open_by_slot[idx])
    return len(union_open)


def _schedule_half_with_count(prefix, controller_count, block1_name, block2_name, block_slots, open_by_slot):
    controllers = _build_controller_ids(prefix, controller_count)
    if not controllers:
        return {"status": "infeasible", "controllers": controllers, "blocks": []}

    best_ok = None
    last_fail = None

    # Try cyclic controller-order rotations and keep the most balanced result.
    for shift in range(len(controllers)):
        rotated = controllers[shift:] + controllers[:shift]
        b1 = _schedule_block1(block1_name, block_slots[block1_name], open_by_slot, rotated)
        if b1["status"] != "ok":
            last_fail = {"status": "infeasible", "controllers": controllers, "blocks": [b1]}
            continue

        initial_totals = _workload_slots_from_assignments(b1["assignments"])
        b2 = _schedule_block2(
            block2_name,
            block_slots[block2_name],
            open_by_slot,
            rotated,
            initial_worked_slots=initial_totals,
        )
        if b2["status"] != "ok":
            last_fail = {"status": "infeasible", "controllers": controllers, "blocks": [b1, b2]}
            continue

        totals = defaultdict(int)
        for k, v in initial_totals.items():
            totals[k] += v
        for k, v in _workload_slots_from_assignments(b2["assignments"]).items():
            totals[k] += v
        for ctrl in controllers:
            totals.setdefault(ctrl, 0)

        max_slots = max(totals.values()) if totals else 0
        min_slots = min(totals.values()) if totals else 0
        gap = max_slots - min_slots
        fairness_key = (gap, max_slots, shift)

        candidate = {
            "status": "ok",
            "controllers": controllers,
            "blocks": [b1, b2],
            "fairnessKey": fairness_key,
            "gapSlots": gap,
        }
        if best_ok is None or candidate["fairnessKey"] < best_ok["fairnessKey"]:
            best_ok = candidate

    if best_ok is not None:
        return {
            "status": "ok",
            "controllers": best_ok["controllers"],
            "blocks": best_ok["blocks"],
            "gapSlots": best_ok["gapSlots"],
        }

    return last_fail or {"status": "infeasible", "controllers": controllers, "blocks": []}


def _find_minimum_feasible_half(prefix, available_count, block1_name, block2_name, block_slots, open_by_slot):
    available = int(available_count)
    if available < 0:
        raise ValueError("Controller count cannot be negative")

    lower_bound = max(
        _required_block1_controllers(block_slots[block1_name], open_by_slot),
        _max_open_in_slots(block_slots[block2_name], open_by_slot),
    )

    if available < lower_bound:
        return {
            "status": "infeasible",
            "reason": f"Available controllers ({available}) below minimum required ({lower_bound})",
            "result": None,
            "minimumRequired": lower_bound,
        }

    min_feasible_count = None
    best_attempt = None
    best_key = None

    for count in range(lower_bound, available + 1):
        attempt = _schedule_half_with_count(
            prefix,
            count,
            block1_name,
            block2_name,
            block_slots,
            open_by_slot,
        )
        if attempt["status"] == "ok":
            if min_feasible_count is None:
                min_feasible_count = count
            # Fairness-first optimization, then smaller controller count.
            key = (attempt.get("gapSlots", 0), count)
            if best_attempt is None or key < best_key:
                best_attempt = attempt
                best_key = key

    if best_attempt is not None:
        return {
            "status": "ok",
            "reason": "",
            "result": best_attempt,
            "minimumRequired": lower_bound,
            "minimumFeasibleCount": min_feasible_count,
            "selectedCount": len(best_attempt["controllers"]),
            "selectedGapSlots": best_attempt.get("gapSlots", 0),
        }

    return {
        "status": "infeasible",
        "reason": f"No feasible schedule found up to available controllers ({available})",
        "result": None,
        "minimumRequired": lower_bound,
        "minimumFeasibleCount": 0,
        "selectedCount": 0,
        "selectedGapSlots": 0,
    }


def _infeasible_half_result(reason):
    return {
        "status": "infeasible",
        "reason": reason,
        "result": None,
        "minimumRequired": 0,
        "minimumFeasibleCount": 0,
        "selectedCount": 0,
        "selectedGapSlots": 0,
    }


def _choose_best_split(total_controllers, block_slots, open_by_slot):
    best = None
    infeasible_reasons = []
    first_half_lower_bound = max(
        _required_block1_controllers(block_slots["first_half_block_1"], open_by_slot),
        _max_open_in_slots(block_slots["first_half_block_2"], open_by_slot),
    )
    second_half_lower_bound = max(
        _required_block1_controllers(block_slots["second_half_block_1"], open_by_slot),
        _max_open_in_slots(block_slots["second_half_block_2"], open_by_slot),
    )

    minimum_total_required = first_half_lower_bound + second_half_lower_bound
    if total_controllers < minimum_total_required:
        reason = (
            f"No feasible night split for totalControllers={total_controllers}. "
            f"Minimum required with current channel timings is {minimum_total_required} "
            f"({first_half_lower_bound} first-half + {second_half_lower_bound} second-half)."
        )
        return _infeasible_half_result(reason), _infeasible_half_result(reason), (0, 0)

    # Only evaluate splits that can satisfy each half's lower bound.
    for first_available in range(first_half_lower_bound, total_controllers - second_half_lower_bound + 1):
        second_available = total_controllers - first_available

        first_half = _find_minimum_feasible_half(
            "f",
            first_available,
            "first_half_block_1",
            "first_half_block_2",
            block_slots,
            open_by_slot,
        )
        second_half = _find_minimum_feasible_half(
            "s",
            second_available,
            "second_half_block_1",
            "second_half_block_2",
            block_slots,
            open_by_slot,
        )

        if first_half["status"] != "ok" or second_half["status"] != "ok":
            if first_half["status"] != "ok":
                infeasible_reasons.append(first_half["reason"])
            if second_half["status"] != "ok":
                infeasible_reasons.append(second_half["reason"])
            continue

        used_total = first_half["selectedCount"] + second_half["selectedCount"]
        gap_key = max(first_half["selectedGapSlots"], second_half["selectedGapSlots"])
        split_balance = abs(first_half["selectedCount"] - second_half["selectedCount"])

        # Objective:
        # 1) minimize used controllers
        # 2) minimize workload gap
        # 3) prefer balanced split
        key = (used_total, gap_key, split_balance, first_available)
        candidate = (key, first_half, second_half, first_available, second_available)
        if best is None or candidate[0] < best[0]:
            best = candidate

    if best is None:
        reason = infeasible_reasons[0] if infeasible_reasons else "No feasible first/second-half split for total controllers"
        return _infeasible_half_result(reason), _infeasible_half_result(reason), (0, 0)

    _, first_half, second_half, first_available, second_available = best
    return first_half, second_half, (first_available, second_available)


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


def _run_night_schedule(payload):
    total_controllers_raw = payload.get("totalControllers")
    first_half_controllers = payload.get("firstHalfControllers", 0)
    second_half_controllers = payload.get("secondHalfControllers", 0)
    channel_closures = payload.get("channelClosures", [])

    closures = _normalize_closures(channel_closures)
    edges, open_by_slot = _build_open_channels_by_slot(closures)

    block_slots = {
        name: _slot_range_to_indexes(start, end)
        for name, (start, end) in BLOCKS.items()
    }

    selected_split = (int(first_half_controllers), int(second_half_controllers))
    if total_controllers_raw is not None:
        total_controllers = int(total_controllers_raw)
        if total_controllers < 15 or total_controllers > 17:
            raise ValueError("Total night controllers must be between 15 and 17")

        first_half, second_half, selected_split = _choose_best_split(total_controllers, block_slots, open_by_slot)
        first_half_controllers = selected_split[0]
        second_half_controllers = selected_split[1]
    else:
        first_half = _find_minimum_feasible_half(
            "f",
            first_half_controllers,
            "first_half_block_1",
            "first_half_block_2",
            block_slots,
            open_by_slot,
        )
        second_half = _find_minimum_feasible_half(
            "s",
            second_half_controllers,
            "second_half_block_1",
            "second_half_block_2",
            block_slots,
            open_by_slot,
        )

    block_results = []
    if first_half["status"] == "ok":
        block_results.extend(first_half["result"]["blocks"])
    else:
        block_results.extend(
            [
                {
                    "block": "first_half_block_1",
                    "status": "infeasible",
                    "reason": first_half["reason"],
                    "assignments": [],
                    "uncovered": [],
                },
                {
                    "block": "first_half_block_2",
                    "status": "infeasible",
                    "reason": first_half["reason"],
                    "assignments": [],
                    "uncovered": [],
                },
            ]
        )

    if second_half["status"] == "ok":
        block_results.extend(second_half["result"]["blocks"])
    else:
        block_results.extend(
            [
                {
                    "block": "second_half_block_1",
                    "status": "infeasible",
                    "reason": second_half["reason"],
                    "assignments": [],
                    "uncovered": [],
                },
                {
                    "block": "second_half_block_2",
                    "status": "infeasible",
                    "reason": second_half["reason"],
                    "assignments": [],
                    "uncovered": [],
                },
            ]
        )

    status = "ok" if all(item["status"] == "ok" for item in block_results) else "infeasible"

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
        "status": status,
        "edges": edges,
        "controllerPools": {
            "firstHalf": first_half["result"]["controllers"] if first_half["status"] == "ok" else [],
            "secondHalf": second_half["result"]["controllers"] if second_half["status"] == "ok" else [],
        },
        "optimization": {
            "selectionMode": "totalControllers" if total_controllers_raw is not None else "halfControllers",
            "requestedControllers": {
                "firstHalf": int(first_half_controllers),
                "secondHalf": int(second_half_controllers),
            },
            "requestedTotalControllers": int(total_controllers_raw) if total_controllers_raw is not None else int(first_half_controllers) + int(second_half_controllers),
            "selectedSplitAvailable": {
                "firstHalf": selected_split[0],
                "secondHalf": selected_split[1],
            },
            "minimumRequiredLowerBound": {
                "firstHalf": first_half["minimumRequired"],
                "secondHalf": second_half["minimumRequired"],
            },
            "minimumFeasibleControllers": {
                "firstHalf": first_half.get("minimumFeasibleCount", 0),
                "secondHalf": second_half.get("minimumFeasibleCount", 0),
            },
            "optimizedControllersUsed": {
                "firstHalf": len(first_half["result"]["controllers"]) if first_half["status"] == "ok" else 0,
                "secondHalf": len(second_half["result"]["controllers"]) if second_half["status"] == "ok" else 0,
            },
            "workloadGapHours": {
                "firstHalf": (first_half.get("selectedGapSlots", 0) * SLOT_MINUTES) / 60,
                "secondHalf": (second_half.get("selectedGapSlots", 0) * SLOT_MINUTES) / 60,
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

    return schedule, controller_order, NIGHT_START, NIGHT_END
