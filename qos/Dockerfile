FROM jdtotow/monitoring:2
MAINTAINER Jean-Didier Totow <totow@unipi.gr>
RUN pip install numpy panda statsmodels
COPY src/ /app
RUN mkdir /config
RUN touch /config/config.json 
RUN chmod 777 /config/config.json 
COPY script.sh /
RUN chmod +x /app/app.py
RUN useradd qos
USER qos
CMD ["./script.sh"]
