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
    "TWR-M",
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
    "TWR-M",
    "SMC-S",
    "SMC-M",
    "TWR-S2",
]
        elif n == 13:
             return [
    "TWR-N",
    "SMC-M",
    "CLD-1",
    "TWR-M",
    "SMC-S",
    "SMC-N",
    "TWR-S2",
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