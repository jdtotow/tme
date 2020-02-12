FROM jdtotow/monitoring:2
MAINTAINER Jean-Didier Totow <totow@unipi.gr>
COPY src/ /app
RUN mkdir /config 
COPY script.sh /
RUN chmod +x /app/app.py
RUN useradd prom-auto-conf
USER prom-auto-conf
CMD ["./script.sh"]
