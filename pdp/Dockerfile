FROM jdtotow/monitoring:2
MAINTAINER Jean-Didier Totow <totow@unipi.gr>
RUN pip install numpy dtw
COPY src/ /app
RUN mkdir /config
RUN touch /config/config.json 
RUN chmod 777 /config/config.json 
COPY script.sh /
RUN chmod +x /app/pdp.py
RUN useradd pdp
USER pdp
CMD ["./script.sh"]
