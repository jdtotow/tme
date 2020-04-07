import pika, json, time
from threading import Thread

push_connexion = None 
push_channel = None 
n_tries = 10

class RabbitMQ(Thread):
    def __init__(self,exchanger,queue,username,password,host,port):
        self.exchanger = exchanger
        self.connection = None
        self.channel = None
        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.queue = queue 
        self.normal_stop = False
        self.manager = None 
        super(RabbitMQ,self).__init__()
    def setManager(self,manager):
        self.manager = manager 
    def connect(self):
        credentials = pika.PlainCredentials(self.username, self.password)
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host,port=self.port,credentials=credentials))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.queue, durable=True)
        if self.exchanger != "":
            self.channel.exchange_declare(exchange=self.exchange,exchange_type="direct",passive=False,durable=True,auto_delete=False)
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue=self.queue,on_message_callback=self.callback)
        print("Connection to broker established ...")
    def startListenning(self):
        self.channel.start_consuming()
    def run(self):
        n_try = 0
        while n_try < n_tries:
            try:
                self.connect()
                self.startListenning()
                if self.normal_stop:
                    break
            except Exception as e:
                print(e)
                print("Process will sleep for 5s")
                time.sleep(5)
        print("End process")

    def reconnect(self):
        self.stop()
        time.sleep(10)
        self.connect()
    def stop(self):
        self.normal_stop = True
        global push_connexion
        if push_connexion:
            push_connexion.close()
        self.channel.stop_consuming()
        if self.connection:
            self.connection.close()
    def callback(self,channel, method, header, body):
        self.manager.setData(body)
        self.channel.basic_ack(method.delivery_tag)
    def sendToClient(self,routing,message):
        thread = Thread(target=self.push,args=[routing,message])
        thread.start()
    def push(self,routing,message):
        global push_channel, push_connexion
        def establishConnection():
            credentials = pika.PlainCredentials(self.username, self.password)
            push_connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host,credentials=credentials))
            channel = push_connection.channel()
            return channel
        if push_channel == None or push_channel.is_closed:
            push_channel = establishConnection()
        try:
            push_channel.basic_publish(exchange=self.exchanger,routing_key=routing,body=message,properties=pika.BasicProperties(content_type='text/json',delivery_mode=1))
        except Exception as e:
            print(e)