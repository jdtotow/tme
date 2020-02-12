import os, time, json, pika, sys 
from configsaver import ConfigSaver
from consumermanager import MultiThreadConsumerManager
#from statsmodels.tsa.holtwinters import ExponentialSmoothing
from dateutil.parser import parse

rabbitmq_username = os.environ.get("RABBITMQUSERNAME","richardm")
rabbitmq_password = os.environ.get("RABBITMQPASSWORD","bigdatastack")
rabbitmq_host = os.environ.get("RABBITMQHOST","localhost")
rabbitmq_port = int(os.environ.get("RABBITMQPORT","5672"))
rabbitmq_exchange = os.environ.get("RABBITMQEXCHANGE","")
ml_executor_queue = os.environ.get("MLEXECUTORQUEUE","ml_executor")
n_tries = int(os.environ.get("NTRIES","10"))

dataset_make_duration = int(os.environ.get("DATASETMAKEDURATION","600"))
max_n_features = int(os.environ.get("MAXNFEATURES","20"))
manager_queue_name = os.environ.get("MANAGERQUEUENAME","manager")

max_data_points = int(os.environ.get("MAXDATAPOINTS","10000"))
max_number_of_row = int(os.environ.get("MAXNUMBERROWS","100"))

class Prediction():
    def __init__(self):
        self.list_time_series = {}
        self.max_data_points = max_data_points
        self.previous_prediction_dict = {}
        self.dict_interval_time = {}
        self.dict_arrival_time = {}
    def makeKey(self,application,slo):
        return slo+"-"+application
    def addPoint(self,value,application,slo):
        key = self.makeKey(application,slo)
        if key in self.list_time_series:
            if len(self.list_time_series[key]) == self.max_data_points:
                self.list_time_series[key].pop(0) #remove the first element
            self.list_time_series[key].append(value)
        else:
            _list = []
            _list.append(value)
            self.list_time_series[key] = _list
    def getValues(self,application,slo):
        key = self.makeKey(application,slo)
        if key in self.list_time_series:
            return self.list_time_series[key]
        return []
    
    def getLastPrediction(self,application,slo):
        key = self.makeKey(application,slo)
        if key in self.previous_prediction_dict:
            return self.previous_prediction_dict[key]
        else:
            return None 
    def addTimeInterval(self,application,slo,interval):
        key = self.makeKey(application,slo)
        if key in self.dict_interval_time:
            self.dict_interval_time[key].append(interval)
        else:
            list_interval = []
            list_interval.append(interval)
            self.dict_interval_time[key] = list_interval
            
    def findTimeInterval(self,application,slo):
        key = self.makeKey(application,slo)
        list_interval = None 
        if key in self.dict_interval_time:
            list_interval = self.dict_interval_time[key]
        if list_interval != None:
            return sum(list_interval)/len(list_interval)
        return None 

    def predict(self,data):
        try:
            if len(data) == 0:
                return None 
            model = ExponentialSmoothing(data)
            model_fit = model.fit()
            value_predicted = model_fit.predict(len(data), len(data))
            return value_predicted[0].item()
        except:
            return None
    def predictionAccuracy(self,application,slo,current_value):
        prediction = self.getLastPrediction(application,slo)
        if prediction != None:
            if prediction > current_value:
                return (current_value/prediction)*100
            elif prediction < current_value:
                return (prediction/current_value)*100
            else:
                return 100 
        else:
            return None 
    def getIntervalTimeSeries(self,application,slo):
        key = self.makeKey(application,slo)
        if key in self.dict_interval_time:
            list_intervals = self.dict_interval_time[key]
            return sum(list_intervals)/len(list_intervals)
        return None 
    def updateTimeSeriesInterval(self,_json):
        application = _json['application']
        slo = _json['metric']
        key = self.makeKey(application,slo)
        if key in self.dict_arrival_time:
            list_arrival = self.dict_arrival_time[key]
            if len(list_arrival) == 10:
                list_arrival.pop(0)
            last_time = list_arrival[-1]
            _now = (_json['start'] + _json['stop'])/2
            if _now > last_time:
                list_arrival.append(_now)
                if key in self.dict_interval_time:
                    if len(self.dict_interval_time[key]) == 10:
                        self.dict_interval_time[key].pop(0)
                    self.dict_interval_time[key].append(_now - last_time)
                else:
                    list_intervals = []
                    list_intervals.append(_now - last_time)
                    self.dict_interval_time[key] = list_intervals
        else:
            list_arrival = []
            _now = (_json['start']+_json['stop'])/2
            list_arrival.append(_now)
            self.dict_arrival_time[key] = list_arrival
            if key in self.dict_interval_time:
                if len(self.dict_interval_time[key]) == 10:
                    self.dict_interval_time[key].pop(0)
                self.dict_interval_time[key].append(_now)
            else:
                list_intervals = []
                list_intervals.append(_now)
                self.dict_interval_time[key] = list_intervals

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

