from gerrychain.accept import always_accept
import random

optimized_accepted_track = []
unoptimized_accepted_track = []


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

STRATEGIES = {
    'neutral': always_accept,
    'optimized': optimized_tcp,
    'unoptimized': unoptimized_tcp
}