import json
import random
import os

def load_world(filepath):
    with open(filepath, "r") as f:
        return json.load(f)

def save_placement(data, file_name, output_dir="data"):
    filename = f"{file_name}.json"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    print(f"saved {file_name}.json")

def generate_packed(json_data):
    N = int(len(json_data["nodes"]) ** 0.5)
    if N == 5:
        # 10 voters packed into 2 districts
        for node in json_data["nodes"]:
            if node["x"] in [0, 1]:
                node["MCURE"] = 1   
            else:
                node["MCURE"] = 0
    elif N == 8:
        # 26 voters packed into 3 districts + 2 left over in 4th 
        for node in json_data["nodes"]:
            x, y = node["x"], node["y"]
            if x in [0, 1, 2] or (x == 3 and y in [0, 1]):
                node["MCURE"] = 1
            else:
                node["MCURE"] = 0
    return json_data

def generate_cracked(json_data):
    N = int(len(json_data["nodes"]) ** 0.5)
    if N == 5:
        # 2 voters spread across 5 districts
        for node in json_data["nodes"]:
            if node["y"] in [0, 1]:
                node["MCURE"] = 1
            else:
                node["MCURE"] = 0
    elif N == 8:
        # 3 voters in columns 2-7, 4 voters in columns 0 and 1 (26 total)
        for node in json_data["nodes"]:
            x, y = node["x"], node["y"]
            if y in [0, 1, 2] or (y == 3 and x in [0, 1]):
                node["MCURE"] = 1
            else:
                node["MCURE"] = 0
    return json_data

def generate_gerried(json_data):
    # get 3/5 seats
    '''
    x 0 1 2 3 4
    y
    0 M M M M .
    1 M M M . .
    2 M M M . .
    3 . . . . .
    4 . . . . .
    '''
    N = int(len(json_data["nodes"]) ** 0.5)
    if N == 5:
        for node in json_data["nodes"]:
            x, y = node["x"], node["y"]
            if x in [0, 1, 2] and y in [0, 1, 2]:
                node["MCURE"] = 1
            elif x == 3 and y == 0:
                node["MCURE"] = 1
            else:
                node["MCURE"] = 0
    elif N == 8:
        # 5 voters in columns 0-4 1 voter in col 5
        for node in json_data["nodes"]:
            x, y = node["x"], node["y"]
            if x in [0, 1, 2, 3, 4] and y in [0, 1, 2, 3, 4]:
                node["MCURE"] = 1
            elif x == 5 and y == 0:
                node["MCURE"] = 1
            else:
                node["MCURE"] = 0
    return json_data

def generate_center(json_data):
    '''
    x 0 1 2 3 4
    y
    0 . . M . .
    1 . M M M .
    2 . M M M .
    3 . M M M .
    4 . . . . .
    '''
    N = int(len(json_data["nodes"]) ** 0.5)
    if N == 5:
        center_coords = [
            (1, 1), (2, 1), (3, 1),
            (1, 2), (2, 2), (3, 2),
            (1, 3), (2, 3), (3, 3),
            (2, 0)
        ]
    elif N == 8:
        center_coords = [
            (3, 1), (4, 1),
            (2, 2), (3, 2), (4, 2), (5, 2),
            (0, 3), (1, 3), (2, 3), (3, 3), (4, 3), (5, 3), (6, 3), (7, 3),
            (1, 4), (2, 4), (3, 4), (4, 4), (5, 4), (6, 4),
            (2, 5), (3, 5), (4, 5), (5, 5),
            (3, 6), (4, 6)
        ]
    else:
        center_coords = []

    for node in json_data["nodes"]:
        if (node["x"], node["y"]) in center_coords:
            node["MCURE"] = 1
        else:
            node["MCURE"] = 0
    return json_data

def generate_random(json_data):
    N = int(len(json_data["nodes"]) ** 0.5)
    n_voters = 10 if N == 5 else 26
    
    node_indices = list(range(len(json_data["nodes"])))
    selected_indices = set(random.sample(node_indices, n_voters))
    
    for i, node in enumerate(json_data["nodes"]):
        if i in selected_indices:
            node["MCURE"] = 1
        else:
            node["MCURE"] = 0
    return json_data

'''
print('5x5 maps generating..')
for strategy, generator in [
    ("5_packed", generate_packed),
    ("5_cracked", generate_cracked),
    ("5_gerried", generate_gerried),
    ("5_center", generate_center),
    ("5_random", generate_random)
    ]:
    template = load_world("data/5by5.json")
    save_placement(generator(template), 5, strategy)
'''

gerrymandria = load_world("data/gerrymandria.json")
gerrymandria = generate_random(gerrymandria)
save_placement(gerrymandria, "gerrymandria_random")

print('done.')
