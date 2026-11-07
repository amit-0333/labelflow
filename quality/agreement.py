from collections import defaultdict, Counter
from core.models import Task, Annotation, AIPrediction, User


## pure function: two lists of labels in, kappa out (-1 to 1)
## returns None when kappa cannot be calculated
def cohens_kappa(a, b):
    n = len(a)
    if n == 0:
        return None

    observed = sum(1 for x, y in zip(a, b) if x == y) / n

    ## chance agreement: how often they would match by luck
    expected = 0
    for label in set(a) | set(b):
        expected += (a.count(label) / n) * (b.count(label) / n)

    if expected == 1:
        return None

    return round((observed - expected) / (1 - expected), 2)


## returns (pairs, confused)
## pairs: kappa for every two annotators, and for AI vs each annotator
## confused: label pairs people disagree on most
def get_agreement(project_id):
    tasks = Task.query.filter_by(project_id=project_id, is_gold=False).all()
    task_ids = [t.id for t in tasks]
    if not task_ids:
        return [], []

    names = {u.id: u.username for u in User.query.all()}

    ## votes[task_id] = {"admin": "spam", "vivek": "not spam", "AI": "spam"}
    votes = defaultdict(dict)
    for a in Annotation.query.filter(Annotation.task_id.in_(task_ids)).all():
        votes[a.task_id][names[a.user_id]] = a.label
    for p in AIPrediction.query.filter(AIPrediction.task_id.in_(task_ids)).order_by(AIPrediction.id).all():
        votes[p.task_id]["AI"] = p.label

    pair_labels = defaultdict(lambda: ([], []))
    confusion = Counter()

    for task_id, v in votes.items():
        people = sorted(v)
        for i in range(len(people)):
            for j in range(i + 1, len(people)):
                p1 = people[i]
                p2 = people[j]
                pair_labels[(p1, p2)][0].append(v[p1])
                pair_labels[(p1, p2)][1].append(v[p2])

                ## most-confused labels: humans only
                if p1 != "AI" and p2 != "AI" and v[p1] != v[p2]:
                    confusion[tuple(sorted((v[p1], v[p2])))] += 1

    pairs = []
    for (p1, p2), (a, b) in pair_labels.items():
        same = sum(1 for x, y in zip(a, b) if x == y)
        pairs.append({
            "a": p1,
            "b": p2,
            "n": len(a),
            "agree": round(same / len(a) * 100),
            "kappa": cohens_kappa(a, b),
        })

    return pairs, confusion.most_common()