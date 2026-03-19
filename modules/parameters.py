params = {}

with open("keys.txt", "r") as file:
    lines = file.read().splitlines()
    for line in lines:
        x = line.split("=", 1)
        if len(x) >= 2:
            params[x[0]] = x[1].strip()
