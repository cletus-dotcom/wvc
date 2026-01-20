from flask import Blueprint

construction_bp = Blueprint(
    "construction",
    __name__,
    template_folder="../../templates/construction"
)

from . import routes

