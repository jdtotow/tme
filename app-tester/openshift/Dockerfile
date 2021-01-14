FROM python:3.7.0
RUN apt-get install -y curl 
RUN python -m pip install --upgrade pip
RUN pip install requests prometheus_client flask
RUN mkdir /app
RUN useradd tester
RUN chown -R tester /app 
COPY tester2.py /app/app.py 
COPY start_qos-response.sh start_qos-cost.sh stop_qos-response.sh stop_qos-cost.sh /app/
COPY agreement-response.json agreement-cost.json /app/
RUN chmod +x /app/*.sh 
EXPOSE 9909
USER tester 
WORKDIR /app 
ENTRYPOINT ["python3","-u","app.py"]