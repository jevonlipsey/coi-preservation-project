from gerrychain.accept import always_accept
import random
import math

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

def optimized_tcp_proportional_50(partition):
    """
    optimizing tcp using simulated annealing, a statistical model for finding global max
    """
    current_score = partition["unweighted_tcp_score"]
    previous_score = partition.parent["unweighted_tcp_score"] if partition.parent else 0

    if current_score >= previous_score:
        return True
    beta = 50
    delta = current_score - previous_score

    prob = math.exp(beta * delta)
    return random.random() < prob

def optimized_tcp_proportional_100(partition):
    """
    optimizing tcp using simulated annealing, a statistical model for finding global max
    """
    current_score = partition["unweighted_tcp_score"]
    previous_score = partition.parent["unweighted_tcp_score"] if partition.parent else 0

    if current_score >= previous_score:
        return True
    beta = 100
    delta = current_score - previous_score

    prob = math.exp(beta * delta)
    return random.random() < prob

def optimized_tcp_proportional_200(partition):
    """
    optimizing tcp using simulated annealing, a statistical model for finding global max
    """
    current_score = partition["unweighted_tcp_score"]
    previous_score = partition.parent["unweighted_tcp_score"] if partition.parent else 0

    if current_score >= previous_score:
        return True
    beta = 200
    delta = current_score - previous_score

    prob = math.exp(beta * delta)
    return random.random() < prob

def optimized_tcp_margin_10_40(partition):
    current_score = partition["unweighted_tcp_score"]
    previous_score = partition.parent["unweighted_tcp_score"] if partition.parent else 0

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

def optimized_tcp_margin_20_50(partition):
    current_score = partition["unweighted_tcp_score"]
    previous_score = partition.parent["unweighted_tcp_score"] if partition.parent else 0

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
            accepted = random.random() < 0.2
        else:
            accepted = random.random() < 0.5
    return accepted

def optimized_tcp_margin_30_60(partition):
    current_score = partition["unweighted_tcp_score"]
    previous_score = partition.parent["unweighted_tcp_score"] if partition.parent else 0

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
            accepted = random.random() < 0.2
        else:
            accepted = random.random() < 0.5
    return accepted

def optimized_tcp_simple_25(partition):
    current_score = partition["unweighted_tcp_score"]
    previous_score = partition.parent["unweighted_tcp_score"] if partition.parent else 0

    accepted = False
    if current_score > previous_score:
        accepted = True
    else:
         accepted = random.random() < 0.25
    return accepted

def optimized_tcp_simple_50(partition):
    current_score = partition["unweighted_tcp_score"]
    previous_score = partition.parent["unweighted_tcp_score"] if partition.parent else 0

    accepted = False
    if current_score > previous_score:
        accepted = True
    else:
         accepted = random.random() < 0.5
    return accepted

def optimized_tcp_simple_75(partition):
    current_score = partition["unweighted_tcp_score"]
    previous_score = partition.parent["unweighted_tcp_score"] if partition.parent else 0

    accepted = False
    if current_score > previous_score:
        accepted = True
    else:
         accepted = random.random() < 0.75
    return accepted

def optimized_cs_simple_25(partition):
    current_score = partition["communities_split"]
    previous_score = partition.parent["communities_split"] if partition.parent else 0

    accepted = False
    if current_score < previous_score:
        accepted = True
    else:
         accepted = random.random() < 0.25
    return accepted

def optimized_cs_simple_50(partition):
    current_score = partition["communities_split"]
    previous_score = partition.parent["communities_split"] if partition.parent else 0

    accepted = False
    if current_score < previous_score:
        accepted = True
    else:
         accepted = random.random() < 0.5
    return accepted

def optimized_cs_simple_75(partition):
    current_score = partition["communities_split"]
    previous_score = partition.parent["communities_split"] if partition.parent else 0

    accepted = False
    if current_score < previous_score:
        accepted = True
    else:
         accepted = random.random() < 0.75
    return accepted

