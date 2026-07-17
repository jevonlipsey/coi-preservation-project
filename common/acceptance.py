from gerrychain.accept import always_accept
import random

optimized_accepted_track = []
unoptimized_accepted_track = []

"""
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
"""


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


"""
def optimized_tcp(partition):
    global optimized_accepted_track
    current_score = partition["weighted_tcp_score"]
    previous_score = partition.parent["weighted_tcp_score"] if partition.parent else 0
    # desired_tcp = partition.graph.graph.graph.get("DESIRED_TCP", 0.5)

    margin = (
        abs(current_score - previous_score) / previous_score
        if previous_score != 0
        else 0
    )

    accepted = [False, False, False, False, False]
    if current_score > previous_score:
        accepted[:] = [True]
    else:
        if margin > 0.01:
            accepted[0] = random.random() < 0.1
            accepted[1] = random.random() < 0.2
            accepted[2] = random.random() < 0.3
            accepted[3] = random.random() < 0.4
            accepted[4] = random.random() < 0.5
        else:
            accepted[0] = random.random() < 0.4
            accepted[1] = random.random() < 0.5
            accepted[2] = random.random() < 0.6
            accepted[3] = random.random() < 0.7
            accepted[4] = random.random() < 0.8
    return accepted
"""


def optimized_tcp(partition):
    global optimized_accepted_track
    current_score = partition["weighted_tcp_score"]
    previous_score = partition.parent["weighted_tcp_score"] if partition.parent else 0
    # desired_tcp = partition.graph.graph.graph.get("DESIRED_TCP", 0.5)

    margin = (
        abs(current_score - previous_score) / previous_score
        if previous_score != 0
        else 0
    )

    # print(margin)
    accepted = False
    for i in range(accepted):
        if current_score > previous_score:
            accepted = True
        else:
            if margin > 0.01:
                accepted = random.random() < 0.1
            else:
                accepted = random.random() < 0.4
    return accepted


def optimized_cs(partition):
    # global optimized_accepted_track
    current_score = partition["communities_split"]
    previous_score = partition.parent["communities_split"] if partition.parent else 0
    # desired_tcp = partition.graph.graph.graph.get("DESIRED_TCP", 0.5)

    margin = abs(current_score - previous_score) if previous_score != 0 else 0

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
    # desired_tcp = partition.graph.graph.graph.get("DESIRED_TCP", 0.5)

    margin = (
        abs(current_score - previous_score) / previous_score
        if previous_score != 0
        else 0
    )

    accepted = False
    if current_score < previous_score:
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
    # desired_tcp = partition.graph.graph.graph.get("DESIRED_TCP", 0.5)

    margin = (
        abs(current_score - previous_score) / previous_score
        if previous_score != 0
        else 0
    )

    accepted = False
    if current_score < previous_score:
        accepted = True
    else:
        if margin > 0.005:
            accepted = random.random() < 0.1
        else:
            accepted = random.random() < 0.4
    return accepted


def optimized_es(partition):
    global optimized_accepted_track
    current_score = partition["even_splits"]
    previous_score = partition.parent["even_splits"] if partition.parent else 0
    # desired_tcp = partition.graph.graph.graph.get("DESIRED_TCP", 0.5)

    margin = (
        abs(current_score - previous_score) / previous_score
        if previous_score != 0
        else 0
    )

    accepted = False
    if current_score < previous_score:
        accepted = True
    else:
        if margin > 0.1:
            accepted = random.random() < 0.1
        else:
            accepted = random.random() < 0.4
    return accepted


import math


def baseline_counties(partition):
    """
    legal neutral: targets the enacted split count of ~9.
    """
    splits = partition["county_split_count"]

    # if it's as good or better than the enacted plan, always accept
    if splits <= 9:
        return True

    # if it's worse, accept with decreasing probability (soft constraint)
    # 10 splits = 36% accept, 11 splits = 13% accept, 12 splits = 5% accept
    prob = math.exp(-(splits - 9))
    return random.random() < prob


def optimized_tcp_sa(partition):
    """
    optimizing tcp using simulated annealing, a statistical model for finding global max
    """
    current_score = partition["weighted_tcp_score"]
    previous_score = partition.parent["weighted_tcp_score"] if partition.parent else 0

    if current_score >= previous_score:
        return True

    # simulated annealing formula: exp(beta * delta)
    # higher beta = more likely to accept worse solutions, lower beta = less likely to accept worse solutions
    # 50 = hot, 100 = warm, 200 = cold
    beta = 100
    delta = current_score - previous_score

    prob = math.exp(beta * delta)
    return random.random() < prob


def optimized_both(partition):
    """
    compromising: optimizing tcp with simulated annealing, but penalizng for county splits > 9
    """
    splits = partition["county_split_count"]
    current_tcp = partition["weighted_tcp_score"]
    previous_tcp = partition.parent["weighted_tcp_score"] if partition.parent else 0

    # high splits = hard reject (+5)
    if splits > 14:
        return False

    # if splits are ok, use simmulated annealing on tcp
    if current_tcp >= previous_tcp:
        return True

    beta = 100
    delta = current_tcp - previous_tcp
    prob = math.exp(beta * delta)

    return random.random() < prob


STRATEGIES = {
    "neutral": always_accept,
    "baseline_counties": baseline_counties,
    "optimized_tcp": optimized_tcp_sa,
    "optimized_both": optimized_both,
    "unoptimized": unoptimized_tcp,
    "optimized_cs": optimized_cs,
    "optimized_se": optimized_se,
    "optimized_sr": optimized_sr,
    "optimized_es": optimized_es,
}
