#manager
import pika, json, requests, time, base64, os, psutil, hashlib, uuid
from threading import Thread
from dateutil.parser import parse
from mon import Monitoring
#from pymongo import MongoClient
from publisher import ThreadPublisher
from consumermanager import MultiThreadConsumerManager
import config
import numpy as np 
#################################################
application_name = config.manager['application']
#################################################
push_url = config.exporter['url']
push_channel = None
push_connexion = None
monitoring = Monitoring(application_name,config.engine)

dbname = os.environ.get("DBNAME","TPME")
db_username = os.environ.get("MONGODB_USERNAME","uprc")
db_password = os.environ.get("MONGODB_PASSWORD","bigdatastack")
mongdb_host = os.environ.get("MONGODB_HOST","mongodb:27017")
gossip_sync_interval = float(os.environ.get("GOSSIPSYNCINTERVAL","60"))
n_threads_consumer = int(os.environ.get("NTHREADSCONSUMER","3"))
manager_all_metrics_queue = os.environ.get("MANAGERALLMETRICSQUEUE","allmetrics")
moving_window_forward = int(os.environ.get("MOVINGWINDOWFARWORD","1"))
url_exporter_qos = os.environ.get("URLEXPORTERQOS","http://localhost:55683")
prom_auto_conf_consumer = os.environ.get("MLCONSUMERQUEUENAME","prom_auto_conf")
enable_prom_auto_conf = os.environ.get("ENABLEPROMAUTOCONF","enabled")
#exchange_broadcast_ingestor = os.environ.get("SYNCEXCHANGENAME","prometheusbeat_sync")


def responder(request,status,body):
    response = {}
    response['request'] = request
    response['status'] = status
    response['data'] = body
    return json.dumps(response)

class RabbitMQ():
    def __init__(self, manager,request,username,password,host,port):
        self.exchanger = None
        self.connection = None
        self.channel = None
        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.parameters = None
        self.manager = manager
        self.request = request
        self.normal_stop = False
        self.request.setManager(self.manager)
        self.request.setQueueManager(self)
    def connect(self):
        credentials = pika.PlainCredentials(self.username, self.password)
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host,port=self.port,credentials=credentials))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue='manager', durable=True)
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue='manager',on_message_callback=self.callback)
        print("Connection to broker established ...")
    def startListenning(self):
        self.channel.start_consuming()
    def reconnect(self):
        self.stop()
        time.sleep(10)
        self.connect()
    def stop(self):
        self.normal_stop = True
        global push_connexion
        if push_connexion:
            push_connexion.close()
        if self.connection:
            self.connection.close()
        self.request.stop()
    def callback(self,channel, method, header, body):
        self.request.setData(body)
        channel.basic_ack(method.delivery_tag)
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

class Consumer():
    def __init__(self,name,queue):
        self.name = name
        self.heartbeat_interval = None
        self.queue = queue
        self.exchange = None
        self.metrics = [] #metrics is a list of metrics
        self.time = time.time()
        self.number_error_message = 0
    def addMetric(self,metric):
        if not metric in self.metrics:
            self.metrics.append(metric)
    def setMetrics(self,metrics):
        self.metrics = metrics
    def setExchange(self,exchange):
        self.exchange = exchange
        print("exchange set <<"+ self.exchange+">>")
    def getExchange(self):
        return self.exchange
    def getMetrics(self):
        return self.metrics
    def getName(self):
        return self.name
    def setHeartbeat(self,_time):
        self.time = _time
    def heartbeatInterval(self):
        return self.heartbeat_interval
    def setHeartbeatInterval(self,interval):
        self.heartbeat_interval = interval
    def getHeartbeat(self):
        return self.time
    def getQueue(self):
        return self.queue
    def setQueue(self,queue):
        self.queue = queue
    def getNumberErrorMessage(self):
        return self.number_error_message
    def incrementErrorMessage(self):
        self.number_error_message +=1
    def resetErrorMessage(self):
        self.number_error_message = 0
    def toJSON(self):
        return {'name': self.name, 'heartbeat_interval': self.heartbeat_interval,'queue': self.queue, 'metrics': self.metrics}

class ConsumerManager():
    def __init__(self):
        self.consumers = []
    def createConsumer(self,name,queue):
        consumer = self.getConsumer(name)
        if consumer != None:
            return None
        else:
            consumer = Consumer(name,queue)
            self.addConsumer(consumer)
            return consumer
    def addConsumer(self,consumer):
        self.consumers.append(consumer)
    def removeConsumer(self,name):
        consumer = self.getConsumer(name)
        if consumer != None:
             self.consumers.remove(consumer)
    def isConsumer(self,name):
        for consumer in self.consumers:
            if name == consumer.getName():
                return True
        return False
    def getConsumer(self,name):
        for consumer in self.consumers:
            if consumer.getName()==name:
                return consumer
        return None
    def getConsumers(self):
        return self.consumers
    def addMetric(self,name,metric):
        consumer = self.getConsumer(name)
        if consumer != None:
            consumer.addMetric(metric)
    def setMetrics(self,name,metrics):
        consumer = self.getConsumer(name)
        if consumer != None:
            consumer.setMetrics(metrics)
            return True
        return None
    def getMetrics(self,name):
        consumer = self.getConsumer(name)
        if consumer != None:
            return (consumer.getQueue(),consumer.getMetrics())
        else:
            return None

