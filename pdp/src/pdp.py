import pika, json, time, os
from threading import Thread 
from configsaver import ConfigSaver
from consumermanager import MultiThreadConsumerManager
#from publisher import ThreadPublisher
from dateutil.parser import parse 
import numpy as np 
from dtw import dtw 

consumer_queue_name = os.environ.get("CONSUMERQUEUENAME","pdp")
rabbitmq_host = os.environ.get("RABBITMQHOSTNAME","localhost")
rabbitmq_port = int(os.environ.get("RABBITMQPORT","5672"))
rabbitmq_username = os.environ.get("RABBITMQUSERNAME","richardm")
rabbitmq_password = os.environ.get("RABBITMQPASSWORD","bigdatastack")
n_tries = int(os.environ.get("NTRIES","10"))
ml_consumer_queue_name = os.environ.get("MLCONSUMERQUEUENAME","ml_executor")
manager_queue_name = os.environ.get("MANAGERQUEUENAME","manager")
#//////////////////////////////////////////////////////////////////////////////
_evaluation_interval = int(os.environ.get("EVALUATIONINTERVAL","300"))
last_all_applications_list_updated = time.time()
all_applications_list_update_interval = int(os.environ.get("APPLICATIONSLISTUPDATEINTERVAL","400"))
baskets_evaluation_period = int(os.environ.get("BASKETEVALUATIONPERIOD","20"))
last_baskets_evaluation = time.time()
_max_relevant_influencers = int(os.environ.get("MAXNUMBERFEATURE","10"))

class PublisherOnce():
    def __init__(self,exchange,queue,message):
        self.exchange = exchange
        self.queue = queue
        self.message = message 
    def publish(self):
        connection = None 
        try:
            credentials = pika.PlainCredentials(rabbitmq_username, rabbitmq_password)
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host,port=rabbitmq_port,credentials=credentials))
            channel = connection.channel()
            channel.basic_publish(exchange=self.exchange,routing_key=self.queue,body=self.message,properties=pika.BasicProperties(content_type='text/json',delivery_mode=1))
            connection.close()
            return True 
        except Exception as e:
            print(e)
            print("Could not publish message, auto reconnect in 2s")
            time.sleep(2)
            if connection != None and not connection.is_closed:
                connection.close()
                self.publish()

class ObservedApplication():
    def __init__(self, name, slo,dependencies,violation):
        self.name = name 
        self.slo = slo 
        self.key = name+"-"+slo
        self.dependencies = dependencies
        self.violation = violation
    def getViolation(self):
        return self.violation
    def getName(self):
        return self.name 
    def getSLO(self):
        return self.slo
    def getKey(self):
        return self.key 
    def getDependencies(self):
        return self.dependencies
    def hasDependency(self,dependency):
        return dependency in self.dependencies

class ObservedApplicationManager():
    def __init__(self):
        self.applications = {}
        self.config = ConfigSaver(self) 
        self.config.checkPreviousConfig()
    def setPreviousConfig(self,previous_config):
        for key, app in previous_config.iteritems():
            self.addApplication(app['name'],app['slo'],app['dependencies'],app['violation'])
    def addApplication(self,name,slo,dependencies,violation):
        app = self.getApplication(name,slo)
        if app == None:
            app = ObservedApplication(name,slo,dependencies,violation)
            self.applications[app.getKey()] = app 
            self.config.setConfig(app.getKey(),{'name': app.getName(),'slo':app.getSLO(),'dependencies': dependencies,'violation':violation})
            return True 
        return False 
    def getApplication(self,name,slo):
        key = name+"-"+slo
        if key in self.applications:
            return self.applications[key]
        else:
            return None 
    def removeApplication(self,name,slo):
        key = name+"-"+slo
        if key in self.applications:
            del self.applications[key]
            self.config.remove(key)
    def getAllApplications(self):
        result = []
        for key in self.applications:
            result.append(self.applications[key])
        return result 
    def isDependencyInUsedElseWhere(self,name,slo,dependency):
        app = self.getApplication(name,slo)
        if app != None:
            apps = self.getAllApplications()
            for _app in apps:
                if _app.getKey() == app.getKey():
                    continue 
                if _app.hasDependency(dependency):
                    return True 
        return False 
    def getApplicationsByDataMetric(self,_json):
        application_name = _json['data']['labels']['application']
        apps = self.getAllApplications()
        result = []
        for app in apps:
            if app.getName() == application_name or application_name in app.getDependencies():
                result.append(app)
        return result 

