import os
import sys

# Ensure root directory is in python search path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app

# Export WSGI application for Vercel Python runtime
app = app