class RequestHandler():
    def __init__(self):
        self.body = None
        self.manager = None
        self.queueing_manager = None
        self.publisher = None
        self.config = ConfigSaver()
        self.previous_config = None
        self.total_request = 0
        self.start_time = time.time()
        self.discovering_service = None
        self.qos_subscription_manager = None
        self.multi_consumer = None
        self.waiting_list = []
        self.applications_discovered = []
    def discoverNewApplication(self,data_metric):
        try:
            application = data_metric['labels']['application']
            if not application in self.applications_discovered:
                self.applications_discovered.append(application)
                print("New application discovered <<"+ application+">>")
        except:
            pass
    def setData(self,body):
        self.body = body
        if self.manager == None:
            print("Manager not ready, Data request saved")
            self.waiting_list.append(body)
        else:
            self.handle()
        if self.manager !=None and len(self.waiting_list) > 0:
            for b in self.waiting_list:
                self.body = b
                self.handle()
            print("Data request handled successfuly")
    def setManager(self,manager):
        self.manager = manager
        self.config.setManager(self.manager)
        self.multi_consumer = MultiThreadConsumerManager(n_threads_consumer,config.rabbitmq['username'],config.rabbitmq['password'],config.rabbitmq['host'],int(config.rabbitmq['port']),20,"",self.setData,"manager")
        self.multi_consumer.start()
        thread = Thread(target=self.connectionRoutineCheck,args=())
        thread.start()
    def connectionRoutineCheck(self):
        while True:
            if not self.multi_consumer.threadsStatus():
                self.multi_consumer.stop()
                print("Restarting threads")
                time.sleep(5)
                self.multi_consumer.start()
            time.sleep(5)
    def setQueueManager(self,rabbit):
        self.queueing_manager = rabbit
        self.qos_subscription_manager = QoSSubscriptionManager(self.queueing_manager)
        self.publisher = Publisher(self.manager,self.queueing_manager, self.qos_subscription_manager)
        self.publisher.setConfig(self.config)
        self.config.setPublisher(self.publisher)
        self.config.setRequestHandler(self)
        #self.discovering_service = PeerDiscovering(self.queueing_manager,self.config)
        #thread = Thread(target=self.discovering_service.start)
        #thread.start()
    def setPreviousConfig(self,previous_config):
        self.previous_config = previous_config
        for name, consumer_json in self.previous_config.iteritems():
            if 'queue' in consumer_json:
                queue = consumer_json['queue']
                res = responder('ping','success', 'Ping request')
                self.queueing_manager.sendToClient(queue,res)
        if 'qos' in self.previous_config:
            data = self.previous_config['qos']
            res = responder('ping','success', 'Ping request')
            self.queueing_manager.sendToClient(data['queue'],res)
    def getQoSElementFromPreviewConfig(self,queue):
        if 'qos' in self.previous_config:
            data = self.previous_config['qos']
            if queue == data['queue']:
                return data
        return None
    def deleteConfigEntry(self,name):
        if name in self.previous_config:
            del self.previous_config[name]
    def getConsumerElementFromPreviousConfig(self,queue):
        for name, consumer_json in self.previous_config.iteritems():
            if queue == consumer_json['queue']:
                return name,consumer_json
        return None
    def stop(self):
        self.config.stop()
        self.publisher.stop()
        self.discovering_service.stop()
        self.multi_consumer.stop()
    def sendAddSubsToIngestor(self,metric_name,application_name,_type,queue):
        _json = {'request': 'add_subs','data':{'metric': metric_name,'application':application_name,'type':_type,'queue':queue}}
        self.queueing_manager.addTask({'queue': '','exchange': exchange_broadcast_ingestor,'message': _json})
    def sendRemoveSubsToIngestor(self,metric_name,application_name):
        _json = {'request': 'remove_subs','data':{'metric': metric_name,'application':application_name }}
        self.queueing_manager.addTask({'queue': '','exchange': exchange_broadcast_ingestor,'message': _json})
    def handle(self):
        self.total_request +=1
        data = None
        if type(self.body) == type({}):
            data = self.body
        else:
            try:
                data = json.loads(self.body)
            except Exception as e:
                print("Cannot decode json content")
                print("type",type(self.body))
                print("content",self.body)
                return None
        ###Send report#####
        interval = time.time() - self.start_time
        if interval >= 5:
            request_rate = self.total_request/interval
            process = psutil.Process(os.getpid())
            memory_usage = process.memory_info().rss
            processor_usage = psutil.cpu_percent()
            monitoring.setMetric("request_rate",request_rate)
            monitoring.setMetric("memory",memory_usage)
            monitoring.setMetric("cpu_usage",processor_usage)
            headers = {'X-Requested-With': 'Python requests', 'Content-type': 'text/json'}
            metrics = monitoring.getMetrics()
            component, engine = monitoring.getIdentity()
            labels = {'engine':engine,'application':component}
            _data = json.dumps({'metrics':metrics,'labels':labels})
            try:
                #sending monitoring (manager) metrics to the input rest api
                requests.post(push_url,_data,headers=headers)
            except:
                monitoring.increment('exception')
            self.total_request = 0
            self.start_time = time.time()
        ################################################################
        if not 'request' in data:
            if 'name' in data:
                self.discoverNewApplication(data)
                if self.qos_subscription_manager != None:
                    self.qos_subscription_manager.addToCollector(data)
                subs = self.publisher.matchSubs(data)
                if subs != []:
                    self.publisher.push(subs,data)
            else:
                pass
            return True
        if data['request'] == 'subscription':
            fields = ['name','queue','metrics','heartbeat_interval']
            for field in fields:
                if not field in data['data']:
                    print("field "+ field +" is missing")
                    return None
            name = data['data']['name']
            queue = data['data']['queue']
            metrics = data['data']['metrics']
            interval = data['data']['heartbeat_interval']
            if name !=None and queue != None and metrics !=None:
                consumer = self.manager.createConsumer(name,queue)
                if consumer == None:
                    res = responder('subscription','error', 'This name is already taken')
                    self.queueing_manager.sendToClient(queue,res)
                    #monitoring.increment('error')
                    return False
                if type(metrics) == type([]):
                    consumer.setMetrics(metrics)
                    if 'exchange' in data['data']:
                        consumer.setExchange(data['data']['exchange'])
                    if interval !=None and type(interval) == type(0):
                        consumer.setHeartbeatInterval(interval)
                    else:
                        consumer.setHeartbeatInterval(config.default_heartbeat)
                    res = responder('subscription','success','OK')
                    if consumer.getExchange() == None:
                        self.queueing_manager.sendToClient(queue,res)
                    else:
                        self.queueing_manager.addTask({'queue': queue,'exchange': consumer.getExchange(),'message': res})
                    self.publisher.addSubscription(consumer)
                    #_list_data_to_save = []
                    for metric in metrics:
                        if metric["name"] == "*":
                            self.sendAddSubsToIngestor("",metric["labels"]["application"],"all",queue)
                        elif not "application" in metric["labels"]:
                            self.sendAddSubsToIngestor(metric["name"],"","metric",queue)
                        else:
                            self.sendAddSubsToIngestor(metric["name"],metric["labels"]["application"],"metric-app",queue)

                        #_job_name = "all"
                        #if 'labels' in metric:
                        #    if 'application' in metric['labels']:
                        #        _job_name = metric['labels']['application']
                        #_list_data_to_save.append({'index':hashlib.md5(metric['name']+_job_name).hexdigest(),'type':'stream','last': int(time.time()),'name': name,'n_access':0,'from':int(time.time()),'job': _job_name})
                    #saveMetrics(_list_data_to_save)
                    #monitoring.increment('request_success')
                    self.config.setConfig(consumer.toJSON())
                else:
                    res = responder('subscription','error', 'metrics are not in the right format')
                    self.queueing_manager.sendToClient(queue,res)
                    #monitoring.increment('error')
            else:
                if queue != None:
                    res = responder('subscription','error','Bad request')
                    self.queueing_manager.sendToClient(queue,res)
                    monitoring.increment('error')
        elif data['request'] == "remove_subscription":
            required_fields = ['name','queue']
            for field in required_fields:
                if not field in data:
                    return False
            self.manager.removeConsumer(data['name'])
            self.publisher.removeSubscriptionbyName(data['name'])
            res = responder('remove_subscription','success','Consumer removed successfuly')
            self.queueing_manager.sendToClient(data['queue'],res)
            self.config.remove(data['name'])
            return True
        elif data['request'] == "set_metrics":
            name = data['data']['name']
            metrics = data['data']['metrics']
            queue = data['data']['queue']
            consumer = self.manager.getConsumer(name)
            if consumer != None:
                if consumer.getQueue() != queue:
                    res = responder('set_metrics','error','Wrong request, queue should not be null')
                    self.queueing_manager.sendToClient(consumer.getQueue(),res)
                    monitoring.increment('error')
                    return False
                if type(metrics) != type([]):
                    res = responder('set_metrics','error','Wrong request, metrics should an array')
                    self.queueing_manager.sendToClient(consumer.getQueue(),res)
                    monitoring.increment('error')
                    return False

                consumer.setMetrics(metrics)
                self.publisher.addSubscription(consumer)
                res = responder('set_metrics','success','Subscription list reset')
                self.queueing_manager.sendToClient(consumer.getQueue(),res)
                monitoring.increment('request_success')
                self.config.setConfig(consumer.toJSON())
        elif data['request'] == 'add_metric':
            name = data['data']['name']
            metric = data['data']['metric']
            queue = data['data']['queue']
            consumer = self.manager.getConsumer(name)
            if consumer != None:
                if consumer.getQueue() == queue:
                    consumer.addMetric(metric)
                    res = responder('add_metric','success','metric added to your subscription')
                    self.queueing_manager.sendToClient(queue,res)
                    self.publisher.addSubscription(consumer)
                    monitoring.increment('request_success')
                    self.config.setConfig(consumer.toJSON())
                else:
                    res = responder('add_metric','error','Bad request')
                    self.queueing_manager.sendToClient(consumer.getQueue(),res)
                    monitoring.increment('error')
        elif data['request'] == 'my_subscription':
            name = data['data']['name']
            queue = data['data']['queue']
            declared_queue,metrics = self.manager.getMetrics(name)
            if declared_queue != None:
                if declared_queue == queue:
                    data = responder('my_subscription','success',metrics)
                    self.queueing_manager.sendToClient(queue,data)
                    monitoring.increment('error')
                else:
                    monitoring.increment('error')
        elif data['request'] == 'qos_start':
            if self.qos_subscription_manager.addSubscription(data['queue'],data['metrics']):
                if 'target' in data:
                    self.qos_subscription_manager.addTargetElement()
                    monitor_request = {'request':'add_component_monitor','application_name': data['target']['application'],'component_name': data['target']['component'],'relicas':'first','hostname':data['target']['hostname'],'port':data['target']['port']}
                    self.queueing_manager.sendToClient(prom_auto_conf_consumer,json.dumps(monitor_request))
                self.queueing_manager.sendToClient(data['queue'],json.dumps({'request':'qos','message':'QoS subscription received'}))
                self.config.addQoS(data)
        elif data['request'] == 'qos_stop':
            print("QoS Stop message received")
            self.qos_subscription_manager.removeSubscription(data['metrics'][0]['name'],data['metrics'][0]['application'])
            self.config.removeQoS()
        elif data['request'] == 'qos_pause':
            print("QoS pause message received")
            self.qos_subscription_manager.pauseQos(data['metrics'][0]['name'],data['metrics'][0]['application'])
        elif data['request'] == 'qos_resume':
            print("QoS Resume message received")
            self.qos_subscription_manager.resumeQoS(data['metrics'][0]['name'],data['metrics'][0]['application'])
        elif data['request'] == 'pong':
            queue = data['data']['queue']
            if self.getConsumerElementFromPreviousConfig(queue) != None:
                name, consumer_json = self.getConsumerElementFromPreviousConfig(queue)
                consumer = self.manager.createConsumer(name,queue)
                consumer.setMetrics(consumer_json['metrics'])
                consumer.setHeartbeatInterval(consumer_json['heartbeat_interval'])
                consumer.setQueue(queue)
                self.publisher.addSubscription(consumer)
                self.deleteConfigEntry(name)
        elif data['request'] == 'pong_qos':
            if 'queue' in data:
                data = self.getQoSElementFromPreviewConfig(data['queue'])
                if data != None:
                    self.qos_subscription_manager.addSubscription(data['queue'],data['metrics'])
        elif data['request'] == 'heartbeat':
            name = data['data']['name']
            queue = data['data']['queue']
            if self.manager.getConsumer(name) == None:
                return False
            declared_queue = self.manager.getConsumer(name).getQueue()
            if declared_queue !=None:
                if declared_queue == queue:
                    consumer = self.manager.getConsumer(name)
                    consumer.setHeartbeat(time.time()) #update the heartbeat
                    consumer.resetErrorMessage()
                else:
                    monitoring.increment('error')
            else:
                if self.getConsumerElementFromPreviousConfig(queue) != None:
                    name, consumer_json = self.getConsumerElementFromPreviousConfig(queue)
                    consumer = self.manager.createConsumer(name,queue)
                    consumer.setMetrics(consumer_json['metrics'])
                    consumer.setHeartbeatInterval(consumer_json['heartbeat_interval'])
                    consumer.setQueue(queue)
                    self.publisher.addSubscription(consumer)
                    self.deleteConfigEntry(name)
        elif data['request'] == 'discovering':
            self.discovering_service.handleMessage(data)
        elif data['request'] == 'get_available_applications':
            if 'queue' in data:
                self.queueing_manager.sendToClient(data['queue'],json.dumps({'request': 'available_applications','data':{'time': time.time(),'applications': self.applications_discovered}}))
        else:
            monitoring.increment('error')

