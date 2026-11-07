import random
from core.db import db
from core.models import Project, Task, Assignment

## chance (0 to 1) that an annotator gets a hidden gold question
## 1.0 is for testing only, change to 0.2 afterwards
GOLD_CHANCE = 0.2


## picks one task for this user and saves the claim
## returns the Task, or None if nothing is left
def claim_next_task(user_id, project_id):
    project = Project.query.get(project_id)
    needed = project.annotators_per_item

    ## 1. user already has an unfinished task, give the same one back
    open_assignment = (
        Assignment.query
        .join(Task, Assignment.task_id == Task.id)
        .filter(Assignment.user_id == user_id)
        .filter(Assignment.status == "assigned")
        .filter(Task.project_id == project_id)
        .first()
    )
    if open_assignment:
        return Task.query.get(open_assignment.task_id)

    ## 2. tasks this user has already taken
    my_task_ids = [a.task_id for a in Assignment.query.filter_by(user_id=user_id).all()]

    ## 3. sometimes give a hidden gold question this user has not seen
    if random.random() < GOLD_CHANCE:
        gold_tasks = Task.query.filter_by(project_id=project_id, is_gold=True).all()
        for gold in gold_tasks:
            if gold.id not in my_task_ids:
                db.session.add(Assignment(task_id=gold.id, user_id=user_id, status="assigned"))
                db.session.commit()
                return gold

    ## 4. normal tasks, "in_progress" first so tasks get finished before new ones start
    candidates = (
        Task.query
        .filter(Task.project_id == project_id)
        .filter(Task.is_gold == False)
        .filter(Task.status.in_(["pending", "in_progress"]))
        .filter(~Task.id.in_(my_task_ids))
        .order_by(Task.status.asc(), Task.id.asc())
        .limit(50)
        .all()
    )

    ## 5. try each candidate: lock it, count slots again, claim it
    for candidate in candidates:
        task = Task.query.filter_by(id=candidate.id).with_for_update().first()
        taken = Assignment.query.filter_by(task_id=task.id).with_for_update().count()

        if taken >= needed:
            db.session.rollback()
            continue

        assignment = Assignment(task_id=task.id, user_id=user_id, status="assigned")
        db.session.add(assignment)
        task.status = "in_progress"
        db.session.commit()
        return task

    return None