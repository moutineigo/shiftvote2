#!/home/eigo55/venv/bin/python

import os
import cgitb
cgitb.enable()

os.environ.setdefault('SHIFTVOTE_DATA_DIR', '/home/eigo55/shiftvote2-data')

from wsgiref.handlers import CGIHandler
from app import app

CGIHandler().run(app)
