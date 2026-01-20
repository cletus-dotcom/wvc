from app import create_app
from app.extensions import db
from app.models.user import User

app = create_app()

with app.app_context():
    # Check if admin already exists
    if User.query.filter_by(username="admin").first():
        print("Admin user already exists.")
    else:
        # Create default admin user
        admin = User(username="admin", role="Admin")
        admin.set_password("123")  # Change password if needed
        db.session.add(admin)
        db.session.commit()
        print("Default admin user created: username='admin', password='admin123'")
