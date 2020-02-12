import pika, time 
from threading import Thread 

class ThreadPublisher(Thread):
    def __init__(self,username,password,host,port,exchange,sleep,exchange_fanout):
        self.tasks = []
        self.connection = None 
        self.channel = None 
        self.username = username 
        self.password = password
        self.host = host 
        self.port = port 
        self.sleep = sleep 
        self.normal_stop = False 
        self.exchange = exchange 
        self.connection_state = False
        self.exchange_fanout_created = False 
        self.exchange_fanout = exchange_fanout 
        super(ThreadPublisher, self).__init__()
    def stop(self):
        self.normal_stop = True 
        self.connection_state = False 
    def sendToClient(self,queue,message):
        _json = {'queue': queue,'message': message}
        self.addTask(_json)
    def getConnectionState(self):
        return self.connection_state
    def connect(self):
        if self.connection:
            try:
                self.connection.close()
            except:
                pass 
        try:
            credentials = pika.PlainCredentials(self.username, self.password)
            self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host,port=self.port,credentials=credentials))
            self.channel = self.connection.channel()
            if self.exchange_fanout and not self.exchange_fanout_created:
                self.channel.exchange_declare(exchange=self.exchange,exchange_type="fanout",passive=False,durable=True,auto_delete=False)
                self.exchange_fanout_created = True 
                print("Exchange fanout created successfuly")
            self.connection_state = True 
            print("Publisher connected to the broker")
        except Exception as e:
            self.reconnect()
            print(e)
            self.send()
    def reconnect(self):
        print("Reconnexion in 5s...")
        time.sleep(2)
        self.connect()
    def send(self):
        if self.channel == None or self.channel.is_closed:
            self.connection_state = False
            self.reconnect()
        for task in self.tasks:
            try:
                if task['queue'] !="":
                    self.channel.basic_publish(exchange="",routing_key=task['queue'],body=task['message'],properties=pika.BasicProperties(content_type='text/json',delivery_mode=1))
                else:
                    self.channel.basic_publish(exchange=self.exchange,routing_key=task['queue'],body=task['message'],properties=pika.BasicProperties(content_type='text/json',delivery_mode=1))
            except Exception as e:
                print(e)
                self.reconnect()
        del self.tasks[:]
    def addTask(self,task):
        self.tasks.append(task)
    def addTasks(self,tasks):
        self.tasks.extend(tasks) 
    def run(self):
        while True:
            if len(self.tasks):
                self.send()
            time.sleep(self.sleep)
            if self.normal_stop:
                break