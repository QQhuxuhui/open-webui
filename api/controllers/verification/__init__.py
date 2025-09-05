from flask import Blueprint
from .verification import verification_bp

bp = Blueprint('verification', __name__)
bp.register_blueprint(verification_bp)