class PeerDiscovering():
    def __init__(self,queueing_manager,config):
        self.id = str(uuid.uuid4())
        self.queueing_manager = queueing_manager
        self.config = config
        self.normal_stop = False
    def handleMessage(self,message):
        if message['id'] != self.id:
            self.config.mergeConfig(message['config'])
    def stop(self):
        self.normal_stop = True
    def start(self):
        if not self.queueing_manager.getConnectionState():
            print("Discovering service will sleep for 10s")
            time.sleep(10)
            self.start()
        print("Discovery service started successfully")
        while not self.normal_stop:
            message = {'time': time.time(),'id': self.id,'request': 'discovering','config':self.config.getConfig()}
            self.queueing_manager.sendToClient('manager',json.dumps(message))
            time.sleep(gossip_sync_interval)

class QoSSubscription():
    def __init__(self,queue, metrics):
        self.queue = queue
        self.metric_name = str(metrics['name'])
        self.interval = metrics['interval']
        self.percentage = metrics['percentage']
        self.application = metrics['application']
        self.deployment = None
        self.start_time = None
        self.evaluation_interval = 5
        self.last_evaluation = time.time()
        self.stop_time = None
        self.number_samples = None
        self.list_values = []
        self.is_paused = False
        self.send_samples = False
        self.moving_window_forward = None 
        if 'moving_window_forward' in metrics:
            self.moving_window_forward = metrics['moving_window_forward']
        else:
            self.moving_window_forward = moving_window_forward
        self.last_evaluation = time.time()
        if 'deployment' in metrics:
            self.deployment = metrics['deployment']
        else:
            self.deployment = metrics['application']
    def setListValues(self,_list):
        self.list_values = _list 
    def getListValues(self):
        return self.list_values
    def getMetricName(self):
        return self.metric_name
    def getMovingWindow(self):
        return self.moving_window_forward
    def pause(self):
        self.is_paused = True
    def resume(self):
        self.is_paused = False
    def isPaused(self):
        return self.is_paused
    def getInterval(self):
        return self.interval
    def getPercentage(self):
        return self.percentage
    def getApplicationName(self):
        return self.application
    def getQueue(self):
        return self.queue
    def setQueue(self,queue):
        self.queue = queue
    def getDeployment(self):
        return self.deployment
    def setStartTime(self,_start):
        self.start_time = _start
    def setStopTime(self,_stop):
        self.stop_time = _stop
    def getStartTime(self):
        return self.start_time
    def getEvaluationInterval(self):
        return self.evaluation_interval
    def updateLastEvaluation(self):
        self.last_evaluation = time.time()
    def getLastEvaluation(self):
        return self.last_evaluation
    def getStopTime(self):
        return self.stop_time
    def setNumberSample(self,_sample):
        self.number_samples = _sample
    def getNumberSample(self):
        return self.number_samples
    def getKey(self):
        return hashlib.md5(self.application+self.metric_name).hexdigest()
    def setEvaluationTime(self,_eval):
        self.last_evaluation = _eval
    def detailMode(self):
        return self.send_samples
    def setDetailMode(self):
        self.send_samples = True
    def __str__(self):
        return "name: "+ self.metric_name+" , application: "+ self.application+" , deployment: "+ self.deployment+" , queue: "+ self.queue+" key :"+ self.getKey()
    def __print__(self):
        print(self.__str__())

