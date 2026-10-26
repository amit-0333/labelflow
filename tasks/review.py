from core.db import db
from core.models import Project, Task, Annotation


## looks at one task and decides: still waiting, completed, or needs_review
def check_task(task_id):
    task = Task.query.get(task_id)
    project = Project.query.get(task.project_id)

    ## the reviewer already decided, never change it
    if task.final_source == "reviewer":
        return

    annotations = Annotation.query.filter_by(task_id=task_id).all()

    ## not everyone has labeled yet, so keep waiting
    if len(annotations) < project.annotators_per_item:
        return

    labels = set()
    for a in annotations:
        labels.add(a.label)

    if len(labels) == 1:
        ## everyone chose the same label
        task.final_label = annotations[0].label
        task.final_source = "consensus"
        task.status = "completed"
    else:
        ## people disagree, the reviewer must decide
        task.status = "needs_review"

    db.session.commit()