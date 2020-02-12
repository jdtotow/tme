import pika, json, time, os 
from threading import Thread 
from configsaver import ConfigSaver

consumer_queue_name = os.environ.get("CONSUMERQUEUENAME","pdp")
rabbitmq_host = os.environ.get("RABBITMQHOSTNAME","localhost")
rabbitmq_port = int(os.environ.get("RABBITMQPORT","5672"))
rabbitmq_username = os.environ.get("RABBITMQUSERNAME","richardm")
rabbitmq_password = os.environ.get("RABBITMQPASSWORD","bigdatastack")
n_tries = int(os.environ.get("NTRIES","10"))
ml_consumer_queue_name = os.environ.get("MLCONSUMERQUEUENAME","ml_executor")
manager_queue_name = os.environ.get("MANAGERQUEUENAME","manager")
#/////////////////////////////////////////////////////////////////////////////////
push_channel = None 
push_connexion = None 

class RabbitMQ():
    def __init__(self, username,password,host,port):
        self.exchanger = None
        self.connection = None
        self.channel = None
        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.manager = None 
        self.normal_stop = False
    
    def connect(self):
        credentials = pika.PlainCredentials(self.username, self.password)
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host,port=self.port,credentials=credentials))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=consumer_queue_name, durable=True)
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue=consumer_queue_name,on_message_callback=self.callback)
        print("Connection to broker established ...")
    def setManager(self,manager):
        self.manager = manager 
        self.manager.setRabbitMQ(self)
    def startListenning(self):
        self.channel.start_consuming()
    def reconnect(self):
        self.stop()
        time.sleep(5)
        self.connect()
    def stop(self):
        self.normal_stop = True
        global push_connexion
        if push_connexion:
            push_connexion.close()
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
            push_channel.basic_publish(exchange="",routing_key=routing,body=message,properties=pika.BasicProperties(content_type='text/json',delivery_mode=1))
        except Exception as e:
            print(e)

class BasketManager():
    def __init__(self):
        self.list_hash_basket = {}
        self.manager = None 
    def setManager(self,manager):
        self.manager = manager 
    def createBasket(self,application_name):
        if not application_name in self.list_hash_basket:
            basket = Basket(self.manager)
            self.list_hash_basket[application_name] = basket 
            print(application_name+" created successfuly")
            return True 
        return False 
    def getBasket(self,application_name):
        if application_name in self.list_hash_basket:
            return self.list_hash_basket[application_name]
        return None 
    def addElement(self,_json):
        try:
            if 'application' in _json['data']['labels']:
                application_name = _json['data']['labels']['application']
                basket = self.getBasket(application_name)
                if basket != None:
                    basket.addElement(_json)
        except Exception as e:
            print(e)
            return False 

class Basket():
    def __init__(self,manager):
        self.hash_baskets = {}
        self.manager = manager 
    def getBasket(self,_time):
        return self.hash_baskets[_time]
    def ifKeyExist(self,_time):
        return _time in self.hash_baskets
    def fieldInBasket(self,field, _time):
        if _time in self.hash_baskets:
            basket = self.hash_baskets[_time]
            if field in basket:
                return True
        return False
    def basketIsCompleted(self,basket,application):
        n_field = self.manager.getNFieldByApplicationName(application)
        if n_field != None:
            if n_field + 1 == len(basket.keys()): # field declared plus time field
                return True 
        return False 
    def evaluation(self,application):
        if len(self.hash_baskets.keys()) == 0:
            return False
        for _time in self.hash_baskets.keys():
            basket = self.hash_baskets[_time]
            if self.basketIsCompleted(basket,application):
                self.publish(basket,application)
                del self.hash_baskets[_time]
    def publish(self,basket,application):
        message = {'application': application,'data': basket}
        #print(message)
        self.manager.sendToClient(ml_consumer_queue_name,json.dumps(message))
    def addElement(self,element):
        name = element['data']['name']
        _time = element['data']['time']
        _time = _time[:-8]
        if self.ifKeyExist(_time):
            basket = self.getBasket(_time)
            if not name in basket:
                basket[name] = element['data']['value']
                self.hash_baskets[_time] = basket
        else:
            basket = {'time': _time}
            basket[name] = element['data']['value']
            self.hash_baskets[_time] = basket
        self.evaluation(element['data']['labels']['application'])