class QoSSubscriptionManager():
    def __init__(self, queueing_manager):
        self.queueing_manager = queueing_manager
        self.subscriptions = {}
        self.collector = {}
        self.application_monitored = {}
    def subscriptionExist(self,name, application_name):
        for key in self.subscriptions.keys():
            if self.subscriptions[key].getKey() == self.createKey(application_name,name):
                return True
        return False
    def getSubsctiptionIndex(self,name,application_name):
        for i in range(len(self.subscriptions.keys())):
            subs = self.subscriptions[self.subscriptions.keys()[i]]
            if subs.getKey() == self.createKey(application_name,name):
                return i
        return None
    def removeSubscription(self,name,application_name):
        if name == None:
            return False
        index = self.getSubsctiptionIndex(name, application_name)
        print("QoS Evaluator consumer with the index : "+ str(index)+" will be removed")
        if index != None:
            key = self.subscriptions.keys()[index]
            del self.subscriptions[key]
    def computeQuantile(self, _list, percentage):
        """
        _size = len(_list)
        if _size == 0:
            return None
        _list.sort()
        position = int((percentage/100.0)*(_size+1))
        if position == _size:
            position -=1
        return _list[position]
        """
        return np.percentile(np.array(_list),percentage,interpolation='lower')
    def createKey(self,application,name):
        return hashlib.md5(application+name).hexdigest()
    def isCollectionReadyByTimeWindow(self,_list):
        subs = _list[0][1]
        if time.time() - subs.getInterval() >= subs.getLastEvaluation():
            _list_value = []
            for tuple in _list:
                _list_value.append(tuple[0]['value'])
            percentage = subs.getPercentage()
            subs.setStartTime(_list[0][0]['time'])
            subs.setStopTime(_list[-1][0]['time'])
            subs.setNumberSample(len(_list_value))
            subs.setEvaluationTime(time.time())
            subs.setListValues(_list_value)
            quantile = self.computeQuantile(_list_value,percentage)
            return (quantile, subs)
        else:
            return False
    def prepareCollection(self,_list):
        if len(_list) == 0:
            return False
        _list_value = []
        subs = _list[0][1]
        for _tuple in _list:
             _list_value.append(_tuple[0]['value'])
        percentage = subs.getPercentage()
        subs.setStartTime(_list[0][0]['time'])
        subs.setStopTime(_list[-1][0]['time'])
        subs.setNumberSample(len(_list_value))
        quantile = self.computeQuantile(_list_value,percentage)
        return [quantile, subs,_list_value]
    def isCollectionReady(self, _list):
        #subs = self.getSubscription(name)
        subs = _list[0][1]
        interval = subs.getInterval()
        if _list[-1][0]['time'] - _list[0][0]['time'] >= interval:
            _list_value = []
            for _tuple in _list:
                _list_value.append(_tuple[0]['value'])
            percentage = subs.getPercentage()
            subs.setStartTime(_list[0][0]['time'])
            subs.setStopTime(_list[-1][0]['time'])
            subs.setNumberSample(len(_list_value))
            quantile = self.computeQuantile(_list_value,percentage)
            return [quantile, subs,_list_value]
        else:
            return False
    def evaluateCollection(self):
        for key in self.collector.keys():
            list_tuple = self.collector[key]
            if len(list_tuple) == 0:
                continue
            subs = list_tuple[0][1]
            if subs.isPaused():
                continue
            response = self.isCollectionReady(list_tuple)
            if response != False:
                message = None
                if subs.detailMode():
                    message = {'request':'qos','list': response[1].getListValues(),'data_points': response[2],'metric':response[1].getMetricName(),'quantile': response[0],'percentage': response[1].getPercentage(),'application': response[1].getApplicationName(),'deployment':response[1].getDeployment(),'start': response[1].getStartTime(),'stop':response[1].getStopTime(),'samples': response[1].getNumberSample()}
                else:
                    message = {'request':'qos','metric':response[1].getMetricName(),'quantile': response[0],'percentage': response[1].getPercentage(),'application': response[1].getApplicationName(),'deployment':response[1].getDeployment(),'start': response[1].getStartTime(),'stop':response[1].getStopTime(),'samples': response[1].getNumberSample()}
                #////////////////////////////////////////////////////////////////////////////////////
                headers = {'X-Requested-With': 'Python requests', 'Content-type': 'text/json'}
                metrics = {response[1].getMetricName()+"_quantile": float(response[0])}
                labels = {'replicas': response[1].getDeployment(),'application': response[1].getApplicationName()}
                data_export_quantile = json.dumps({'metrics':metrics,'labels':labels})
                try:
                    #sending monitoring (manager) metrics to the input rest api
                    requests.post(url_exporter_qos,data_export_quantile,headers=headers)
                except Exception as e:
                    print(e)
                #////////////////////////////////////////////////////////////////////////////////////
                self.queueing_manager.sendToClient(response[1].getQueue(),json.dumps(message))
                index = 0
                while index < subs.getMovingWindow():
                    if len(self.collector[key]) > 0:
                        del self.collector[key][0]
                        index +=1
                    else:
                        break 
    def removePromConfig(self,app_info):
        required_fields = ['application_name','component_name','replicas']
        for field in required_fields:
            if not field in app_info:
                print("Field <<"+field+" >> is missing")
                return False 
        message = {}
        message['request'] = "remove_component_monitor"
        message['application_name'] = app_info['application_name']
        message['component_name'] = app_info['component_name']
        message['replicas'] = app_info['replicas']
        key = app_info['application_name']+app_info['component_name']+app_info['replicas']
        if key in self.application_monitored:
            del self.application_monitored[key] 
        self.queueing_manager.sendToClient(prom_auto_conf_consumer,json.dumps(message))
    def preparePromConfig(self,app_info):
        required_fields = ['application_name','component_name','replicas','hostname','port']
        for field in required_fields:
            if not field in app_info:
                print("Field << "+field+" >> is missing")
                return False 
        message = {}
        message['request'] = "add_component_monitor"
        message['application_name'] = app_info['application_name']
        message['component_name'] = app_info['component_name']
        message['replicas'] = app_info['replicas']
        message['hostname'] = app_info['hostname']
        message['port'] = app_info['port']
        self.application_monitored[app_info['application_name']+app_info['component_name']+app_info['replicas']] = True 
        self.queueing_manager.sendToClient(prom_auto_conf_consumer,json.dumps(message))
    def addSubscription(self, queue, metrics):
        required_fields = ['name','application','percentage','interval']
        if len(metrics) == 0:
            return False
        for metric in metrics:
            for field in required_fields:
                if not field in metric:
                    print(field +" is missing")
                    return False
            subs = QoSSubscription(queue,metric)
            if 'detail_mode' in metric:
                if metric['detail_mode']:
                    subs.setDetailMode()
                    print("Detail mode activated")
            self.subscriptions[subs.getKey()] = subs
            print("QoS Subscrition for "+ metric['name']+" of the app "+metric['application']+", created at "+ str(time.time())+", key : "+ subs.getKey()+", interval : "+ str(metric['interval'])) 
            #senf to the ingestor
            _json = {'request': 'add_subs','data':{'metric': metric['name'],'application':metric['application'],'type':'metric-app','queue':queue }}
            print(_json)
            #self.queueing_manager.addTask({'queue': 'ingestor','exchange': exchange_broadcast_ingestor,'message': _json})
            self.queueing_manager.addTask({'queue': queue_ingestor,'exchange': exchange_ingestor,'message': json.dumps(_json)})
            
        return True

    def getSubscription(self,name,application_name):
        key = self.createKey(application_name,name)
        if key in self.subscriptions:
            return self.subscriptions[key]
        return None
    def pauseQos(self,application,name):
        subs = self.getSubscription(name,application)
        if subs != None:
            key = subs.getKey()
            subs.pause()
            if key in self.collector:
                del self.collector[key]
            print("Evaluation paused for the metric : "+ name +", of the application : "+ application)
            return True
        return False
    def resumeQoS(self,application,name):
        subs = self.getSubscription(name,application)
        if subs != None:
            subs.resume()
            print("Evaluation resumed for the metric : "+ name +", of the application : "+ application)
            return True
        return False
    def addToCollector(self, data_metric):
        #subs = self.getSubscription(data_metric['name'],data_metric['labels']['application'])
        if not 'application' in data_metric['labels']:
            return False
        subs = self.getSubscription(data_metric['name'],data_metric['labels']['application'])
        if subs != None:
            if subs.isPaused():
                return False
            key = subs.getKey()
            if key in self.collector:
                self.collector[key].append((data_metric,subs))
            else:
                list_tuple = []
                list_tuple.append((data_metric,subs))
                self.collector[key] = list_tuple
                print("Key created for : "+ data_metric['name']+", Time: "+ str(time.time()))
            self.evaluateCollection()


