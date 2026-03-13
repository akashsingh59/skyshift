from .layout import get_layout
from .block import BlockGenerator


def generate_14_schedule(controllers, positions, start, end):
    n=len(controllers)
    p=len(positions)
    CONTRIB = 30
    MIN_REST_BEFORE_CONTRIB = 5
    MIN_REST_BEFORE_PRIMARY = 30
       
    
    layout = get_layout(p,n)

    pointer = 0
    pos_pointer = 0
    full_schedule = {}

    for block in layout:

        size = block["size"]
        pos_count = block["pos"]

        block_controllers = controllers[pointer:pointer+size]
        block_positions = positions[pos_pointer:pos_pointer+pos_count]

        pointer += size
        pos_pointer += pos_count

        generator = BlockGenerator(
            block_controllers,
            block_positions,
            start,
            end
        )

        schedule = generator.generate(block["pattern"])
        full_schedule.update(schedule)

    return full_schedule