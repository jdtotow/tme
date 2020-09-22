FROM ubuntu:16.04 
RUN apt-get update 
RUN apt-get -y upgrade 
RUN apt-get install -y curl 
RUN mkdir /app 
COPY agreement.json /app 
COPY start_qos.sh /app 
COPY stop_qos.sh /app 
RUN chmod +x /app/start_qos.sh 
RUN chmod +x /app/stop_qos.sh 
WORKDIR /app 
ENTRYPOINT ["/app/start_qos.sh"]