class ConfigSaver():
    def __init__(self):
        self.current_config = None
        self.manager = None
        self.publisher = None
        self.queueing_manager = None
    def setManager(self,manager):
        self.manager =  manager
    def setPublisher(self,publisher):
        self.publisher = publisher
    def setRequestHandler(self,handler):
        self.request_handler = handler
        self.checkPreviousConfig()
    def addQoS(self,data_qos):
        self.current_config['qos'] = data_qos
        self.save()
    def removeQoS(self):
        del self.current_config['qos']
    def remove(self,name):
        if name in self.current_config:
            del self.current_config[name]
        self.save()
    def stop(self):
        self.save()

    def getConfig(self):
        return self.current_config

    def save(self):
        _file = open(config.configfilepath+'/config.json','w')
        _file.write(json.dumps(self.current_config))
        _file.close()

    def mergeConfig(self,config):
        for name in config.keys():
            if not self.isNameInConfig(name):
                self.current_config[name] = config
        self.save()
    def isNameInConfig(self,name):
        return name in self.current_config

    def checkPreviousConfig(self):
        _content = ""
        try:
            _file = open(config.configfilepath+'/config.json','r')
            _content = _file.read()
        except:
            pass 
        if _content == "":
            self.current_config = {}
        else:
            self.current_config = {}
            try:
                self.current_config = json.loads(_content)
            except Exception as e:
                pass
            if self.current_config == {}:
                print("No previous config found")
                return None
            self.request_handler.setPreviousConfig(self.current_config)
        _file.close()
    def setConfig(self, _json):
        self.current_config[_json['name']] = _json
        self.save()

