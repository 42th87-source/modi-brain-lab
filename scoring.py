import statistics


def get_valid_reaction_times(rows, condition):
    times = []

    for row in rows:
        if row["input_condition"] == condition and row["valid"] is True:
            times.append(float(row["reaction_time_ms"]))

    return times


def calculate_task1_summary(rows):
    button_times = get_valid_reaction_times(rows, "button")
    gyro_times = get_valid_reaction_times(rows, "gyro")

    result = {
        "button_valid_count": len(button_times),
        "gyro_valid_count": len(gyro_times),
        "button_median": None,
        "gyro_median": None,
        "input_difference": None
    }

    if len(button_times) > 0:
        result["button_median"] = statistics.median(button_times)

    if len(gyro_times) > 0:
        result["gyro_median"] = statistics.median(gyro_times)

    if result["button_median"] is not None and result["gyro_median"] is not None:
        result["input_difference"] = result["gyro_median"] - result["button_median"]

    return result
