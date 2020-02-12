FROM jdtotow/monitoring:2
MAINTAINER Jean-Didier Totow <totow@unipi.gr>
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
