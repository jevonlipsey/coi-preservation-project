from gerrychain.accept import always_accept
import random

optimized_accepted_track = []
unoptimized_accepted_track = []

'''
def optimized_tcp(partition):
    global optimized_accepted_track
    current_score = partition["weighted_tcp_score"]
    previous_score = partition.parent["weighted_tcp_score"] if partition.parent else 0
    desired_tcp = partition.graph.graph.graph.get("DESIRED_TCP", 0.5)

    accepted = False
    # floor
    if current_score >= desired_tcp:
        accepted = True
    # favorably accept upward movement
    elif current_score > previous_score:
        accepted = random.random() < 0.8
    # avoid getting stuck
    else:
        accepted = random.random() < 0.05
    # counter for acceptance
    optimized_accepted_track.append(accepted)
    return accepted
'''

def unoptimized_tcp(partition):
    global unoptimized_accepted_track
    current_score = partition["weighted_tcp_score"]
    # Default to 1.0 (perfect) if no parent, so the first step always looks "worse"
    previous_score = partition.parent["weighted_tcp_score"] if partition.parent else 1.0

    accepted = False
    # accept all terrible maps
    if current_score <= 0.40:
        accepted = True
    # favorably accept downward movement
    elif current_score < previous_score:
        accepted = random.random() < 0.8
    # avoid getting stuck
    else:
        accepted = random.random() < 0.05

    unoptimized_accepted_track.append(accepted)
    return accepted

def optimized_tcp(partition):
    global optimized_accepted_track
    current_score = partition["weighted_tcp_score"]
    previous_score = partition.parent["weighted_tcp_score"] if partition.parent else 0
    #desired_tcp = partition.graph.graph.graph.get("DESIRED_TCP", 0.5)

    margin = (
        abs(current_score - previous_score) / previous_score
        if previous_score != 0
        else 0
    )

    print(margin)
    accepted = False
    if current_score > previous_score:
        accepted = True
    else:
        if margin > 0.05:
            accepted = random.random() < 0.1
        else:
            accepted = random.random() < 0.4
    return accepted

def optimized_cs(partition):
    #global optimized_accepted_track
    current_score = partition["communities_split"]
    previous_score = partition.parent["communities_split"] if partition.parent else 0
    #desired_tcp = partition.graph.graph.graph.get("DESIRED_TCP", 0.5)

    margin = (
        abs(current_score - previous_score) 
        if previous_score != 0
        else 0
    )

    accepted = False
    if current_score < previous_score:
        accepted = True
    else:
        if margin > 2:
            accepted = random.random() < 0.1
        else:
            accepted = random.random() < 0.4
    return accepted

def optimized_se(partition):
    global optimized_accepted_track
    current_score = partition["shannon_entropy"]
    previous_score = partition.parent["shannon_entropy"] if partition.parent else 0
    #desired_tcp = partition.graph.graph.graph.get("DESIRED_TCP", 0.5)

    margin = (
        abs(current_score - previous_score) / previous_score
        if previous_score != 0
        else 0
    )

    accepted = False
    if current_score > previous_score:
        accepted = True
    else:
        if margin > 0.1:
            accepted = random.random() < 0.1
        else:
            accepted = random.random() < 0.4
    return accepted

def optimized_sr(partition):
    global optimized_accepted_track
    current_score = partition["sr_entropy"]
    previous_score = partition.parent["sr_entropy"] if partition.parent else 0
    #desired_tcp = partition.graph.graph.graph.get("DESIRED_TCP", 0.5)

    margin = (
        abs(current_score - previous_score) / previous_score
        if previous_score != 0
        else 0
    )

    accepted = False
    if current_score > previous_score:
        accepted = True
    else:
        if margin > 0.01:
            accepted = random.random() < 0.1
        else:
            accepted = random.random() < 0.4
    return accepted


def optimized_se(partition):
    global optimized_accepted_track
    current_score = partition["sr_entropy"]
    previous_score = partition.parent["sr_entropy"] if partition.parent else 0
    #desired_tcp = partition.graph.graph.graph.get("DESIRED_TCP", 0.5)

    margin = (
        abs(current_score - previous_score) / previous_score
        if previous_score != 0
        else 0
    )

    accepted = False
    if current_score > previous_score:
        accepted = True
    else:
        if margin > 0.01:
            accepted = random.random() < 0.1
        else:
            accepted = random.random() < 0.4
    return accepted


STRATEGIES = {
    'neutral': always_accept,
    'optimized': optimized_tcp,
    'unoptimized': unoptimized_tcp,
    'optimized_cs': optimized_cs,
    'optimized_se': optimized_se,
    'optimized_sr': optimized_sr
}