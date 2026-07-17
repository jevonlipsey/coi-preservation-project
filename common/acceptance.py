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


def optimized_tcp(partition):
    global optimized_accepted_track
    current_score = partition["weighted_tcp_score"]
    previous_score = partition.parent["weighted_tcp_score"] if partition.parent else 0

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
    legal neutral: aggressively optimizes to keep county splits low, targeting ~9.
    """
    current_splits = partition["county_split_count"]
    previous_splits = (
        partition.parent["county_split_count"] if partition.parent else current_splits
    )

    # If we hit the Enacted target, accept everything to explore the "legal" space
    if current_splits <= 9:
        return True

    # If it improves the splits (lowers them), always accept
    if current_splits < previous_splits:
        return True

    # If splits stay exactly the same, accept most of the time to allow lateral exploration
    if current_splits == previous_splits:
        return random.random() < 0.80

    # If splits get WORSE (increase), strongly reject
    # 5% chance to accept a worse map just to avoid getting permanently stuck
    return random.random() < 0.05


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
    compromising: optimizing tcp with margin heuristic, but hard capping county splits > 14
    """
    splits = partition["county_split_count"]
    current_tcp = partition["weighted_tcp_score"]
    previous_tcp = partition.parent["weighted_tcp_score"] if partition.parent else 0

    # hard legal ceiling for county splits
    if splits > 14:
        return False

    # if splits are legal, use the standard TCP margin heuristic
    margin = abs(current_tcp - previous_tcp) / previous_tcp if previous_tcp != 0 else 0

    if current_tcp > previous_tcp:
        return True
    else:
        if margin > 0.01:
            return random.random() < 0.1
        else:
            return random.random() < 0.4


STRATEGIES = {
    "neutral": always_accept,
    "baseline_counties": baseline_counties,
    "optimized_tcp": optimized_tcp,
    "optimized_tcp_sa": optimized_tcp_sa,
    "optimized_both": optimized_both,
    "unoptimized": unoptimized_tcp,
    "optimized_cs": optimized_cs,
    "optimized_se": optimized_se,
    "optimized_sr": optimized_sr,
    "optimized_es": optimized_es,
}