class Application():
    def __init__(self,name,slo):
        self.name = name 
        self.slo = slo 
        self.features = None 
    def getKey(self):
        return self.name+"-"+self.slo 
    def setFeatures(self,features):
        self.features = features
    def getFeatures(self):
        return self.features

class DatasetElement():
    def __init__(self,features):
        self.features = features
        self.list_values = {}
        self.existing_feature = []
        self.slo = None
        self.time = None 
    def setTime(self,_time):
        self.time = _time  
    def setSLO(self,slo):
        self.slo = slo
    def getValue(self,feature):
        if feature in self.existing_feature:
            _list = self.list_values[feature]
            return sum(_list)/len(_list)
        return None  
    def addValue(self,slo,value):
        if not slo in self.existing_feature:
            _list = []
            _list.append(float(value))
            self.list_values[slo] = _list 
            self.existing_feature.append(slo) 
        else:
            self.list_values[slo].append(float(value))
        return True 
    def toRow(self,previous_row):
        result = ""
        #getting the slo
        slo_value = self.getValue(self.slo)
        if slo_value == None:
            if previous_row == None:
                slo_value = 0
                self.addValue(self.slo,0)
            else:
                slo_value = previous_row.getValue(self.slo)
                self.addValue(self.slo,slo_value)
        result = str(slo_value)+ ","
        #adding time column
        result = result + str(self.time) +","
        for feature in self.features:
            key = str(feature['metric'])
            _value = self.getValue(key)
            if _value == None:
                if previous_row == None:
                    _value = 0
                    self.addValue(key,float(0))
                else:
                    _value = previous_row.getValue(key)
                    self.addValue(key,_value)
            result = "{0}{1},".format(result,_value)
        if result !="":
            return result[:-1]
        return None
    def getContent(self):
        return self.list_values
        

class Basket():
    def __init__(self, application_name,slo,features):
        self.application_name = application_name
        self.slo = slo 
        self.features = features #[{'application':'application','metric': slo}]
        self.structure_dataset = {}
        self.manager = None 
        self.file = open("/dataset/"+self.application_name+"-"+self.slo+".csv", "a+")
        self.size_to_write = 100
        self.number_of_row = 0
        self.addTitleToFile()
    def dataPointIsSLO(self,application,slo):
        return application == self.application_name and slo == self.slo 
    def addTitleToFile(self):
        if os.stat("/dataset/"+self.application_name+"-"+self.slo+".csv").st_size > 0:
            return None 
        line = self.slo+",time,"
        for feature in self.features:
            line += feature['metric']+","
        self.file.write(line[:-1]+"\n") #removing the last ',' then write 
        self.file.close()
    def setManager(self,manager):
        self.manager = manager 
    def getName(self):
        return self.application_name
    def getSLO(self):
        return self.slo 
    def getFeatures(self):
        return self.features
    def hasFeature(self,application,slo):
        for feature in self.features:
            if feature['application'] == application and feature['metric'] == slo:
                return True 
        return False 
    def addDatasetElement(self,value,_time,slo):
        t = parse(_time)
        key = int(time.mktime(t.timetuple()))
        if key in self.structure_dataset:
            element = self.structure_dataset[key]
            element.addValue(str(slo),value)
        else:
            element = DatasetElement(self.features)
            element.setSLO(self.slo)
            element.setTime(key)
            element.addValue(slo,value)
            self.structure_dataset[key] = element
        if len(self.structure_dataset.keys()) >= self.size_to_write*1.5:
            self.writeDataToFile()
        print("structure size <<"+str(len(self.structure_dataset.keys()))+">> for the slo <<"+slo+">>")
    def closeDataset(self):
        self.file = open("/dataset/"+self.application_name+"-"+self.slo+".csv", "a+")
        previous_row = None
        for key in self.structure_dataset.keys():
            element = self.structure_dataset[key]
            line = element.toRow(previous_row)
            if line != None:
                self.file.write(line+"\n")
                del self.structure_dataset[key]
            previous_row = element
        self.file.close()

    def peekTheSmollest(self):
        smollest_key = None 
        for key in self.structure_dataset.keys():
            if smollest_key == None or key < smollest_key:
                smollest_key = key 
        return smollest_key

    def writeDataToFile(self):
        self.file = open("/dataset/"+self.application_name+"-"+self.slo+".csv", "a+")
        index = 0
        _keys = self.structure_dataset.keys()
        previous_row = None 
        while index < self.size_to_write:
            key = self.peekTheSmollest()
            if key in self.structure_dataset:
                element = self.structure_dataset[key]
                try:
                    line = element.toRow(previous_row)
                except Exception as e:
                    print(e)
                if line != None:
                    self.file.write(line+"\n")
                    self.number_of_row +=1
                del self.structure_dataset[key]
                index +=1
                previous_row = element
        self.file.close()
        if self.number_of_row == max_data_points:
            self.closeDataset()
            for feature in self.features:
                application, slo = feature['application'], feature['metric']
                self.manager.unsubscribe(application,slo)

