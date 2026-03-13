from .layout import get_layout
from .block import BlockGenerator


def generate_14_schedule(controllers, positions, start, end):
    assert len(controllers) == 14, "This builder requires 14 controllers"
    assert len(positions) == 8, "This builder requires 8 positions"

    CONTRIB = 30
    MIN_REST_BEFORE_CONTRIB = 5
    MIN_REST_BEFORE_PRIMARY = 30

    layout = get_layout(len(positions), len(controllers))

    pointer = 0
    pos_pointer = 0
    full_schedule = {controller: [] for controller in controllers}

    # Build the fixed primary schedule first.
    for block in layout:
        size = block["size"]
        pos_count = block["pos"]

        block_controllers = controllers[pointer:pointer + size]
        block_positions = positions[pos_pointer:pos_pointer + pos_count]

        pointer += size
        pos_pointer += pos_count

        generator = BlockGenerator(
            block_controllers,
            block_positions,
            start,
            end,
        )
        schedule = generator.generate(block["pattern"])

        for controller, assignments in schedule.items():
            full_schedule[controller].extend(assignments)

    primary_positions = set(positions[:7])
    contributory_position = positions[7]

    def primary_intervals_for_controller(controller):
        return sorted(
            [
                (block_start, block_end)
                for position, block_start, block_end in full_schedule.get(controller, [])
                if position in primary_positions
            ],
            key=lambda interval: interval[0],
        )

    def slot_is_legal_for_controller(controller, slot_start, slot_end):
        primaries = primary_intervals_for_controller(controller)

        overlaps_primary = any(
            not (slot_end <= p_start or slot_start >= p_end)
            for p_start, p_end in primaries
        )
        if overlaps_primary:
            return False

        previous_primary_end = None
        next_primary_start = None

        for p_start, p_end in primaries:
            if p_end <= slot_start:
                previous_primary_end = p_end
            if p_start >= slot_end and next_primary_start is None:
                next_primary_start = p_start

        if previous_primary_end is not None:
            if slot_start - previous_primary_end < MIN_REST_BEFORE_CONTRIB:
                return False

        if next_primary_start is not None:
            if next_primary_start - slot_end < MIN_REST_BEFORE_PRIMARY:
                return False

        return True

    # Fixed 13 half-hour contributory slots covering the full shift.
    contributory_slots = []
    t = start
    while t < end:
        slot_end = min(t + CONTRIB, end)
        if slot_end - t != CONTRIB:
            raise RuntimeError("Shift length must be divisible into 30-minute contributory slots")
        contributory_slots.append((t, slot_end))
        t = slot_end

    # Build bipartite graph: slot index -> eligible controllers.
    slot_to_candidates = {}
    for slot_index, (slot_start, slot_end) in enumerate(contributory_slots):
        candidates = [
            controller
            for controller in controllers
            if slot_is_legal_for_controller(controller, slot_start, slot_end)
        ]
        slot_to_candidates[slot_index] = candidates

    # Match each slot to exactly one controller, each controller to at most one slot.
    assigned_controller_for_slot = {}
    assigned_slot_for_controller = {}

    def try_assign(slot_index, seen_controllers):
        for controller in slot_to_candidates[slot_index]:
            if controller in seen_controllers:
                continue
            seen_controllers.add(controller)

            if controller not in assigned_slot_for_controller:
                assigned_slot_for_controller[controller] = slot_index
                assigned_controller_for_slot[slot_index] = controller
                return True

            current_slot = assigned_slot_for_controller[controller]
            if try_assign(current_slot, seen_controllers):
                assigned_slot_for_controller[controller] = slot_index
                assigned_controller_for_slot[slot_index] = controller
                return True

        return False

    # Harder slots first reduces backtracking failures.
    slot_order = sorted(slot_to_candidates, key=lambda idx: len(slot_to_candidates[idx]))

    for slot_index in slot_order:
        if not try_assign(slot_index, set()):
            slot_start, slot_end = contributory_slots[slot_index]
            raise RuntimeError(
                f"Contributory channel cannot be manned for slot {slot_start}-{slot_end}"
            )

    # Append exactly one contributory assignment per matched controller.
    for slot_index, controller in assigned_controller_for_slot.items():
        slot_start, slot_end = contributory_slots[slot_index]
        full_schedule[controller].append((contributory_position, slot_start, slot_end))

    for controller in full_schedule:
        full_schedule[controller].sort(key=lambda item: item[1])

    return full_schedule
