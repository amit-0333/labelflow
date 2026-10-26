from flask import Blueprint, render_template
from flask_login import current_user
from core.models import Project
from auth.decorators import role_required
from tasks.assignment import claim_next_task

tasks_bp = Blueprint("tasks", __name__)


## annotator or admin clicks "Start labeling", the app picks a task for them
@tasks_bp.route('/start_labeling/<int:project_id>')
@role_required("admin", "annotator")
def start_labeling(project_id):
    Project.query.get_or_404(project_id)
    task = claim_next_task(current_user.id, project_id)
    return render_template('task.html', task=task, project_id=project_id)