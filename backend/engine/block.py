from .templates import generate_2_3_grid, generate_3_5_grid, generate_1_2_grid
from .optimizer import solve_4_7_block
from .utils import round5

class BlockGenerator:

    def __init__(self, controllers, positions, start, end):
        self.controllers = controllers
        self.positions = positions
        self.start = start
        self.end = end
        self.total = end - start

    def generate(self, pattern_type):

        count = len(self.controllers)

        if pattern_type == "4:7":
            return solve_4_7_block(
                self.controllers,
                self.positions,
                self.start,
                self.end,
            )

        if pattern_type == "2:3":
            half_slot = round5(self.total / (3 * count))
        elif pattern_type == "3:5":
            half_slot = round5(self.total / (2 * count))
        elif pattern_type == "1:2":
            half_slot=round5(self.total/(3*count))
        else:
            raise ValueError("Unknown pattern")

        time_points = self._build_time_points(half_slot)

        half_slots = len(time_points) - 1

        if pattern_type == "2:3":
            grid = generate_2_3_grid(self.controllers, half_slots)
        elif pattern_type == "3:5":
            grid = generate_3_5_grid(self.controllers, half_slots)
        elif pattern_type == "1:2":
            grid= generate_1_2_grid(self.controllers, half_slots)

        return self._build_schedule(grid, time_points)

    def _build_time_points(self, half_slot):
        points = [self.start]
        current = self.start
        while current < self.end:
            current += half_slot
            points.append(min(current, self.end))
        return points

    def _build_schedule(self, grid, time_points):
        schedules = {c: [] for c in self.controllers}

        for p, column in enumerate(grid):
            i = 0
            while i < len(column):
                controller = column[i]
                j = i + 1
                while j < len(column) and column[j] == controller:
                    j += 1

                schedules[controller].append(
                    (self.positions[p], time_points[i], time_points[j])
                )
                i = j

        return schedules
