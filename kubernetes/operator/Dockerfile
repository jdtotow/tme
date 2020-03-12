FROM python:3.7
RUN pip install kopf kubernetes 
COPY handler.py /handler.py
COPY tme_config.py /tme_config.py 
CMD kopf run --standalone /handler.py --verbose 