class Publisher():
    def __init__(self,manager,rabbit,qos_subscription_manager):
        self.manager = manager
        self.queueing_manager = rabbit
        self.publish_list = []
        self.stop_publisher = False
        self.config = None
        self.qos_subscription_manager = qos_subscription_manager
    def stop(self):
        self.stop_publisher = True
    def setConfig(self,_config):
        self.config = _config
    def isInPublishList(self,name,metric):
        for subs in self.publish_list:
            if subs.getQueue()==name and subs.getMetric()==metric:
                return True
        return False
    def matchSubs(self,beat):
        metric_name = beat['name']
        metric_labels = beat['labels']
        result = []
        result = self.getSubscriptionFromMetricName(metric_name,metric_labels)
        if 'application' in metric_labels:
            result.extend(self.getSubscriptionFromApplication(metric_labels['application']))
        return result

    def getSubscriptionFromApplication(self, application_name):
        result = []
        for subs in self.publish_list:
            labels = subs.getLabels()
            if labels == None:
                continue
            if 'application' in labels and subs.getMetric()=="*":
                if subs.getLabels()['application'] == application_name:
                    result.append(subs)
        return result
    def getSubscriptionFromMetricName(self,name,labels):
        results = []
        for subs in self.publish_list:
            if name == subs.getMetric():
                if subs.getLabels() == None:
                    results.append(subs)
                else:
                    if subs.hasLabels(labels):
                        results.append(subs)
        return results
    def addSubscription(self, consumer):
        _list_fields = ['on_change_only','labels','amount','interval']
        if self.isConsumerInPublishList(consumer):
            self.removeSubscription(consumer)
        metrics = consumer.getMetrics()
        for metric in metrics:
            for l in _list_fields:
                if not l in metric:
                    metric[l] = None
            sub = Subscription(consumer.getName(),metric['name'],metric['on_change_only'],consumer.getQueue(), metric['labels'], metric['amount'], metric['interval'])
            self.publish_list.append(sub)
    def removeSubscriptionbyName(self,name):
        consumer = self.manager.getConsumer(name)
        if consumer != None:
            self.removeSubscription(consumer)
            return True
        else:
            return False
    def removeSubscription(self, consumer):
        name = consumer.getName()
        for sub in self.publish_list:
            if sub.getConsumerName() == name:
                self.publish_list.remove(sub)
        self.config.remove(name)
    def isConsumerInPublishList(self,consumer):
        for sub in self.publish_list:
            if sub.getConsumerName()==consumer.getName():
                return True
        return False
    def push(self,publish_list,metric_json):
        if publish_list == None:
            return None
        for sub in publish_list:
            metric_name = sub.getMetric()
            consumer = self.manager.getConsumer(sub.getConsumerName())
            if consumer == None:
                continue
            if (consumer.heartbeatInterval() > 0) and (time.time() - consumer.getHeartbeat() > consumer.heartbeatInterval()):
                self.removeSubscription(consumer)
                self.manager.removeConsumer(sub.getConsumerName())
                continue

            timestamp = metric_json['@timestamp']
            #first_cond  = dateparser.parse(timestamp) > sub.getTime()
            second_cond = sub.getOnValueChangeOnly()
            third_cond = metric_json['value'] != sub.getLastValue()
            if (not second_cond) or (second_cond and third_cond):
                measurement = {'time': timestamp,'labels':metric_json['labels'],'value':metric_json['value'],'name': metric_json['name']}
                sub.setTime(parse(timestamp))
                sub.setLastValue(metric_json['value'])
                queue = sub.getQueue()
                resp = responder('stream','success',measurement)
                if consumer.getExchange() == None:
                    self.queueing_manager.sendToClient(queue,resp)
                else:
                    self.queueing_manager.addTask({'queue':queue,'message': resp,'exchange': consumer.getExchange()})
                _job_name = "all"
                name = metric_json['name']
                if 'application' in metric_json['labels']:
                    _job_name = metric_json['labels']['application']
                _json_object = {'index':hashlib.md5(name+_job_name).hexdigest(),'type':'stream','last': int(time.time()),'name': name,'n_access':0,'from':int(time.time()),'job': _job_name}
                #saveMetric(_json_object)
                #monitoring.add('output_data',len(resp_text))
                #self.queueing_manager.sendToClient(queue,resp)