class DatasetMaker():
    def __init__(self,manager):
        self.applications = {}
        self.config = ConfigSaver(self)
        self.manager = manager 
        self.list_applications_slo_subscription = {}
        self.basket_dict = {}
        self.current_config = {}
    def setPreviousConfig(self,config):
        self.current_config = config 
        for key, _json in self.current_config.iteritems():
            self.addApplication(_json['application'],_json['slo'],_json['features']) 
        print("ML config reloaded successfuly")
    def makeKey(self,application,slo):
        return application+"-"+slo 
    def createBasket(self,application_name,slo,features):
        basket = self.getBasket(application_name,slo)
        if basket == None:
            basket = Basket(application_name,slo,features)
            basket.setManager(self.manager)
            self.basket_dict[application_name+"-"+slo] = basket 
            return True 
        return False 
    def getBasket(self,application_name,slo):
        key = application_name+"-"+slo 
        if key in self.basket_dict:
            return self.basket_dict[key]
        return None 
    def getBasketByDataStream(self,application,slo):
        result = []
        for key in self.basket_dict.keys():
            if self.basket_dict[key].hasFeature(application,slo) or self.basket_dict[key].dataPointIsSLO(application,slo):
                result.append(self.basket_dict[key])
        return result 
    def getApplication(self,application,slo):
        key = self.makeKey(application,slo)
        if key in self.applications:
            return self.applications[key]
        return None 
    def prepareRequestForFeatures(self,features):
        for feature in features:
            application, slo = feature['application'], feature['metric']
            key = application+"-"+slo 
            if not key in self.list_applications_slo_subscription:
                self.sendSubscription(application,slo)
    def addApplication(self,application,slo,features):
        key = self.makeKey(application,slo)
        if not key in self.applications:
            app = Application(application,slo)
            app.setFeatures(features)
            self.applications[key] = app 
            #self.config.setConfig(key,{'application': application,'slo': slo,'features': features})
            self.createBasket(application,slo,features)
            print("Application <<"+application+">> with the slo <<"+slo+">> added")
            if not key in self.list_applications_slo_subscription:
                self.sendSubscription(application,slo)
                self.prepareRequestForFeatures(features)
            return True 
        return False 
    def sendSubscription(self,application,slo):
        message = {}
        message['request'] = 'subscription'
        data = {}
        data['name'] = "ml_executor_"+application+"-"+slo
        data['queue'] = ml_executor_queue
        data['heartbeat_interval'] = 0
        metrics = []
        metric = {}
        metric['name'] = slo
        metric['on_change_only'] = False
        metric['labels'] = {'application':application}
        metrics.append(metric)
        data['metrics'] = metrics
        message['data'] = data
        self.manager.sendToClient(manager_queue_name,json.dumps(message))
        self.list_applications_slo_subscription[application+"-"+slo] = True 
        print("Subscription request sent for the application <<"+application+">> with the slo <<"+slo+">>")
    
class Manager():
    def __init__(self):
        self.config = None 
        self.dataset_maker = DatasetMaker(self)
        self.consumer = None  
    def setConsumer(self,consumer):
        self.consumer = consumer 
    def stop(self):
        self.consumer.stop()

    def sendToClient(self,queue,content):
        rabbitmq = PublisherOnce("",queue,content)
        rabbitmq.publish()

    def unsubscribe(self,application_name,slo):
        request = {'name': "ml_executor_"+application_name+"-"+slo,'queue': ml_executor_queue,'request':'remove_subscription'}
        rabbitmq = PublisherOnce("",manager_queue_name,json.dumps(request))
        rabbitmq.publish()
        print("Unsubscribe request send for the <<"+application_name+">> with the metric <<"+slo+">>")

    def setData(self,data):
        _json = None 
        try:
            _json = json.loads(data)
        except:
            print("Cannot parse json content")
        if 'request' in _json:
            if _json['request'] == "prepare_dataset":
                self.prepareDataset(_json)
            elif _json['request'] == "stream":
                self.handleSubscriptionData(_json)
    def prepareDataset(self,_json):
        application = _json['data']['application']['name']
        slo = _json['data']['application']['slo']
        self.dataset_maker.addApplication(application,slo,_json['data']['metrics'])
    def handleSubscriptionData(self,_json):
        baskets = self.dataset_maker.getBasketByDataStream(_json['data']['labels']['application'],_json['data']['name'])
        if baskets != []:
            for basket in baskets:
                basket.addDatasetElement(_json['data']['value'],_json['data']['time'],_json['data']['name'])

def main():
    manager = Manager()
    rabbitmq = MultiThreadConsumerManager(3,rabbitmq_username,rabbitmq_password,rabbitmq_host,rabbitmq_port,10,rabbitmq_exchange,manager,ml_executor_queue)
    manager.setConsumer(rabbitmq)
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
        except (KeyboardInterrupt, SystemExit):
            connected = True
            manager.stop()
            rabbitmq.stop()
        except Exception as e:
            print(e)
            print("Auto reconnection in 5 secs ...")
            rabbitmq.stop()
            time.sleep(5)

if __name__ == "__main__":
    main()