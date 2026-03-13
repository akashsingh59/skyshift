from .layout import get_layout
from .block import BlockGenerator


def generate_14_schedule(controllers, positions, start, end):
    assert len(controllers) == 14, "This builder requires 14 controllers"
    assert len(positions) == 8, "This builder requires 8 positions"

    CONTRIB = 30
    SWITCH_GAP = 5
    VACANT_CONTROLLER = "VACANT"

    layout = get_layout(len(positions), len(controllers))

    pointer = 0
    pos_pointer = 0
    full_schedule = {controller: [] for controller in controllers}
    full_schedule[VACANT_CONTROLLER] = []

    # 1. Build the 7 primary channels first.
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

    def primary_intervals(controller):
        return sorted(
            [
                (block_start, block_end)
                for position, block_start, block_end in full_schedule[controller]
                if position in primary_positions
            ],
            key=lambda item: item[0],
        )

    # 2. Build legal rest periods for each controller.
    # A contributory slot can sit inside off-duty time as long as:
    # - it starts at least 5 min after the previous primary ends
    # - it ends at least 5 min before the next primary starts
    def rest_periods(controller):
        primaries = primary_intervals(controller)
        rests = []

        if not primaries:
            rests.append((start, end))
            return rests

        # Before first primary
        first_start = primaries[0][0]
        rest_start = start
        rest_end = first_start - SWITCH_GAP
        if rest_start < rest_end:
            rests.append((rest_start, rest_end))

        # Between primaries
        for i in range(len(primaries) - 1):
            prev_end = primaries[i][1]
            next_start = primaries[i + 1][0]

            rest_start = prev_end + SWITCH_GAP
            rest_end = next_start - SWITCH_GAP

            if rest_start < rest_end:
                rests.append((rest_start, rest_end))

        # After last primary
        last_end = primaries[-1][1]
        rest_start = last_end + SWITCH_GAP
        rest_end = end
        if rest_start < rest_end:
            rests.append((rest_start, rest_end))

        return rests

    controller_rest_map = {
        controller: rest_periods(controller)
        for controller in controllers
    }

    # 3. Build fixed 30-minute contributory slots across the shift.
    contributory_slots = []
    t = start
    while t + CONTRIB <= end:
        contributory_slots.append((t, t + CONTRIB))
        t += CONTRIB

    # 4. Greedily assign each slot to the first remaining controller whose
    #    legal rest period fully contains that slot. One controller gets at most one slot.
    remaining = list(controllers)

    for slot_start, slot_end in contributory_slots:
        assigned_controller = None

        for controller in remaining:
            rests = controller_rest_map[controller]
            if any(rest_start <= slot_start and slot_end <= rest_end for rest_start, rest_end in rests):
                assigned_controller = controller
                break

        if assigned_controller is None:
            full_schedule[VACANT_CONTROLLER].append(
                (contributory_position, slot_start, slot_end)
            )
        else:
            full_schedule[assigned_controller].append(
                (contributory_position, slot_start, slot_end)
            )
            remaining.remove(assigned_controller)

    for controller in full_schedule:
        full_schedule[controller].sort(key=lambda item: item[1])

    return full_schedule
