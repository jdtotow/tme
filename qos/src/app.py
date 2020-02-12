import pika, json, time, os, requests
import numpy as np 
import panda as pd 
from threading import Thread 
from configsaver import ConfigSaver
from publisher import ThreadPublisher 

n_tries = int(os.environ.get("NTRIES","10"))
username = os.environ.get("RABBITMQUSERNAME","richardm")
password = os.environ.get("RABBITMQPASSWORD","bigdatastack")
host = os.environ.get("RABBITMQHOSTNAME","localhost")
port = int(os.environ.get("RABBITMQPORT","5672"))
queue_name = os.environ.get("RABBITMQQUEUENAME","qos_evaluator")
manager_queue_name = os.environ.get("MANAGERQUEUENAME","manager")
exchange = os.environ.get("RABBITMQQOSEXCHANGE","qos-fanout")
publisher_sleep = 0.2
pdp_queue_name = os.environ.get("PDPQUEUENAME","pdp")
outliers_threshold = int(os.environ.get("OUTLIERTHRESHOLD","3"))

max_data_points = int(os.environ.get("MAXDATAPOINTS","1000"))
exporter_url = os.environ.get("EXPORTER_URL","localhost:55682")

push_channel = None 
push_connexion = None 

class RabbitMQ():
    def __init__(self,request,username,password,host,port):
        self.connection = None
        self.channel = None
        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.request = request
        self.normal_stop = False
        self.rabbitmq_connection_state = False 

    def getConnectionState(self):
        return self.rabbitmq_connection_state
    
    def connect(self):
        credentials = pika.PlainCredentials(self.username, self.password)
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host,port=self.port,credentials=credentials))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=queue_name, durable=True)
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue=queue_name,on_message_callback=self.callback)
        self.rabbitmq_connection_state = True 
        self.request.setConsumer(self)
        print("Consumer connected to the broker...")

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
        self.rabbitmq_connection_state = False 
    def getNormalStop(self):
        return self.normal_stop
    def callback(self,channel, method, header, body):
        self.request.setData(body)
        self.channel.basic_ack(method.delivery_tag)

class QoS():
    def __init__(self,application,deployment,slo,threshold,_type,queue,prediction,under_utilization_threshold,dependencies,percentage,interval):
        self.application = application
        self.deployment = deployment
        self.slo = slo 
        self.threshold = threshold
        self.type = _type 
        self.queue = queue 
        self.prediction = prediction
        self.percentage = percentage
        self.dependencies = dependencies
        self.under_utilization_threshold = under_utilization_threshold
        self.interval = interval 
        self.target = None 
    def setTargetElement(self,target):
        self.target = target 
    def getTargetElement(self):
        return self.target 
    def getApplication(self):
        return self.application
    def getDeployment(self):
        return self.deployment
    def getSLO(self):
        return self.slo
    def getThreshold(self):
        return self.threshold
    def getType(self):
        return self.type 
    def getQueue(self):
        return self.queue 
    def getPrediction(self):
        return self.prediction
    def getUnderUtilizationThreshold(self):
        return self.under_utilization_threshold
    def getDependencies(self):
        return self.dependencies
    def getPercentage(self):
        return self.percentage
    def getInterval(self):
        return self.interval 
    

