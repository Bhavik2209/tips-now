"""
WSGI config for momentum project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os
import sys

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'momentum.settings')

application = get_wsgi_application()

app = application

# if __name__ == "__main__":
#     execute_from_command_line(sys.argv)