def generate_2_3_grid(controllers, half_slots):
    count = len(controllers)
    return [
        [controllers[(i // 2) % count] for i in range(half_slots)],
        [controllers[(1 + (i + 1) // 2) % count] for i in range(half_slots)],
    ]

def generate_1_2_grid(controllers, half_slots):
    count = len(controllers)
    return [
        [controllers[(i) % count] for i in range(half_slots)],
        
    ]

def generate_3_5_grid(controllers, half_slots):
    count = len(controllers)
    stride2 = [(2 * i) % count for i in range(count)]
    stride_seq = [controllers[i] for i in stride2]
    inverse = [stride2.index(i) for i in range(count)]

    grid = []
    for p in range(3):
        start_idx = inverse[p]
        column = [
            stride_seq[(start_idx + i // 2) % count]
            for i in range(half_slots)
        ]
        grid.append(column)

    return grid