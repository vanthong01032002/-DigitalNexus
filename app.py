import os
import logging
from datetime import timedelta
from flask import Flask, redirect, url_for, flash, session, g, request
from flask_bcrypt import Bcrypt
from flask_session import Session
from flask_wtf.csrf import CSRFProtect
import qrcode
from io import BytesIO
import base64
import random
import string
from utils import CustomJSONEncoder

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "s4W!t7qzX@9nFd8Lp$e2RmVk&cG0aYj")

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Configure session
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)
app.json_encoder = CustomJSONEncoder
Session(app)

# Initialize Bcrypt
bcrypt = Bcrypt(app)

# Import views after app initialization to avoid circular imports
from views import *

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
