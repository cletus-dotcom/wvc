from flask import Blueprint

carenderia_bp = Blueprint(
    "carenderia",
    __name__,
    template_folder="../../templates/carenderia"
)

from . import routes
