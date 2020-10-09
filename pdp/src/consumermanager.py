import pika, time  
from threading import Thread

class Worker(Thread):
    def __init__(self,username,password,host,port,exchange,queue,handler,n_tries):
        self.username = username 
        self.password = password
        self.host = host 
        self.port = port 
        self.exchange = exchange 
        self.queue = queue 
        self.connection = None 
        self.channel = None 
        self.handler = handler 
        self.n_tries = n_tries 
        self.connection_state = False 
        self.normal_stop = False 
        super(Worker,self).__init__()
    def connect(self):
        try:
            credentials = pika.PlainCredentials(self.username, self.password)
            self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host,port=self.port,credentials=credentials))
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=self.queue, durable=True)
            #self.channel.queue_bind(queue=self.queue,exchange=self.exchange)
            self.channel.basic_qos(prefetch_count=1)
            self.channel.basic_consume(queue=self.queue,on_message_callback=self.callback)
            self.connection_state = True 
        except Exception as e:
            print("Error while connection")
            print(e)
            
    def startConsuming(self):
        try:
            self.channel.start_consuming()
        except Exception as e:
            print("Consumer thread failed, restart in 2s...")
            print(e)
            if self.connection:
                self.connection.close()
                time.sleep(2)
                self.connect()
                self.startConsuming()
    def getConnectionState(self):
        return self.connection_state
    def stop(self):
        self.normal_stop = True 
    def callback(self,channel, method, header, body):
        self.handler.setData(body)
        if self.normal_stop:
            if self.connection:
                self.connection.close()
            self.channel.stop_consuming()
        self.channel.basic_ack(method.delivery_tag)
    def run(self):
        index = 0
        while True:
            try:
                self.connect()
                break 
            except Exception as e:
                print(e)
                index +=1
                print("Worker will sleep for 20s")
                time.sleep(20)
        if self.connection_state:
            print("Worker start to consume")
            self.startConsuming()
        print("End Process")


class MultiThreadConsumerManager():
    def __init__(self,n_consumers,username,password,host,port,n_tries,exchange,handler,queue):
        self.n_consumers = n_consumers
        self.username = username
        self.password = password
        self.host = host 
        self.port = port 
        self.n_tries = n_tries 
        self.exchange = exchange
        self.handler = handler 
        self.queue = queue 
        self.list_workers = []
    def start(self):
        for i in range(self.n_consumers):
            worker = Worker(self.username,self.password,self.host,self.port,self.exchange,self.queue,self.handler,self.n_tries)
            self.list_workers.append(worker)
            worker.start()
            
    def stop(self):
        for worker in self.list_workers:
            worker.stop()
    def checkThreads(self):
        for thread in self.list_workers:
            if not thread.getConnectionState():
                thread.stop()
                time.sleep(1)
                thread.start()
            
