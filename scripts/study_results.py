"""Prints every number used in the README results table for one project.

Usage:
    python scripts/study_results.py <project_id>

With Docker:
    docker compose exec web python scripts/study_results.py <project_id>
"""
import os
import sys
from statistics import mean, median

# make "from app import app" work when this file is run from the scripts folder
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from core.models import Project, Task, Annotation, AIPrediction
from quality.stats import get_project_stats
from quality.agreement import get_agreement
from quality.scores import get_annotator_scores


## returns (mean, median, count) in seconds, or None when there is no data
def summarize(seconds):
    if not seconds:
        return None
    return round(mean(seconds), 1), round(median(seconds), 1), len(seconds)


def show(label, value):
    print(f"  {label}: {value}")


def main():
    project_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    with app.app_context():
        project = Project.query.get(project_id)
        if project is None:
            print("No project with id", project_id)
            return

        s = get_project_stats(project_id)
        pairs, confused = get_agreement(project_id)

        print(f"\nProject {project_id}: {project.name} ({project.task_type})")

        print("\nProgress")
        show("tasks (without gold)", s["total"])
        show("completed", s["status"]["completed"])
        show("needs review", s["status"]["needs_review"])
        show("human labels", s["labels"])
        show("tasks decided by the reviewer", s["reviewer_fixed"])

        print("\nAI acceptance")
        if s["acceptance"] is None:
            show("acceptance rate", "n/a (no labels were shown a suggestion)")
        else:
            show("acceptance rate", f"{s['acceptance']}% of {s['shown']} labels")

        # time per label, computed from the raw rows so the median can be shown too
        task_ids = [t.id for t in Task.query.filter_by(project_id=project_id, is_gold=False).all()]
        with_ai = []
        without_ai = []
        if task_ids:
            ai_task_ids = {p.task_id for p in AIPrediction.query.filter(AIPrediction.task_id.in_(task_ids)).all()}
            for a in Annotation.query.filter(Annotation.task_id.in_(task_ids)).all():
                if a.task_id in ai_task_ids and a.time_taken_ms:
                    seconds = a.time_taken_ms / 1000
                    if a.accepted_ai is not None:
                        with_ai.append(seconds)
                    else:
                        without_ai.append(seconds)

        print("\nTime per label (seconds)")
        for name, values in (("with AI suggestion", with_ai), ("without AI suggestion", without_ai)):
            result = summarize(values)
            if result is None:
                show(name, "n/a")
            else:
                show(name, f"mean {result[0]}, median {result[1]}, n = {result[2]}")
        if s["saved_pct"] is None:
            show("time saved (mean)", "n/a (needs labels from both groups)")
        else:
            show("time saved (mean)", f"{s['saved_pct']}%")

        print("\nQuality checks")
        show("wrong gold answers", f"{s['gold_wrong']} of {s['gold_total']}")
        show("labels under 1 second", s["too_fast"])

        print("\nCohen's kappa per pair")
        if not pairs:
            print("  no labels yet")
        for p in pairs:
            kappa = "n/a" if p["kappa"] is None else p["kappa"]
            print(f"  {p['a']} vs {p['b']}: kappa {kappa}, agreement {p['agree']}%, tasks {p['n']}")

        print("\nMost confused labels (humans only)")
        if not confused:
            print("  no disagreements")
        for (l1, l2), count in confused:
            print(f"  {l1} / {l2}: {count}")

        print("\nAnnotator scores (all projects)")
        for r in get_annotator_scores():
            print(f"  {r['username']}: labels {r['total']}, gold {r['gold_correct']}/{r['gold_total']}, "
                  f"too fast {r['fast']}, weight {r['weight']}")
        print()


if __name__ == "__main__":
    main()