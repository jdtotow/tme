FROM python:3 
RUN pip install --upgrade pip
RUN pip install numpy dtw requests prometheus_client pika python-dateutil
COPY src/ /app
RUN mkdir /config
RUN touch /config/config.json 
RUN chmod 777 /config/config.json 
COPY script.sh /
RUN chmod +x /app/pdp.py
RUN useradd pdp
USER pdp
CMD ["./script.sh"]
