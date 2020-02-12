FROM python:3
ADD consumer.py /
ADD config.py /
ADD rabbitmqtester.py /

RUN pip install pika requests psutil

CMD [ "python","-u", "./consumer.py" ]
