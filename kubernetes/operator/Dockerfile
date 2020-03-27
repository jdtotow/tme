FROM python:3.7
RUN pip install kopf kubernetes 
COPY handler_v2.py /handler.py
RUN mkdir /config 
COPY planner.json /config/planner.json 
COPY tme_config.py /tme_config.py 
CMD kopf run --standalone /handler.py --verbose 