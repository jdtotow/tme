FROM jdtotow/monitoring:2
MAINTAINER Jean-Didier Totow <totow@unipi.gr>
COPY app/ /app
COPY script.sh /
RUN chmod +x /app/app.py
RUN useradd exporter
EXPOSE 55684
USER exporter
CMD ["./script.sh"]
