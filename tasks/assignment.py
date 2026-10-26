from core.db import db
from core.models import Project, Task, Assignment


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

    ## 2. tasks this user has already taken (never give the same task twice)
    my_task_ids = [a.task_id for a in Assignment.query.filter_by(user_id=user_id).all()]

    ## 3. candidate tasks, "in_progress" first so tasks get finished before new ones start
    candidates = (
        Task.query
        .filter(Task.project_id == project_id)
        .filter(Task.status.in_(["pending", "in_progress"]))
        .filter(~Task.id.in_(my_task_ids))
        .order_by(Task.status.asc(), Task.id.asc())
        .limit(50)
        .all()
    )

    ## 4. try each candidate: lock it, count slots again, claim it
    for candidate in candidates:
        ## FOR UPDATE: other people wait here until we commit
        task = Task.query.filter_by(id=candidate.id).with_for_update().first()

        ## locking read, so we see the latest count
        taken = Assignment.query.filter_by(task_id=task.id).with_for_update().count()

        if taken >= needed:
            db.session.rollback()  ## release the lock, try the next one
            continue

        assignment = Assignment(task_id=task.id, user_id=user_id, status="assigned")
        db.session.add(assignment)
        task.status = "in_progress"
        db.session.commit()  ## commit releases the lock
        return task

    return None