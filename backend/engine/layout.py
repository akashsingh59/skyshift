def get_layout(n):

    if n == 12:
        return [
            {"pattern": "2:3", "size": 3, "pos": 2},
            {"pattern": "2:3", "size": 3, "pos": 2},
            {"pattern": "2:3", "size": 3, "pos": 2},
            {"pattern": "2:3", "size": 3, "pos": 2},
        ]

    elif n == 13:
        return [
            {"pattern": "3:5", "size": 5, "pos": 3},
            {"pattern": "3:5", "size": 5, "pos": 3},
            {"pattern": "2:3", "size": 3, "pos": 2},
        ]

    else:
        raise ValueError("Unsupported strength")