class QoSManager():
    def __init__(self):
        self.qos_list = []
        self.rabbitmq = None 
        self.config = None 
    def setConfig(self,config):
        self.config = config
    def addQoS(self,application, deployment, slo, threshold,_type,queue,prediction,under_utilization_threshold,dependencies,percentage,interval):
        if not self.qosExist(application,deployment,slo):
            qos = QoS(application,deployment,slo,threshold,_type,queue,prediction,under_utilization_threshold,dependencies,percentage,interval)
            self.qos_list.append(qos)
            print("QoS objectives added ")
            self.sendSubscriptionRequest(qos)
            return True 
        else:
            return False 
    def qosExist(self,application,deployment,slo):
        if self.getQoS(application,deployment,slo):
            return True 
        else:
            return False 
    def getSizeQos(self):
        return len(self.qos_list)
    def getQoS(self,application,deployment,slo):
        for q in self.qos_list:
            if q.getApplication() == application and q.getDeployment() == deployment and q.getSLO()== slo:
                return q
        return None 
    def addTargetElement(self,application,deployment,slo,target):
        qos = self.getQoS(application,deployment,slo)
        if qos != None:
            qos.setTargetElement(target)
            return True 
        return False 
    def stop(self):
        for qos in self.qos_list:
            self.sendStopQoS(qos)
    def setRabbitMQ(self,rabbitmq):
        self.rabbitmq = rabbitmq
    def sendStopQoS(self, qos):
        request = {}
        request['request'] = 'qos_stop'
        metrics = []
        metrics.append({'name': qos.getSLO()})
        request['metrics'] = metrics 
        self.rabbitmq.sendToClient(manager_queue_name,json.dumps(request))
        #/////////////////////////Sending message to PDP/////////////////////////////////
        message = {'application': qos.getApplication(),'deployment': qos.getDeployment(),'request':'remove_application'}
        self.rabbitmq.sendToClient(pdp_queue_name,json.dumps(message))
        self.config.remove(qos.getApplication()+"_"+qos.getDeployment()+"_"+qos.getSLO())
    def sendSubscriptionRequest(self, qos):
        request = {}
        request['request'] = 'qos_start'
        request['queue'] = queue_name
        metric = {'name': qos.getSLO(),'interval': qos.getInterval(), 'percentage': qos.getPercentage(),'application': qos.getApplication(),'deployment': qos.getDeployment(),'detail_mode': True}
        metrics = []
        metrics.append(metric)
        if qos.getTargetElement() != None:
            request['target'] = qos.getTargetElement()
        request['metrics'] = metrics 
        self.rabbitmq.sendToClient(manager_queue_name,json.dumps(request))
        if qos.getPrediction():
            self.sendRequestToPDP(qos.getApplication(),qos.getDeployment(),qos.getSLO(),qos.getDependencies(),qos.getThreshold(),qos.getType(),qos.getUnderUtilizationThreshold())
    def sendRequestToPDP(self,application,deployment,slo,dependencies,threshold,threshold_type,under_utilization_threshold):
        message = {'request': 'add_application','queue': queue_name}
        message['data'] = {'name': application,'slo':slo,'dependencies':dependencies,'deployment':deployment}
        message['violation'] = {'threshold':threshold,'threshold_type': threshold_type,'under_utilization_threshold': under_utilization_threshold}
        self.rabbitmq.sendToClient(pdp_queue_name,json.dumps(message))
        print("Request PDP sent for <<"+application+">>")
 
