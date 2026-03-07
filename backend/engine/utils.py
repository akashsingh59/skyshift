# utils.py

def round5(value):
    return int(5 * round(float(value) / 5))


def mins_to_hhmm(mins):
    hours = mins // 60
    minutes = mins % 60
    return f"{hours:02d}:{minutes:02d}"


def hhmm_to_mins(hhmm):
    h, m = map(int, hhmm.split(":"))
    return h * 60 + m


def format_duration(mins):
    hours = mins // 60
    minutes = mins % 60
    return f"{hours}h {minutes}m"


def validate_shift_window(start_mins, end_mins, min_length=60):
    if end_mins <= start_mins:
        return False
    if (end_mins - start_mins) < min_length:
        return False
    return True


def validate_no_overlap(schedule):
    for controller, blocks in schedule.items():
        blocks = sorted(blocks, key=lambda x: x[1])
        for i in range(1, len(blocks)):
            if blocks[i][1] < blocks[i-1][2]:
                raise ValueError(f"Overlap detected for {controller}")