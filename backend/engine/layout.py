def get_layout(p,n):
    if p==7:
        if n==12:
            return [
                {"pattern":"4:7","size":7, "pos": 4},
                {"pattern":"3:5","size":5, "pos": 3},
                
            ]
        elif n==13:
            return [
                {"pattern":"4:7","size":7,"pos":4},
                {"pattern":"1:2","size":2,"pos":1},
                {"pattern":"1:2","size":2,"pos":1},
                {"pattern":"1:2","size":2,"pos":1},
            ]
        elif n==11:
            return [
                {"pattern":"1:2","size":2,"pos":1},
                {"pattern":"2:3","size":3,"pos":2},
                {"pattern":"2:3","size":3,"pos":2},
                {"pattern":"2:3","size":3,"pos":2},
            ]
    if p==8:
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

        elif n==14:
             return [
            {"pattern": "1:2", "size": 2, "pos": 1},
            {"pattern": "1:2", "size": 2, "pos": 1},
            {"pattern": "1:2", "size": 2, "pos": 1},
            {"pattern": "1:2", "size": 2, "pos": 1},
            {"pattern": "1:2", "size": 2, "pos": 1},
            {"pattern": "1:2", "size": 2, "pos": 1},
            {"pattern": "1:2", "size": 2, "pos": 1},
        ]

        else:
            raise ValueError("Unsupported strength")