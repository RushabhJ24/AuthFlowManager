import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the app with the extension
db.init_app(app)

with app.app_context():
    # Import models to ensure tables are created
    import models  # noqa: F401
    import auth  # noqa: F401
    db.create_all()
    
    # Initialize default settings if they don't exist
    from models import User, Settings
    from werkzeug.security import generate_password_hash
    
    # Initialize default settings
    if not Settings.query.filter_by(key='CENTRAL_LAT').first():
        Settings.set_value('CENTRAL_LAT', os.environ.get("CENTRAL_LAT", "20.457316"), 
                          'Central service location latitude')
        Settings.set_value('CENTRAL_LNG', os.environ.get("CENTRAL_LNG", "75.016754"), 
                          'Central service location longitude')
        Settings.set_value('SERVICE_RADIUS_KM', os.environ.get("SERVICE_RADIUS_KM", "5"), 
                          'Service radius in kilometers')
    
    # Create admin user if it doesn't exist
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@tiffinservice.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    
    admin_user = User.query.filter_by(email=admin_email).first()
    if not admin_user:
        central_lat, central_lng = Settings.get_central_coordinates()
        admin_user = User(
            name="Admin",
            email=admin_email,
            phone="1234567890",
            password_hash=generate_password_hash(admin_password),
            address="Admin Address",
            latitude=central_lat,
            longitude=central_lng,
            is_admin=True
        )
        db.session.add(admin_user)
        db.session.commit()
        logging.info(f"Admin user created with email: {admin_email}")