class DataPoint():
    def __init__(self,timestamp,value):
        self.timestamp = timestamp
        self.value = value 
    def getTimeStamp(self):
        return self.timestamp
    def getValue(self):
        return self.value 

class TimeSerie():
    def __init__(self,metric_name,application_name,_start,_stop):
        self.metric_name = metric_name
        self.application_name = application_name
        self.list_data_points = {}
        self.start = _start
        self.stop = _stop
        self.size = 0
        self.is_slo = False 
    def getMetricName(self):
        return self.metric_name
    def getApplicationName(self):
        return self.application_name
    def addDataPoint(self,_time,value):
        t = parse(_time)
        timestamp = int(time.mktime(t.timetuple()))
        data_point = DataPoint(timestamp,float(value))
        self.list_data_points[timestamp] = data_point
        self.size +=1
    def setIsSLO(self):
        self.is_slo = True 
    def isSLO(self):
        return self.is_slo
    def setStart(self,_start):
        self.start = _start
    def setStop(self,_stop):
        self.stop = _stop
    def getKey(self):
        return self.application_name+"-"+self.metric_name
    def getValues(self):
        keys = self.list_data_points.keys()
        keys.sort()
        result = []
        for key in keys:
            result.append(self.list_data_points[key].getValue())
        return result
    def getSize(self):
        return self.size 
    def isConstant(self):
        result = True  
        value = self.list_data_points[self.list_data_points.keys()[0]].getValue()
        for key in self.list_data_points.keys():
            data_point = self.list_data_points[key]
            if data_point.getValue() != value:
                result = False 
        return result

class Basket():
    def __init__(self,slo,application_name):
        self.slo = slo 
        self.application_name = application_name
        self.list_time_series = {}
        self.start = None 
        self.stop = None 
        self.list_time_series_dropped = []
        self.manager = None 
        self.dependencies = None 
        self.violation = None 
        self.state = 'active'
    def setState(self,state):
        self.state = state 
    def getState(self):
        return self.state 
    def setViolation(self,violation):
        self.violation = violation
    def getViolation(self):
        return self.violation
    def setDependencies(self,dependencies):
        self.dependencies = dependencies
    def getDependencies(self):
        return self.dependencies
    def setManager(self,manager):
        self.manager = manager 
    def getSLO(self):
        return self.slo 
    def getApplicationName(self):
        return self.application_name 
    def createTimeSerie(self,metric_name,application_name):
        result = "normal"
        key = application_name+"-"+metric_name
        if not key in self.list_time_series_dropped:
            time_serie = TimeSerie(metric_name,application_name,self.start,self.stop)
            if metric_name == self.slo:
                time_serie.setIsSLO()
                print("SLO detected for the application<<"+application_name+">>")
                result = "slo"
            self.list_time_series[time_serie.getKey()] = time_serie 
        return result
    def getSLOTimeSerie(self):
        for key in self.list_time_series.keys():
            if self.list_time_series[key].isSLO():
                return self.list_time_series[key]
        return None 
    def removeTimeSerieByKey(self,key):
        if key in self.list_time_series:
            del self.list_time_series[key]
            self.list_time_series_dropped.append(key)
    def removeTimeSerie(self,metric_name,application_name):
        key = application_name+"-"+metric_name
        if key in self.list_time_series:
            del self.list_time_series[key]
            self.list_time_series_dropped.append(key)
    def getTimeSerie(self,metric_name,application_name):
        key = application_name+"-"+metric_name
        if key in self.list_time_series:
            return self.list_time_series[key]
        return None 
    def getTimeSerieByKey(self,key):
        if key in self.list_time_series:
            return self.list_time_series[key]
        return None
    def addPoint(self,metric_name,application_name,_time,value):
        time_serie = self.getTimeSerie(metric_name,application_name)
        if time_serie != None:
            time_serie.addDataPoint(_time,value)
        else:
            response = self.createTimeSerie(metric_name,application_name)
            if response == "slo":
                for dependency in self.dependencies:
                    if not dependency in self.manager.getListApplicationsSubscription():
                        self.manager.sendSubscriptionRequest(dependency)
                        print("Dependency subscription <<"+dependency+">> for the application <<"+application_name+">> sent")
            self.addPoint(metric_name,application_name,_time,value)
    def getKey(self):
        return self.application_name+"-"+self.slo
    def setTime(self,_start,_stop):
        self.start = int(_start)
        self.stop = int(_stop)
    def setStart(self,_start):
        self.start = _start
        self.stop = _start + _evaluation_interval
    def getStartTime(self):
        return self.start 
    def getStopTime(self):
        return self.stop 
    def empty(self):
        for key in self.list_time_series.keys():
            try:
                del self.list_time_series[key]
            except:
                pass 
        print("Basket has been reinitialized")
    def getAllTimeSeries(self):
        result = []
        for key in self.list_time_series.keys():
            try:
                result.append(self.list_time_series[key])
            except:
                pass 
        return result
    def computeDistance(self,list_value_slo,list_value_time_serie):
        try:
            x = np.array(list_value_slo)
            y = np.array(list_value_time_serie)
            manhattan_distance = lambda x, y: np.abs(x - y)
            d, cost_matrix, acc_cost_matrix, path = dtw(x, y, dist=manhattan_distance)
            return d 
        except:
            return 2000
    def evaluate(self):
        slo_time_serie = self.getSLOTimeSerie()
        if slo_time_serie == None:
            print("SLO values not ready")
            return [] 
        all_time_series = self.getAllTimeSeries()
        result = []
        for time_series in all_time_series:
            if time_series.isSLO():
                continue
            if time_series.isConstant():
                continue
            values = time_series.getValues()
            slo_values = slo_time_serie.getValues()
            if len(slo_values) == 0:
                break 
            distance = self.computeDistance(slo_values,values)
            result.append({'distance': distance,'key': time_series.getKey()})
        return result 