class Subscription():
    def __init__(self,consumer_name,metric,on_change_only,queue,labels,amount,interval):
        self.consumer_name = consumer_name
        self.queue = queue
        self.metric = metric
        self.time = time.time()
        self.last_value = 0
        self.on_value_changed_only = on_change_only
        self.labels = labels
        self.amount = amount
        self.interval = interval
        self.subs_signature = hashlib.md5(self.metric+json.dumps(labels)).hexdigest
        self.parseValue()

    def parseValue(self):
        if self.amount == None:
            self.amount = 1
        if int(self.amount) > 100:
            self.amount = 100
        if self.on_value_changed_only == None:
            self.on_value_changed_only = False
        if self.interval == None or self.interval < 1:
            self.interval = 5
        if self.labels != None:
            if type(self.labels) != type({}):
                self.labels = None
    def getLabels(self):
        return self.labels
    def hasLabels(self,labels):
        if labels == None or labels == {}:
            return True
        for key in self.labels.keys():
            if key in labels:
                if labels[key] != self.labels[key]:
                    return False
        return True
    def getAmount(self):
        return str(self.amount)
    def getConsumerName(self):
        return self.consumer_name
    def getSignature(self):
        return self.subs_signature
    def getMetric(self):
        return self.metric
    def getInterval(self):
        return self.interval
    def setQueue(self,queue):
        self.queue = queue
    def getQueue(self):
        return self.queue
    def getTime(self):
        return self.time
    def setTime(self,time):
        self.time = int(time.strftime('%s'))
    def setLastValue(self,value):
        self.last_value = value
    def getLastValue(self):
        return self.last_value
    def getOnValueChangeOnly(self):
        return self.on_value_changed_only
    def __str__(self):
        return {'consumer': self.consumer_name,'queue': self.queue, 'metric': self.metric,'labels':self.labels}


