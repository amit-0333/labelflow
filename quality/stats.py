from core.models import Task, Annotation, AIPrediction
from quality.scores import FAST_MS


## average seconds, or None if there is no data
def avg_seconds(values):
    if not values:
        return None
    return round(sum(values) / len(values) / 1000, 1)


def get_project_stats(project_id):
    tasks = Task.query.filter_by(project_id=project_id).all()
    task_by_id = {t.id: t for t in tasks}
    ids = list(task_by_id) or [0]

    normal = [t for t in tasks if not t.is_gold]
    status = {"pending": 0, "in_progress": 0, "needs_review": 0, "completed": 0}
    for t in normal:
        status[t.status] = status.get(t.status, 0) + 1

    annotations = Annotation.query.filter(Annotation.task_id.in_(ids)).all()
    ai_task_ids = {p.task_id for p in AIPrediction.query.filter(AIPrediction.task_id.in_(ids)).all()}

    ## acceptance rate: only labels where the suggestion was shown
    shown = [a for a in annotations if a.accepted_ai is not None]
    acceptance = None
    if shown:
        acceptance = round(sum(1 for a in shown if a.accepted_ai) / len(shown) * 100)

    ## time with the AI suggestion vs without, on tasks that have an AI label
    with_ai = []
    without_ai = []
    for a in annotations:
        t = task_by_id[a.task_id]
        if t.is_gold or a.task_id not in ai_task_ids or not a.time_taken_ms:
            continue
        if a.accepted_ai is not None:
            with_ai.append(a.time_taken_ms)
        else:
            without_ai.append(a.time_taken_ms)

    avg_with = avg_seconds(with_ai)
    avg_without = avg_seconds(without_ai)
    saved_pct = None
    if avg_with is not None and avg_without:
        saved_pct = round((avg_without - avg_with) / avg_without * 100)

    ## bad labels caught
    gold_total = 0
    gold_wrong = 0
    too_fast = 0
    for a in annotations:
        t = task_by_id[a.task_id]
        if t.is_gold:
            gold_total += 1
            if a.label != t.gold_label:
                gold_wrong += 1
        if a.time_taken_ms is not None and a.time_taken_ms < FAST_MS:
            too_fast += 1

    reviewer_fixed = sum(1 for t in normal if t.final_source == "reviewer")

    return {
        "total": len(normal),
        "status": status,
        "labels": len(annotations),
        "acceptance": acceptance,
        "shown": len(shown),
        "avg_with": avg_with,
        "n_with": len(with_ai),
        "avg_without": avg_without,
        "n_without": len(without_ai),
        "saved_pct": saved_pct,
        "gold_total": gold_total,
        "gold_wrong": gold_wrong,
        "too_fast": too_fast,
        "reviewer_fixed": reviewer_fixed,
    }