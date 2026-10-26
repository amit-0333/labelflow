from flask import Blueprint, render_template, request, redirect
from flask_login import current_user
from core.db import db
from core.models import Project, Task, Assignment, Annotation
from auth.decorators import role_required
from tasks.assignment import claim_next_task

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

    return redirect('/start_labeling/' + str(project.id))