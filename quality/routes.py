from flask import Blueprint, render_template
from auth.decorators import role_required
from quality.scores import get_annotator_scores

quality_bp = Blueprint("quality", __name__)


## admin only: quality table for all annotators
@quality_bp.route('/quality')
@role_required("admin")
def quality():
    return render_template('quality.html', rows=get_annotator_scores())