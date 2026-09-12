"""Deterministic training adjustments for pure coach mode."""


def working_sets(exercise):
    return [
        item
        for item in exercise.get("sets", [])
        if item.get("set_type", "working") == "working"
    ]


def session_signature(exercise):
    sets = working_sets(exercise)
    top_weight = max(
        (item.get("weight_kg", 0) or 0 for item in sets),
        default=0,
    )
    reps_at_top = sum(
        item.get("reps", 0) or 0
        for item in sets
        if (item.get("weight_kg", 0) or 0) == top_weight
    )
    return top_weight, reps_at_top


def interruption_adjustment(days_since_last):
    if days_since_last is None or days_since_last < 7:
        return 0
    if days_since_last <= 14:
        return -10
    if days_since_last <= 30:
        return -20
    return None


def set_effort_rpe(item):
    if item.get("rpe") is not None:
        return item["rpe"]
    if item.get("rir") is not None:
        return 10 - item["rir"]
    return None


def _has_two_large_declines(history):
    if len(history) < 3:
        return False
    loads = [session_signature(item)[0] for item in history[-3:]]
    return loads[1] < loads[0] * 0.9 and loads[2] < loads[1] * 0.9


def _has_three_stagnant_occurrences(history):
    if len(history) < 3:
        return False
    signatures = [session_signature(item) for item in history[-3:]]
    return signatures[1] <= signatures[0] and signatures[2] <= signatures[1]


def recommend_exercise(history, days_since_last):
    """Return a JSON-safe next-action recommendation for one exercise."""
    if not history:
        return {
            "action": "build_baseline",
            "reason": "没有可比较的历史记录，先用轻重量建立基线。",
            "load_adjustment_percent": 0,
        }

    history = sorted(history, key=lambda item: item.get("date", ""))
    latest = history[-1]
    pain = latest.get("pain", {})
    if (pain.get("severity", 0) or 0) > 0:
        return {
            "action": "stop_or_substitute",
            "reason": "最近一次记录存在疼痛，停止或更换为无痛动作。",
            "load_adjustment_percent": 0,
        }

    interruption = interruption_adjustment(days_since_last)
    if interruption is None:
        return {
            "action": "rebuild_baseline",
            "reason": "距离上次训练超过 30 天，用一次训练重新建立基线。",
            "load_adjustment_percent": None,
        }

    if _has_two_large_declines(history):
        action = "deload"
        reason = "连续两次最高工作重量下降超过 10%，安排减量训练。"
    elif _has_three_stagnant_occurrences(history):
        action = "review_stagnation"
        reason = "连续三次重量和同重量次数都没有进步，检查技术、休息和动作适配。"
    else:
        sets = working_sets(latest)
        efforts = [set_effort_rpe(item) for item in sets]
        known_efforts = [value for value in efforts if value is not None]
        reps = [item.get("reps", 0) or 0 for item in sets]
        if any(rep < 8 for rep in reps) or any(value >= 9 for value in known_efforts):
            action = "reduce_5_10_percent"
            reason = "最近一次未达到 8 次，或强度达到 RPE 9，降低 5%-10%。"
        elif (
            len(sets) >= 2
            and all(rep >= 12 for rep in reps)
            and len(known_efforts) == len(sets)
            and max(known_efforts) <= 8
        ):
            action = "increase_minimum"
            reason = "至少两个正式组达到 12 次且强度不高于 RPE 8，下次最小幅度加重。"
        else:
            action = "hold_add_reps"
            reason = "保持当前重量，优先把正式组次数提高到 12 次。"

    if interruption in (-10, -20):
        reason = f"停练间隔对应 {abs(interruption)}% 降重；{reason}"
        if action in {"increase_minimum", "hold_add_reps", "reduce_5_10_percent"}:
            action = "resume_reduced"

    return {
        "action": action,
        "reason": reason,
        "load_adjustment_percent": interruption,
    }
