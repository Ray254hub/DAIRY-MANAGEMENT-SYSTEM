import sys
import os

# 1. Add the application directory to the system path
sys.path.insert(0, os.path.dirname(__file__))

# 2. Import your Flask app instance
# Note: 'from app' assumes your main Python file is named app.py.
# 'import app' gets the 'app = Flask(__name__)' variable.
from app import app as application