class BasketManager():
    def __init__(self):
        self.dict_basket = {}
        self.evaluation_interval = _evaluation_interval #seconds
        self.max_relevant_influencers = _max_relevant_influencers
        self.manager = None 
    def setManager(self,manager):
        self.manager = manager 
    def createBasket(self,slo,application_name,dependencies):
        basket = Basket(slo,application_name)
        basket.setTime(time.time(),time.time()+self.evaluation_interval)
        basket.setManager(self.manager)
        basket.setDependencies(dependencies)
        self.dict_basket[basket.getKey()] = basket
        return basket 
    def getBasket(self,slo,application_name):
        key = application_name+"-"+slo
        if key in self.dict_basket:
            return self.dict_basket[key]
        return None 
    def reduce(self,ranking_list,basket):
        if ranking_list == []:
            return [] 
        if len(ranking_list) < self.max_relevant_influencers:
            return ranking_list
        index = self.max_relevant_influencers - 1
        while index < len(ranking_list):
            key = ranking_list[index]['key'] 
            basket.removeTimeSerieByKey(key)
            del ranking_list[index]
            index +=1
        return ranking_list
    def sendReport(self,basket, ranking_list):
        report = {'violation': basket.getViolation(),'time': time.time()}
        application = {'name': basket.getApplicationName(),'slo':basket.getSLO()}
        metrics = []
        index = 0
        for element in ranking_list:
            if index == self.max_relevant_influencers:
                break 
            time_series = basket.getTimeSerieByKey(element['key'])
            if time_series != None:
                _tuple = {'metric': time_series.getMetricName(),'application': time_series.getApplicationName(),'rank': element['distance']}
                metrics.append(_tuple)
            index +=1
        report['application'] = application
        report['metrics'] = metrics
        message = {'request': 'prepare_dataset','data': report}
        print(report)
        rabbitmq = PublisherOnce("",ml_consumer_queue_name,json.dumps(message))
        rabbitmq.publish()
        print("Report sent for the application <<"+application['name']+">>")
    def verifyDependencies(self,ranking_list,basket):
        dependencies = basket.getDependencies()
        apps = []
        for element in ranking_list:
            time_series = basket.getTimeSerieByKey(element['key'])
            if time_series != None:
                application_name = time_series.getApplicationName()
                if not application_name in apps:
                    apps.append(application_name)
        
        for dependency in dependencies:
            exist = False 
            for element in ranking_list:
                if dependency in apps:
                    exist = True 
            if not exist:
                self.manager.unsubscribe(dependency)
    def evaluateBackets(self):
        for key in self.dict_basket.keys():
            basket = self.dict_basket[key]
            if basket.getStopTime() <= time.time():
                result = basket.evaluate()
                ranking_list = sorted(result, key = lambda i: i['distance'],reverse=False)
                if len(ranking_list) > 0:
                    self.sendReport(basket,ranking_list)
                    self.manager.pauseBasket(basket)
                else:
                    basket.empty()
                    basket.setTime(time.time(),time.time()+self.evaluation_interval)

