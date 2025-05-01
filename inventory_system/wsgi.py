"""
WSGI config for inventory_system project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""
import sys
import os
from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventory_system.settings')

application = get_wsgi_application()
application = WhiteNoise(application, root='staticfiles')
print("Python Path:", sys.path, file=sys.stderr)
print("Whitenoise Path:", 
      [p for p in sys.path if 'whitenoise' in p.lower()], 
      file=sys.stderr)