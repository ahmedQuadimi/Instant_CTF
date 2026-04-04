import math


def calculate_points(max_points, min_points, decay_factor, solves_count) -> int:
    return max(
        min_points,
        round(max_points * math.exp(-decay_factor * solves_count)),
    )