class Manager():
    def __init__(self):
        self.observed_application_manager = ObservedApplicationManager()
        self.list_applications_subscription = []
        self.basket_manager = BasketManager()
        self.basket_manager.setManager(self)
        self.all_available_applications = []
        self.consumer = None 
    def setConsumer(self,consumer):
        self.consumer = consumer 
    def getListApplicationsSubscription(self):
        return self.list_applications_subscription
    def getAllAvailableApplication(self):
        global last_all_applications_list_updated
        message = {'request': 'get_available_applications','queue':consumer_queue_name}
        rabbitmq = PublisherOnce("",manager_queue_name,json.dumps(message))
        rabbitmq.publish()
        print("Request get all applications sent")
        last_all_applications_list_updated = time.time()
    def updateAvailableApplication(self,data):
        for application in data['applications']:
            if not application in self.all_available_applications:
                self.all_available_applications.append(application)
    def pauseBasket(self,basket):
        basket.setState('paused')
        self.consumer.checkThreads()
        application_name = basket.getApplicationName()
        self.removeApplication({'application': application_name,'slo': basket.getSLO()})
        print("The application <<"+application_name+">> with the metric <<"+basket.getSLO()+">> will be stopped")
    def restartBasket(self,application,slo):
        basket = self.basket_manager.getBasket(slo,application)
        basket.setStart(time.time())
        self.consumer.checkThreads()
        if basket != None:
            basket.setState('active')
            dependencies = None 
            if len(self.all_available_applications) == 0:
                dependencies = basket.getDependencies()
            else:
                dependencies = self.all_available_applications
            self.AddApplication(application,slo,dependencies,basket.getViolation())
            print("Application <<"+application+">> restarted")
            print("sending dependencies subscriptions")
            for dependency in dependencies:
                if not dependency in self.list_applications_subscription:
                    self.sendSubscriptionRequest(dependency)
    def sendToClient(self,queue,content):
        rabbitmq = PublisherOnce("",queue,content)
        rabbitmq.publish()
    def sendPongRequest(self):
        request = {}
        request['queue'] = consumer_queue_name
        rabbitmq = PublisherOnce("",manager_queue_name,json.dumps(request))
        rabbitmq.publish()
    def setData(self,body):
        _json = None 
        try:
            _json = json.loads(body)
        except Exception as e:
            print(e)
            return False 
        if 'request' in _json:
            if _json['request'] == "add_application":
                if self.AddApplication(_json['data']['name'],_json['data']['slo'],_json['data']['dependencies'],_json['violation']):
                    print("application "+ _json['data']['name']+" has been added")
                else:
                    print("The application has not been added")
            elif _json['request'] == "stream":
                self.addElement(_json)
            elif _json['request'] == "ping":
                self.sendPongRequest()
            elif _json['request'] == "remove_application":
                self.removeApplication(_json)
            elif _json['request'] == "restart_application":
                self.restartBasket(_json['data']['application'],_json['data']['slo'])
                print("application "+ _json['data']['application']+" has been restarted")
            elif _json['request'] == "available_applications":
                self.updateAvailableApplication(_json['data'])
                print("Applications list updated")
            elif _json['request'] == "subscription":
                print(_json)
            elif _json['request'] == "pause_application":
                self.stopApplication(_json)
            else:
                print("Unknow request")
                print(_json['request'])
        if time.time() - all_applications_list_update_interval > last_all_applications_list_updated:
            self.getAllAvailableApplication()
    def addElement(self,_json):
        global last_baskets_evaluation
        if 'application' in _json['data']['labels']:
            apps = self.observed_application_manager.getApplicationsByDataMetric(_json)
            if apps != []:
                for app in apps:
                    metric_name = _json['data']['name']
                    application = _json['data']['labels']['application']
                    basket = self.basket_manager.getBasket(app.getSLO(),app.getName())
                    if basket == None:
                        basket = self.basket_manager.createBasket(app.getSLO(),app.getName(),app.getDependencies())
                        basket.setViolation(app.getViolation())
                        basket.addPoint(metric_name,application,_json['data']['time'],_json['data']['value'])
                        print("Basket created for <<"+app.getName()+">>")
                    else:
                        basket.addPoint(metric_name,application,_json['data']['time'],_json['data']['value'])
                        if time.time() - baskets_evaluation_period > last_baskets_evaluation:
                            self.basket_manager.evaluateBackets()
                            last_baskets_evaluation = time.time()
    def stopApplication(self,_json):
        application_name = _json['data']['application']
        slo = _json['data']['slo']
        basket = self.basket_manager.getBasket(slo,application_name)
        if basket != None:
            self.pauseBasket(basket)
    def unsubscribe(self,application_name):
        request = {'name': 'pdp_'+application_name,'queue': consumer_queue_name,'request':'remove_subscription'}
        rabbitmq = PublisherOnce("",manager_queue_name,json.dumps(request))
        rabbitmq.publish()
        if application_name in self.list_applications_subscription:
            self.list_applications_subscription.remove(application_name)
    def removeApplication(self,_json):
        required_field = ['application','slo']
        for field in required_field:
            if not field in _json:
                print("Field <"+field+"> is missing")
                return False 
        app = self.observed_application_manager.getApplication(_json['application'],_json['slo'])
        if app != None:
            dependencies = app.getDependencies()
            if not _json['application'] in dependencies:
                dependencies.append(_json['application'])
            for dependency in dependencies:
                if not self.observed_application_manager.isDependencyInUsedElseWhere(app.getName(),app.getSLO(),dependency):
                    self.unsubscribe(dependency)
            self.observed_application_manager.removeApplication(app.getName(),app.getSLO())
    def stop(self):
        apps = self.observed_application_manager.getAllApplications()
        for app in apps:
            self.unsubscribe(app.getName())
        self.consumer.stop()
    def sendSubscriptionRequest(self,application_name):
        message = {}
        message['request'] = 'subscription'
        data = {}
        data['name'] = 'pdp_'+application_name
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
        rabbitmq = PublisherOnce("",manager_queue_name,json.dumps(message))
        rabbitmq.publish()
        self.list_applications_subscription.append(application_name)
        
    def AddApplication(self,name,slo,dependencies,violation):
        if self.observed_application_manager.addApplication(name,slo,dependencies,violation):
            if not name in self.list_applications_subscription:
                self.sendSubscriptionRequest(name)
                print("Subscription request sent for the application <<"+name+">>")
                return True 
        else:
            print("Application not fully started")
            app = self.observed_application_manager.getApplication(name,slo)
            if app != None:
                print("Restart forced ...")
                self.sendSubscriptionRequest(name)
                return True 
            else:
                print("Cannot force restarting the application")
                return False 
         
def main():
    manager = Manager()
    rabbitmq = MultiThreadConsumerManager(1,rabbitmq_username,rabbitmq_password,rabbitmq_host,rabbitmq_port,10,"",manager,consumer_queue_name)
    connected = False
    index = 0
    while not connected:
        if index == n_tries:
            print("Impossible to establish connexion to RabbitMQ")
            break
        try:
            index +=1
            print(str(index)+' , try to connect to brocker ...')
            rabbitmq.start()
            connected = True
            manager.setConsumer(rabbitmq)
        except (KeyboardInterrupt, SystemExit):
            connected = True
            manager.stop()
            rabbitmq.stop()
        except Exception as e:
            print(e)
            print("Auto reconnection in 5 secs ...")
            rabbitmq.stop()
            time.sleep(5)

if __name__== "__main__":
    main()
