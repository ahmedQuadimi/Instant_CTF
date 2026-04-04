import math


def calculate_points(max_points, min_points, decay_factor, solves_count) -> int:
    return max(
        min_points,
        round(max_points * math.exp(-decay_factor * solves_count)),
    )


def calculate_linear_points(max_points, min_points, decay_factor, solves_count) -> int:
    return max(
        min_points,
        round(max_points * (1 - (decay_factor * solves_count))),
    )


def calculate_event_points(
    scoring_strategy, max_points, min_points, decay_factor, solves_count
) -> int:
    if scoring_strategy == "STATIC":
        return max_points
    if scoring_strategy == "LINEAR":
        return calculate_linear_points(
            max_points, min_points, decay_factor, solves_count
        )
    return calculate_points(max_points, min_points, decay_factor, solves_count)
