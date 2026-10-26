from flask import Blueprint, render_template, request, redirect
from flask_login import current_user
from core.db import db
from core.models import Project
from auth.decorators import role_required

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