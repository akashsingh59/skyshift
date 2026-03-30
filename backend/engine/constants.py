POSITIONS = [1, 2, 3, 4, 5, 6, 7, 8]

NIGHT_POSITION_LABELS = {
    1: "TWR-M",
    2: "TWR-N",
    3: "CLD-1",
    4: "SMC-S",
    5: "SMC-N",
    6: "TWR-S1",
    7: "SMC-M",
    8: "TWR-S2",
}

NIGHT_POSITION_ORDER = [NIGHT_POSITION_LABELS[channel] for channel in POSITIONS]


def get_positions(p,n):
    if p>8 or p<7:
         return [
    "TWR-M",
    "SMC-N",
    "CLD-1",
    "TWR-M",
    "SMC-S",
    "TWR-S1",
    "SMC-M",
    "TWR-S2",
]
    if p==8:
        if n == 13:
            return  [
    "TWR-M",
    "TWR-N",
    "CLD-1",
    "SMC-S",
    "SMC-N",
    "TWR-S1",
    "SMC-M",
    "TWR-S2",
]
        elif n == 12 :
            return [
    "TWR-M",
    "SMC-N",
    "CLD-1",
    "TWR-N",
    "SMC-S",
    "TWR-S1",
    "SMC-M",
    "TWR-S2",
]
        else:
             return [
    "TWR-M",
    "SMC-N",
    "CLD-1",
    "TWR-N",
    "SMC-S",
    "TWR-S1",
    "TWR-S2",
    "SMC-M",
]
        
    if p==7:
        if n == 11:
            return  [
    "TWR-M",
    "SMC-S",
    "CLD-1",
    "TWR-N",
    "SMC-N",
    "SMC-M",
    "TWR-S2",
]
        elif n ==12 :
             return [
    "TWR-M",
    "SMC-N",
    "CLD-1",
    "TWR-N",
    "TWR-S2",
    "SMC-M",
    "SMC-S",
]
        elif n == 13:
             return [
    "TWR-N",
    "SMC-M",
    "TWR-M",
    "SMC-S",
    "TWR-S2",
    "CLD-1",
    "SMC-N",
]
        


POSITIONS_3_5 = [
    "TWR-M",
    "TWR-N",
    "CLD-1",
    "SMC-S",
    "SMC-N",
    "TWR-S1",
    "SMC-M",
    "TWR-S2",
]
POSITIONS_2_3 = [
    "TWR-M",
    "SMC-N",
    "CLD-1",
    "TWR-M",
    "SMC-S",
    "TWR-S1",
    "SMC-M",
    "TWR-S2",
]
