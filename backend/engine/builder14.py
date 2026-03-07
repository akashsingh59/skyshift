def generate_14_schedule(controllers, positions, start, end):
   

    assert len(controllers) == 14
    assert len(positions) == 8

    PRIMARY = 65
    CONTRIB = 30
    MIN_REST_BEFORE_CONTRIB = 5
    MIN_REST_BEFORE_PRIMARY = 30

    total = end - start
    primary_blocks_count = total // PRIMARY  # should be 6
    assert primary_blocks_count == 6, "Shift must fit 6 primary blocks"

    # -------------------------
    # 1️⃣ Build primary schedule
    # -------------------------

    primary_blocks = []
    for i in range(primary_blocks_count):
        s = start + i * PRIMARY
        e = s + PRIMARY
        primary_blocks.append((s, e))

    # Pair controllers into 7 channels
    pairs = [controllers[i:i+2] for i in range(0, 14, 2)]

    schedule = {c: [] for c in controllers}

    # Assign alternating primary blocks
    for block_index, (block_start, block_end) in enumerate(primary_blocks):
        for channel_index, pair in enumerate(pairs):
            active = pair[block_index % 2]
            schedule[active].append(
                (positions[channel_index], block_start, block_end)
            )

    # Helper to fetch primary intervals for a controller
    def primary_intervals(controller):
        return sorted(
            [(s, e) for (pos, s, e) in schedule[controller]
             if pos in positions[:7]],
            key=lambda x: x[0]
        )

    # -------------------------
    # 2️⃣ Build contributory schedule (time-driven)
    # -------------------------

    contributory_windows = []
    t = start
    while t + CONTRIB <= end:
        contributory_windows.append((t, t + CONTRIB))
        t += CONTRIB

    for (c_start, c_end) in contributory_windows:

        assigned = False

        for controller in controllers:

            primaries = primary_intervals(controller)

            # Check not overlapping primary
            overlaps_primary = any(
                not (c_end <= p_start or c_start >= p_end)
                for (p_start, p_end) in primaries
            )
            if overlaps_primary:
                continue

            # Find previous and next primary relative to this contributory window
            previous_primary_end = None
            next_primary_start = None

            for (p_start, p_end) in primaries:
                if p_end <= c_start:
                    previous_primary_end = p_end
                if p_start >= c_end and next_primary_start is None:
                    next_primary_start = p_start

            # Enforce ≥5 min rest after previous primary
            if previous_primary_end is not None:
                if c_start - previous_primary_end < MIN_REST_BEFORE_CONTRIB:
                    continue

            # Enforce ≥30 min rest before next primary
            if next_primary_start is not None:
                if next_primary_start - c_end < MIN_REST_BEFORE_PRIMARY:
                    continue

            # If all constraints satisfied → assign
            schedule[controller].append(
                (positions[7], c_start, c_end)
            )
            assigned = True
            break  # move to next contributory window

        if not assigned:
            raise RuntimeError(
                f"P8 could not be manned during {c_start}-{c_end}"
            )

    return schedule