FROM python:3 
RUN pip install --upgrade pip
RUN pip install pika prometheus_client requests python-dateutil
#RUN python -m pip install statsmodels
COPY src/ /app
RUN mkdir /config /dataset 
RUN touch /config/config.json 
RUN chmod 777 /config/config.json 
COPY script.sh /
RUN chmod +x /app/app.py
RUN useradd ml
USER ml
CMD ["./script.sh"]