class Application():
    def __init__(self, name, n_field):
        self.name = name 
        self.n_field = n_field 
    def getName(self):
        return self.name 
    def getNField(self):
        return self.n_field

class Manager():
    def __init__(self):
        self.applications = []
        self.rabbitmq = None 
        self.basket_manager = BasketManager()
        self.basket_manager.setManager(self)
        self.config = None 
    def sendToClient(self,queue,content):
        self.rabbitmq.sendToClient(queue,content)
    def setRabbitMQ(self,rabbitmq):
        self.rabbitmq = rabbitmq
        self.config = ConfigSaver(self)
    def setPreviousConfig(self,config):
        for app_name, _json in config.iteritems():
            self.AddApplication(_json['data']['name'],_json['data']['n_field'])
        print("Config reloaded")
    def sendPongRequest(self):
        request = {}
        request['queue'] = consumer_queue_name
        self.rabbitmq.sendToClient(manager_queue_name,json.dumps(request))
    def setData(self,body):
        _json = None 
        try:
            _json = json.loads(body)
        except Exception as e:
            print(e)
            return False 
        if 'request' in _json:
            if _json['request'] == "add_application":
                if self.AddApplication(_json['data']['name'],_json['data']['n_field']):
                    print("application "+ _json['data']['name']+" has been added")
                    response =  {'request': 'add_application','status': 'success','application': _json['data']['name']}
                    self.rabbitmq.sendToClient(_json['queue'],json.dumps(response))
                    self.config.setConfig(_json['data']['name'],_json)
                else:
                    response =  {'request': 'add_application','status': 'error','messsage':'application already exists','application': _json['data']['name']}
                    self.rabbitmq.sendToClient(_json['queue'],json.dumps(response))
            elif _json['request'] == "stream":
                self.basket_manager.addElement(_json)
            elif _json['request'] == "ping":
                self.sendPongRequest()
            elif _json['request'] == "remove_application":
                self.removeApplication(_json)
            else:
                print(_json)
    def unsubscribe(self,application_name):
        request = {'name': application_name,'queue': consumer_queue_name,'request':'remove_subscription'}
        self.rabbitmq.sendToClient(manager_queue_name,json.dumps(request))
        self.config.remove(application_name)
    def removeApplication(self,_json):
        required_field = ['application','deployment']
        for field in required_field:
            if not field in _json:
                print("Field <"+field+"> is missing")
                return False 
        app = self.getApplication(_json['application'])
        if app != None:
            self.unsubscribe(_json['application'])
    def stop(self):
        for app in self.applications:
            self.unsubscribe(app.getName())
    def sendSubscriptionRequest(self,application_name):
        message = {}
        message['request'] = 'subscription'
        data = {}
        data['name'] = application_name
        data['queue'] = consumer_queue_name
        data['heartbeat_interval'] = 0
        metrics = []
        metric = {}
        metric['name'] = "*"
        metric['on_change_only'] = False
        metric['labels'] = {'application':application_name}
        metrics.append(metric)
        data['metrics'] = metrics
        message['data'] = data
        self.rabbitmq.sendToClient(manager_queue_name,json.dumps(message))
        print("Subscription request sent")
    def AddApplication(self,name,n_field):
        app = self.getApplication(name)
        if app == None:
            app = Application(name,n_field)
            self.applications.append(app)
            self.sendSubscriptionRequest(name)
            self.basket_manager.createBasket(name)
            return True 
        return False 
    def getApplication(self,name):
        for app in self.applications:
            if app.getName() == name:
                return app 
        return None 
    def getNFieldByApplicationName(self,name):
        for app in self.applications:
            if app.getName() == name:
                return app.getNField()
        return None 
         
def main():
    manager = Manager()
    rabbitmq = RabbitMQ(rabbitmq_username,rabbitmq_password,rabbitmq_host,rabbitmq_port)
    connected = False
    index = 0
    while not connected:
        if index == n_tries:
            print("Impossible to establish connexion to RabbitMQ")
            break
        try:
            index +=1
            print(str(index)+' , try to connect to brocker ...')
            rabbitmq.connect()
            rabbitmq.setManager(manager)
            connected = True
        except (KeyboardInterrupt, SystemExit):
            connected = True
            manager.stop()
            rabbitmq.stop()
        except Exception as e:
            print(e)
            print("Auto reconnection in 5 secs ...")
            rabbitmq.stop()
            time.sleep(5)
    if connected:
        rabbitmq.startListenning()

if __name__== "__main__":
    main()
