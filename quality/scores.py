from core.models import User, Task, Annotation

## a label made faster than this (in milliseconds) counts as "too fast"
FAST_MS = 1000


## pure function: numbers in, weight out (0 to 1)
def calc_weight(gold_total, gold_correct, total_labels, fast_labels):
    if gold_total > 0:
        weight = gold_correct / gold_total
    else:
        weight = 1.0  ## no gold answers yet, trust by default

    if total_labels > 0:
        weight = weight * (1 - fast_labels / total_labels)

    return round(max(0.0, min(1.0, weight)), 2)


## one row per annotator
def get_annotator_scores():
    rows = []
    for user in User.query.all():
        annotations = Annotation.query.filter_by(user_id=user.id).all()
        if len(annotations) == 0:
            continue

        gold_total = 0
        gold_correct = 0
        fast_labels = 0

        for a in annotations:
            task = Task.query.get(a.task_id)
            if task.is_gold:
                gold_total += 1
                if a.label == task.gold_label:
                    gold_correct += 1
            if a.time_taken_ms is not None and a.time_taken_ms < FAST_MS:
                fast_labels += 1

        rows.append({
            "username": user.username,
            "total": len(annotations),
            "gold_total": gold_total,
            "gold_correct": gold_correct,
            "fast": fast_labels,
            "weight": calc_weight(gold_total, gold_correct, len(annotations), fast_labels),
        })
    return rows