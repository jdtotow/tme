FROM python:3
RUN apt-get install -y curl 
RUN python -m pip install --upgrade pip
RUN pip install requests
RUN mkdir /app
RUN useradd tester
RUN chown -R tester /app 
COPY recommender_tester.py /app/app.py 
COPY start_qos-response.sh start_qos-cost.sh stop_qos-response.sh stop_qos-cost.sh /app/
COPY agreement-response.json agreement-cost.json /app/
RUN chmod +x /app/*.sh 
USER tester 
WORKDIR /app 
ENTRYPOINT ["python3","-u","app.py"]