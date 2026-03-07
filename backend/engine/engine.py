from .layout import get_layout
from .block import BlockGenerator
from .builder14 import generate_14_schedule

def generate_day_schedule(controllers, positions, start, end):
    n=len(controllers)
    if n == 14:
       return generate_14_schedule(controllers, positions, start, end)
    
    layout = get_layout(n)

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