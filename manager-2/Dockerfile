FROM jdtotow/monitoring:2
MAINTAINER Jean-Didier Totow <totow@unipi.gr>
RUN pip install pymongo confluent_kafka numpy 
COPY app/ /app
RUN mkdir /config
COPY config/config.json /config 
COPY script.sh /
RUN chmod +x /app/manager.py
RUN chmod +x /app/wsgi.py
RUN useradd manager
RUN chown -R manager /config
RUN chmod 777 /config/config.json
EXPOSE 55671 
USER manager
CMD ["./script.sh"]
