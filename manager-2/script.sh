#!bin/bash
cd app
python -u manager.py &
python wsgi.py &
python wsgi_qos.py 
