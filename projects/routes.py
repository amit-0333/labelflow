from flask import Blueprint, render_template, request, redirect
from flask_login import current_user
from core.db import db
from core.models import Project, Task
from auth.decorators import role_required
from projects.csv_parser import parse_csv
from core.models import AIPrediction
from jobs.queue import queue

projects_bp = Blueprint("projects", __name__)


## show all projects (any logged in user can see the list)
@projects_bp.route('/projects')
@role_required("admin", "annotator", "reviewer")
def projects():
    all_projects = Project.query.all()
    return render_template('projects.html', projects=all_projects)


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
    description = request.form.get('description')
    guidelines = request.form.get('guidelines')
    labels_text = request.form.get('labels')
    annotators_per_item = request.form.get('annotators_per_item')

    ## "spam, not_spam" becomes ["spam", "not_spam"]
    label_options = []
    for label in labels_text.split(','):
        label = label.strip()
        if label != '':
            label_options.append(label)

    ## need at least 2 labels
    if len(label_options) < 2:
        return render_template('create_project.html', message="Enter at least 2 labels, separated by commas")

    project = Project(
        name=name,
        description=description,
        guidelines=guidelines,
        label_options=label_options,
        annotators_per_item=int(annotators_per_item),
        created_by=current_user.id
    )
    db.session.add(project)
    db.session.commit()

    return redirect('/projects')


@projects_bp.route('/project/<int:project_id>')
@role_required("admin", "annotator", "reviewer")
def project_page(project_id):
    project = Project.query.get_or_404(project_id)
    task_count = Task.query.filter_by(project_id=project_id).count()
    ai_count = (
        AIPrediction.query
        .join(Task, AIPrediction.task_id == Task.id)
        .filter(Task.project_id == project_id)
        .count()
    )
    return render_template('project.html', project=project, task_count=task_count, ai_count=ai_count)


## admin only: read the CSV and save each row as a task
@projects_bp.route('/perform_upload_csv/<int:project_id>', methods=['POST'])
@role_required("admin")
def perform_upload_csv(project_id):
    project = Project.query.get_or_404(project_id)
    file = request.files.get('file')

    ## no file chosen
    if file is None or file.filename == '':
        task_count = Task.query.filter_by(project_id=project_id).count()
        return render_template('project.html', project=project, task_count=task_count, message="Choose a CSV file first")

    tasks, error = parse_csv(file)

    if error:
        task_count = Task.query.filter_by(project_id=project_id).count()
        return render_template('project.html', project=project, task_count=task_count, message=error)

        ## a gold_label must be one of the project labels
    for t in tasks:
        if t["gold_label"] and t["gold_label"] not in project.label_options:
            task_count = Task.query.filter_by(project_id=project_id).count()
            return render_template('project.html', project=project, task_count=task_count, message="gold_label '" + t["gold_label"] + "' is not one of the project labels")

    for t in tasks:
        task = Task(
            project_id=project_id,
            text=t["text"],
            extra_data=t["extra"],
            is_gold=bool(t["gold_label"]),
            gold_label=t["gold_label"]
        )
        db.session.add(task)
    db.session.commit()

    task_count = Task.query.filter_by(project_id=project_id).count()
    return render_template('project.html', project=project, task_count=task_count, message=str(len(tasks)) + " tasks uploaded")

## admin only: send the pre-labeling job to the worker
@projects_bp.route('/perform_prelabel/<int:project_id>')
@role_required("admin")
def perform_prelabel(project_id):
    Project.query.get_or_404(project_id)
    ## the job is given by name, so the website does not import the worker code
    queue.enqueue("jobs.prelabel.prelabel_project", project_id, job_timeout=3600)
    return redirect('/project/' + str(project_id))