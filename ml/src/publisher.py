import pika, time 
from threading import Thread 

class ThreadPublisher(Thread):
    def __init__(self,username,password,host,port,exchange,sleep):
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
            self.connection_state = True 
            print("Publisher connected to the broker")
            self.send()
        except Exception as e:
            print(e)
    def reconnect(self):
        print("Reconnexion in 2s...")
        time.sleep(2)
        self.connect()
    def send(self):
        if self.channel == None or self.channel.is_closed:
            self.reconnect()
        for task in self.tasks:
            try:
                self.channel.basic_publish(exchange=self.exchange,routing_key=task['queue'],body=task['message'],properties=pika.BasicProperties(content_type='text/json',delivery_mode=1))
                print("sent")
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
            if not self.connection_state:
                print("Publisher tries to connect")
                time.sleep(5)
                self.connect()
            if len(self.tasks) > 0:
                self.send()
            else:
                time.sleep(self.sleep)
            if self.normal_stop:
                break