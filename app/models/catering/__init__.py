from flask import Blueprint

catering_bp = Blueprint(
    "catering",
    __name__,
    template_folder="../../templates/catering"
)

from . import routes
