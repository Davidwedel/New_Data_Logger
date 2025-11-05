#!/usr/bin/env python3
"""
WSGI Entry Point for Apache mod_wsgi
Exposes the Flask application for production deployment
"""
import sys
import os

# Add project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)
sys.path.insert(0, os.path.join(project_dir, "server"))
sys.path.insert(0, os.path.join(project_dir, "server/unitas_manager"))

# Import the Flask app from webapp
from webapp import app as application

# Set production configuration
application.config['DEBUG'] = False
application.secret_key = os.environ.get('SECRET_KEY', 'CHANGE_THIS_IN_PRODUCTION')

# If you want to use environment variables for sensitive config:
# application.config.update(
#     SECRET_KEY=os.environ.get('SECRET_KEY', 'fallback-secret-key'),
# )
