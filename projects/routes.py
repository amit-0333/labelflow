from flask import Blueprint, render_template, request, redirect
from flask_login import current_user
from core.db import db
from core.models import Project, Task, AIPrediction
from auth.decorators import role_required
from projects.csv_parser import parse_csv
from jobs.queue import queue

projects_bp = Blueprint("projects", __name__)


## numbers shown on project cards and the project page
def get_counts(project_id):
    tasks = Task.query.filter_by(project_id=project_id, is_gold=False).all()
    total = len(tasks)
    completed = sum(1 for t in tasks if t.status == "completed")
    needs_review = sum(1 for t in tasks if t.status == "needs_review")
    ai_count = (
        AIPrediction.query
        .join(Task, AIPrediction.task_id == Task.id)
        .filter(Task.project_id == project_id)
        .count()
    )
    gold_count = Task.query.filter_by(project_id=project_id, is_gold=True).count()
    percent = round(completed / total * 100) if total else 0
    return {
        "total": total,
        "completed": completed,
        "needs_review": needs_review,
        "ai_count": ai_count,
        "gold_count": gold_count,
        "percent": percent,
    }


## show the project page with a message
def show_project(project, message=None):
    return render_template('project.html', project=project, c=get_counts(project.id), message=message)


## show all projects as cards
@projects_bp.route('/projects')
@role_required("admin", "annotator", "reviewer")
def projects():
    items = []
    for p in Project.query.order_by(Project.id.desc()).all():
        items.append({"project": p, "c": get_counts(p.id)})
    return render_template('projects.html', items=items)


## admin only: show the create project page
@projects_bp.route('/create_project')
@role_required("admin")
def create_project():
    return render_template('create_project.html')


## admin only: take form data and save the project
@projects_bp.route('/perform_create_project', methods=['POST'])
@role_required("admin")
def perform_create_project():
    name = request.form.get('name')
    task_type = request.form.get('task_type')
    description = request.form.get('description')
    guidelines = request.form.get('guidelines')
    labels_text = request.form.get('labels') or ''
    annotators_per_item = request.form.get('annotators_per_item')

    ## labels are fixed for pairwise and rating
    if task_type == "pairwise":
        label_options = ["A", "B"]
    elif task_type == "rating":
        label_options = ["1", "2", "3", "4", "5"]
    else:
        task_type = "classification"
        label_options = []
        for label in labels_text.split(','):
            label = label.strip()
            if label != '':
                label_options.append(label)
        if len(label_options) < 2:
            return render_template('create_project.html', message="Enter at least 2 labels, separated by commas")

    project = Project(
        name=name,
        task_type=task_type,
        description=description,
        guidelines=guidelines,
        label_options=label_options,
        annotators_per_item=int(annotators_per_item),
        created_by=current_user.id
    )
    db.session.add(project)
    db.session.commit()

    return redirect('/projects')


## show one project
@projects_bp.route('/project/<int:project_id>')
@role_required("admin", "annotator", "reviewer")
def project_page(project_id):
    project = Project.query.get_or_404(project_id)
    message = None
    if request.args.get('queued'):
        message = "AI pre-labeling started. Refresh in a few seconds to see the count."
    return show_project(project, message)


## admin only: read the CSV and save each row as a task
@projects_bp.route('/perform_upload_csv/<int:project_id>', methods=['POST'])
@role_required("admin")
def perform_upload_csv(project_id):
    project = Project.query.get_or_404(project_id)
    file = request.files.get('file')

    if file is None or file.filename == '':
        return show_project(project, "Choose a CSV file first")

    tasks, error = parse_csv(file, project.task_type)
    if error:
        return show_project(project, error)

    ## a gold_label must be one of the project labels
    for t in tasks:
        if t["gold_label"] and t["gold_label"] not in project.label_options:
            return show_project(project, "gold_label '" + t["gold_label"] + "' is not one of the project labels")

    for t in tasks:
        db.session.add(Task(
            project_id=project_id,
            text=t["text"],
            extra_data=t["extra"],
            is_gold=bool(t["gold_label"]),
            gold_label=t["gold_label"]
        ))
    db.session.commit()

    return show_project(project, str(len(tasks)) + " tasks uploaded")


## admin only: send the pre-labeling job to the worker
@projects_bp.route('/perform_prelabel/<int:project_id>')
@role_required("admin")
def perform_prelabel(project_id):
    Project.query.get_or_404(project_id)
    queue.enqueue("jobs.prelabel.prelabel_project", project_id, job_timeout=3600)
    return redirect('/project/' + str(project_id) + '?queued=1')