def main():
    manager = ConsumerManager()
    request = RequestHandler()
    request.setManager(manager)
    queue_manager = None
    if config.manager['brocker'] == "RabbitMQ":
        #queue_manager = RabbitMQ(manager,request,config.rabbitmq['username'],config.rabbitmq['password'],config.rabbitmq['host'],int(config.rabbitmq['port']))
        queue_manager = ThreadPublisher(config.rabbitmq['username'],config.rabbitmq['password'],config.rabbitmq['host'],int(config.rabbitmq['port']),"",0.1)
    else:
        queue_manager = Kafka(config.kafka['hosts'],config.kafka['topic'],config.kafka['group-id'],manager,request)

    ntry = int(config.manager['ntry'])
    connected = False
    n_tries = 0
    while not connected:
        if n_tries == ntry:
            print("Impossible to establish connexion to RabbitMQ")
            break
        try:
            n_tries +=1
            print(str(n_tries)+' , try to connect to brocker..')
            queue_manager.start()
            connected = True
            request.setQueueManager(queue_manager)
        except (KeyboardInterrupt, SystemExit):
            connected = True
            queue_manager.stop()
        except Exception as e:
            print("Auto reconnection in 5 secs ...")
            queue_manager.stop()
            time.sleep(5)

if __name__ == "__main__":
    main()
