from flask import Blueprint, render_template
from core.models import Project
from auth.decorators import role_required
from quality.scores import get_annotator_scores
from quality.agreement import get_agreement
from quality.stats import get_project_stats

quality_bp = Blueprint("quality", __name__)


## admin only: quality table for all annotators
@quality_bp.route('/quality')
@role_required("admin")
def quality():
    return render_template('quality.html', rows=get_annotator_scores())


## admin or reviewer: agreement numbers for one project
@quality_bp.route('/agreement/<int:project_id>')
@role_required("admin", "reviewer")
def agreement(project_id):
    project = Project.query.get_or_404(project_id)
    pairs, confused = get_agreement(project_id)
    return render_template('agreement.html', project=project, pairs=pairs, confused=confused)

## admin or reviewer: one page with the main numbers of a project
@quality_bp.route('/dashboard/<int:project_id>')
@role_required("admin", "reviewer")
def dashboard(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template('dashboard.html', project=project, s=get_project_stats(project_id))