class QoSHandler():
    def __init__(self):
        self.applications = {}
        self.manager = QoSManager()
        self.config = None 
        self.current_config = None
        self.rabbitmq = ThreadPublisher(username,password,host,port,exchange,publisher_sleep,True)
        self.rabbitmq.connect()
        self.rabbitmq.start()
        self.consumer = None 
        self.setRabbitMQObject()
    def setPreviousConfig(self,config):
        self.current_config = config 
        for key, _json in self.current_config.iteritems():
            self.manager.addQoS(_json['application'],_json['deployment'],_json['slo'],_json['threshold'],_json['type'],_json['queue'],_json['prediction'],_json['under_utilization_threshold'],_json['dependencies'],_json['percentage'],_json['interval'])
        print("QoS config reloaded successfuly")
    def setConsumer(self,consumer):
        self.consumer = consumer
    def setRabbitMQObject(self):
        self.manager.setRabbitMQ(self.rabbitmq)
        self.config = ConfigSaver(self)
        self.manager.setConfig(self.config)
    def responde(self,message, status):
        return {'message': message,'status':status}
    def setData(self,data):
        _json = None 
        try:
            _json = json.loads(data)
        except Exception as e:
            print(e)
            return False 
        if 'request' in _json:
            if _json['request'] == "define_qos":
                self.handleUserRequest(_json)
            elif _json['request'] == "qos":
                self.handlePercentile(_json)
            elif _json['request'] == "ping":
                self.sendPongRequest()
            elif _json['request'] == "remove_qos":
                self.removeQoS(_json)
            else:
                print(_json)
        else:
            print("field <<request>> not defined")
            print(_json)
    def sendPongRequest(self):
        message = {'request': 'pong_qos','queue': queue_name}
        self.rabbitmq.sendToClient(manager_queue_name,json.dumps(message))
    def removeQoS(self,_json):
        required_fields = ['application','deployment','slo','queue']
        for field in required_fields:
            if not field in _json:
                print("Field <<"+field+">> is missing")
                return False 
        qos = self.manager.getQoS(_json['application'],_json['deployment'],_json['slo'])
        if qos != None:
            self.manager.sendStopQoS(qos)
    def handleUserRequest(self,_json):
        required_fields = ['request','application','dependencies','percentage','deployment','slo','threshold','type','queue','prediction','under_utilization_threshold','interval']
        for field in required_fields:
            if not field in _json:
                print("Field <<"+ field +">> is missing in the data")
                return False 
        msg = None 
        if self.manager.addQoS(_json['application'],_json['deployment'],_json['slo'],_json['threshold'],_json['type'],_json['queue'],_json['prediction'],_json['under_utilization_threshold'],_json['dependencies'],_json['percentage'],_json['interval']):
            if 'target' in _json:
                self.manager.addTargetElement(_json['application'],_json['deployment'],_json['slo'],_json['target'])
            msg = json.dumps(self.responde('QoS objective defined','success'))  
            self.config.setConfig(_json['application']+"_"+_json['deployment']+"_"+_json['slo'],_json) 
        else:
            msg = json.dumps(self.responde('This QoS already exist','error'))
        self.rabbitmq.sendToClient(_json['queue'],msg)
        print("Subscription request sent, application: "+ _json['application']+" slo: "+ _json['slo'])
    def getUtilizationLevel(self,quantile,qos):
        return int((quantile-qos.getUnderUtilizationThreshold())/(qos.getThreshold() - qos.getUnderUtilizationThreshold()))*100
    def getViolationLevel(self,quantile,threshold):
        if quantile > threshold:
            return int(((quantile - threshold)/threshold)*100)
        else:
            return int(((threshold - quantile)/threshold)*100)
    def stop(self):
        self.manager.stop()
        self.rabbitmq.stop()
        self.consumer.stop()
    def computeOuliers(self,data_points):
        outliers = []
        mean_1 = np.mean(data_points)
        std_1 = np.std(data_points)
        for y in data_points:
            z_score= (y - mean_1)/std_1 
            if np.abs(z_score) > outliers_threshold:
                outliers.append(y)
        return outliers
    def detectOutliers(self,_json,qos):
        data_points = []
        for point in _json['data_points']:
            data_points.append(int(point))
        outliers = self.computeOuliers(data_points)
        if len(outliers) != 0:
            message = {'request':'outliers','size_datapoints': _json['samples'],'size_outliers': len(outliers),'metric':_json['metric'],'start': _json['start'],'stop':_json['stop'],'application': qos.getApplication(),'deployment':qos.getDeployment()}
            return message 
        return None 
    def exportMetrics(self,violation,application,qos,violation_level):
        violation_level_label = None
        if violation_level == 0:
            violation_level_label = 'No violation'
        elif violation_level <= 40:
            violation_level_label = 'Mild'
        else:
            violation_level_label = 'Serious'

        export = {"metrics": {'violation': violation},"labels": {'app': application,'slo': qos.getSLO(),'level': violation_level_label}}
        try:
            requests.post(exporter_url,data=json.dumps(export),headers={'X-Requested-With': 'Python requests', 'Content-type': 'application/json'})
        except Exception as e:
            print(e)
    def detectViolation(self,_json, qos):
        quantile = float(_json['quantile'])
        message = None 
        if qos.getType() == ">":
            if quantile > qos.getThreshold():
                message = {'request':'violation','percentage':_json['percentage'],'metric':_json['metric'],'utilization': self.getUtilizationLevel(quantile,qos),'samples':_json['samples'],'level_of_violation': self.getViolationLevel(quantile,qos.getThreshold()),'type':'>','threshold': qos.getThreshold(),'evaluation': quantile,'start': _json['start'],'stop':_json['stop'],'application': qos.getApplication(),'deployment':qos.getDeployment()}
        elif qos.getType() == "<":
            if quantile < qos.getThreshold():
                message = {'request':'violation','percentage':_json['percentage'],'metric':_json['metric'],'utilization': self.getUtilizationLevel(quantile,qos),'samples':_json['samples'],'level_of_violation': self.getViolationLevel(quantile,qos.getThreshold()),'type':'<','threshold': qos.getThreshold(),'evaluation': quantile,'start': _json['start'],'stop':_json['stop'],'application': qos.getApplication(),'deployment':qos.getDeployment()}
        return message
    def checkProactiveViolation(self,value_predicted,qos):
        message = None 
        if qos.getType() == ">":
            if value_predicted > qos.getThreshold():
                message = {'request': 'proactive_violation','prediction': value_predicted}
        elif qos.getType() == "<":
            if value_predicted < qos.getThreshold():
                message = {'request': 'proactive_violation','prediction': value_predicted}
        return message

    def detectUnderUtilization(self,_json,qos):
        quantile = float(_json['quantile'])
        message = None 
        if qos.getType() == ">":
            if quantile < qos.getUnderUtilizationThreshold():
                message = {'request':'under_utilization','percentage':_json['percentage'],'metric':_json['metric'],'utilization': self.getUtilizationLevel(quantile,qos),'samples':_json['samples'],'level_of_violation': self.getViolationLevel(quantile,qos.getUnderUtilizationThreshold()),'type':'>','threshold': qos.getUnderUtilizationThreshold(),'evaluation': quantile,'start': _json['start'],'stop':_json['stop'],'application': qos.getApplication(),'deployment':qos.getDeployment()}
        elif qos.getType() == "<":
            if quantile > qos.getUnderUtilizationThreshold():
                message = {'request':'under_utilization','percentage':_json['percentage'],'metric':_json['metric'],'utilization': self.getUtilizationLevel(quantile,qos),'samples':_json['samples'],'level_of_violation': self.getViolationLevel(quantile,qos.getUnderUtilizationThreshold()),'type':'<','threshold': qos.getUnderUtilizationThreshold(),'evaluation': quantile,'start': _json['start'],'stop':_json['stop'],'application': qos.getApplication(),'deployment':qos.getDeployment()}
        return message
    def handlePercentile(self,_json):
        required_fields = ['application','metric','quantile','deployment','start','stop']
        for field in required_fields:
            if not field in _json:
                return False 
        qos = self.manager.getQoS(_json['application'],_json['deployment'],_json['metric'])
        if qos == None:
            print("QoS objectives not defined for application : "+ _json['application']+" , deployment: "+ _json['deployment'])
            return False 
        result_violation = self.detectViolation(_json, qos)
        if result_violation != None:
            self.exportMetrics(_json['quantile'],_json['application'],qos, result_violation['level_of_violation'])
            self.rabbitmq.sendToClient("",json.dumps(result_violation)) 
        else:
            self.exportMetrics(0,_json['application'],qos,0)
            
        result_under_utilization = self.detectUnderUtilization(_json,qos)
        if result_under_utilization != None:
            self.rabbitmq.sendToClient("",json.dumps(result_under_utilization))
        if 'data_points' in _json:
            result_outliers = self.detectOutliers(_json,qos)
            if result_outliers != None:
                self.rabbitmq.sendToClient("",json.dumps(result_outliers))
        
        
def main():
    request = QoSHandler()
    rabbitmq = RabbitMQ(request,username,password,host,port)
    index = 0
    while index < n_tries:
        try:
            print(str(index+1)+ " try to connect ...")
            rabbitmq.connect()
            break 
        except Exception as e:
            print(e)
            index +=1
            time.sleep(5)
        except (KeyboardInterrupt, SystemExit):
            request.stop()
            rabbitmq.stop()
            print("Normal quit")
            break 
    if rabbitmq.getConnectionState():
        print("QoS Evaluator started successfuly")
        rabbitmq.startListenning()
    print("End process")

if __name__== "__main__":
    main()
