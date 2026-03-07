from .engine import generate_day_schedule  # your function
from .constants import POSITIONS

def build_controllers(n):
    return [f"C{i+1}" for i in range(n)]

def generate_schedule(shift, total_controllers):

    controllers = build_controllers(total_controllers)

    if shift == "morning":
        start = 120
        end = 510
    elif shift == "afternoon":
        start = 510
        end = 900
    else:
        raise ValueError("Day scheduler only handles morning/afternoon")

    schedule = generate_day_schedule(
        controllers,
        POSITIONS,
        start,
        end
    )

    return {
        "shift": shift,
        "positions": schedule
    }