def optimized_cs_proportional_50(partition):
    """
    optimizing tcp using simulated annealing, a statistical model for finding global max
    """
    current_score = partition["communities_split"]
    previous_score = partition.parent["communities_split"] if partition.parent else 0

    if current_score <= previous_score:
        return True
    beta = 50
    delta = current_score - previous_score

    prob = math.exp(beta * delta)
    return random.random() < prob

def optimized_cs_proportional_100(partition):
    """
    optimizing tcp using simulated annealing, a statistical model for finding global max
    """
    current_score = partition["communities_split"]
    previous_score = partition.parent["communities_split"] if partition.parent else 0

    if current_score <= previous_score:
        return True
    beta = 100
    delta = current_score - previous_score

    prob = math.exp(beta * delta)
    return random.random() < prob

def optimized_cs_proportional_200(partition):
    """
    optimizing tcp using simulated annealing, a statistical model for finding global max
    """
    current_score = partition["communities_split"]
    previous_score = partition.parent["communities_split"] if partition.parent else 0

    if current_score <= previous_score:
        return True
    beta = 200
    delta = current_score - previous_score

    prob = math.exp(beta * delta)
    return random.random() < prob

def optimized_cs_margin_10_40(partition):
    current_score = partition["communities_split"]
    previous_score = partition.parent["communities_split"] if partition.parent else 0

    margin = (
        abs(current_score - previous_score) / previous_score
        if previous_score != 0
        else 0
    )

    accepted = False
    if current_score < previous_score:
        accepted = True
    else:
        if margin > 6:
            accepted = random.random() < 0.1
        else:
            accepted = random.random() < 0.4
    return accepted

def optimized_cs_margin_20_50(partition):
    current_score = partition["communities_split"]
    previous_score = partition.parent["communities_split"] if partition.parent else 0

    margin = (
        abs(current_score - previous_score) / previous_score
        if previous_score != 0
        else 0
    )

    accepted = False
    if current_score < previous_score:
        accepted = True
    else:
        if margin > 6:
            accepted = random.random() < 0.2
        else:
            accepted = random.random() < 0.5
    return accepted

def optimized_cs_margin_30_60(partition):
    current_score = partition["communities_split"]
    previous_score = partition.parent["communities_split"] if partition.parent else 0

    margin = (
        abs(current_score - previous_score) / previous_score
        if previous_score != 0
        else 0
    )

    accepted = False
    if current_score < previous_score:
        accepted = True
    else:
        if margin > 6:
            accepted = random.random() < 0.3
        else:
            accepted = random.random() < 0.6
    return accepted


STRATEGIES = {
    "neutral": always_accept,
    "optimized_tcp": optimized_tcp,
    "unoptimized": unoptimized_tcp,
    "optimized_cs": optimized_cs,
    "optimized_se": optimized_se,
    "optimized_sr": optimized_sr,
    "optimized_es": optimized_es,
    "proportional_50": optimized_tcp_proportional_50,
    "proportional_100": optimized_tcp_proportional_100,
    "proportional_200": optimized_tcp_proportional_200,
    "margin_10_40": optimized_tcp_margin_10_40,
    "margin_20_50": optimized_tcp_margin_20_50,
    "margin_30_60": optimized_tcp_margin_30_60,
    "simple_25": optimized_tcp_simple_25,
    "simple_50": optimized_tcp_simple_50,
    "simple_75": optimized_tcp_simple_75,
    "proportional_cs_50": optimized_cs_proportional_50,
    "proportional_cs_100": optimized_cs_proportional_100,
    "proportional_cs_200": optimized_cs_proportional_200,
    "margin_cs_10_40": optimized_cs_margin_10_40,
    "margin_cs_20_50": optimized_cs_margin_20_50,
    "margin_cs_30_60": optimized_cs_margin_30_60,
    "simple_cs_25": optimized_cs_simple_25,
    "simple_cs_50": optimized_cs_simple_50,
    "simple_cs_75": optimized_cs_simple_75,
}
