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
    "CLD-1(4:7)",
    "SMC-N(4:7)",
    "TWR-N(4:7)",
    "TWR-M(4:7)",
    "TWR-S2(3:5)",
    "SMC-M(3:5)",
    "SMC-S(3:5)",
]
        elif n == 13:
             return [
    "TWR-N(4:7)",
    "SMC-M(4:7)",
    "TWR-M(4:7)",
    "SMC-S(4:7)",
    "TWR-S2(1:2)",
    "CLD-1(1:2)",
    "SMC-N(1:2)",
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
