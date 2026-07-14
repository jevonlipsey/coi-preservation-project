from gerrychain.accept import always_accept
import random

from sympy import partition

optimized_accepted_track = []
unoptimized_accepted_track = []

"""
def optimized_tcp(partition):
    global optimized_accepted_track
    current_score = partition["weighted_tcp_score"]
    previous_score = partition.parent["weighted_tcp_score"] if partition.parent else 0
    # desired_tcp = partition.graph.graph.graph.get("DESIRED_TCP", 0.5)

    ## hill climb
    accepted = False
    # favorably accept upward movement
    if current_score > previous_score:
        accepted = random.random() < 0.8
    # avoid getting stuck
    else:
        accepted = random.random() < 0.1
    # counter for acceptance
    optimized_accepted_track.append(accepted)
    return accepted
"""


def unoptimized_tcp(partition):
    global unoptimized_accepted_track
    current_score = partition["weighted_tcp_score"]
    previous_score = partition.parent["weighted_tcp_score"] if partition.parent else 1.0

    accepted = False
    # accept all terrible maps
    # favorably accept downward movement
    if current_score < previous_score:
        accepted = random.random() < 0.8
    # avoid getting stuck
    else:
        accepted = random.random() < 0.1

    unoptimized_accepted_track.append(accepted)
    return accepted


def optimized_tcp(partition):
    current_score = partition["weighted_tcp_score"]
    previous_score = partition.parent["weighted_tcp_score"] if partition.parent else 0

    accepted = False
    margin = (
        abs(current_score - previous_score) / previous_score
        if previous_score != 0
        else 0
    )

    if current_score > previous_score:
        accepted = True
    else:
        if margin > 0.05:
            accepted = random.random() < 0.1
        else:
            accepted = random.random() < 0.4
    return accepted


STRATEGIES = {
    "neutral": always_accept,
    "optimized": optimized_tcp,
    "unoptimized": unoptimized_tcp,
}
