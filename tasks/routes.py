from flask import Blueprint, render_template, request, redirect
from flask_login import current_user
from core.db import db
from core.models import Project, Task, Assignment, Annotation
from auth.decorators import role_required
from tasks.assignment import claim_next_task
from tasks.review import check_task
from core.models import ReviewDecision, User


tasks_bp = Blueprint("tasks", __name__)


## annotator or admin clicks "Start labeling", the app picks a task for them
@tasks_bp.route('/start_labeling/<int:project_id>')
@role_required("admin", "annotator")
def start_labeling(project_id):
    project = Project.query.get_or_404(project_id)
    task = claim_next_task(current_user.id, project_id)
    return render_template('task.html', task=task, project=project)

## save the label, mark the assignment as done, then go to the next task
@tasks_bp.route('/perform_submit_label', methods=['POST'])
@role_required("admin", "annotator")
def perform_submit_label():
    task_id = int(request.form.get('task_id'))
    label = request.form.get('label')
    time_taken = request.form.get('time_taken_ms')

    task = Task.query.get_or_404(task_id)
    project = Project.query.get(task.project_id)

    ## the user must really own this task and the label must be valid
    assignment = Assignment.query.filter_by(
        task_id=task_id, user_id=current_user.id, status="assigned"
    ).first()

    if assignment is None or label not in project.label_options:
        return redirect('/start_labeling/' + str(project.id))

    annotation = Annotation(
    task_id=task_id,
    user_id=current_user.id,
    label=label,
    time_taken_ms=int(time_taken) if time_taken else None
    )
    db.session.add(annotation)
    assignment.status = "submitted"
    db.session.commit()

    check_task(task_id)

    return redirect('/start_labeling/' + str(project.id))

## reviewer or admin: show all tasks that need a decision
@tasks_bp.route('/review')
@role_required("admin", "reviewer")
def review_queue():
    tasks = Task.query.filter_by(status="needs_review").all()

    ## for each task, collect who gave which label
    items = []
    for t in tasks:
        project = Project.query.get(t.project_id)
        votes = []
        for a in Annotation.query.filter_by(task_id=t.id).all():
            user = User.query.get(a.user_id)
            votes.append({"username": user.username, "label": a.label})
        items.append({"task": t, "labels": project.label_options, "votes": votes})

    return render_template('review.html', items=items)


## reviewer picks the final label, this decision is final
@tasks_bp.route('/perform_review', methods=['POST'])
@role_required("admin", "reviewer")
def perform_review():
    task_id = int(request.form.get('task_id'))
    label = request.form.get('label')

    task = Task.query.get_or_404(task_id)
    project = Project.query.get(task.project_id)

    ## only tasks waiting for review, and only a valid label
    if task.status != "needs_review" or label not in project.label_options:
        return redirect('/review')

    decision = ReviewDecision(task_id=task_id, reviewer_id=current_user.id, label=label)
    db.session.add(decision)

    task.final_label = label
    task.final_source = "reviewer"
    task.status = "completed"
    db.session.commit()

    return redirect('/review')