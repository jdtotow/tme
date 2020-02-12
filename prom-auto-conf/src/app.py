import pika, json, time, os 

rabbitmq_host = os.environ.get("RABBITMQHOSTNAME","localhost")
rabbitmq_port = int(os.environ.get("RABBITMQPORT","5672"))
rabbitmq_username = os.environ.get("RABBITMQUSERNAME","richardm")
rabbitmq_password = os.environ.get("RABBITMQPASSWORD","bigdatastack")
n_tries = int(os.environ.get("NTRIES","10"))
prom_auto_conf_consumer = os.environ.get("MLCONSUMERQUEUENAME","prom_auto_conf")
targets_file_path = os.environ.get("TARGETFILEPATH","./config/targets.json")
#/////////////////////////////////////////////////////////////////////////////////

class RabbitMQ():
    def __init__(self, username,password,host,port):
        self.exchanger = None
        self.connection = None
        self.channel = None
        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.handler = None 
        self.normal_stop = False
    
    def connect(self):
        credentials = pika.PlainCredentials(self.username, self.password)
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.host,port=self.port,credentials=credentials))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=prom_auto_conf_consumer, durable=True)
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue=prom_auto_conf_consumer,on_message_callback=self.callback)
        print("Connection to broker established ...")
    def setHandler(self,handler):
        self.handler = handler 
    def startListenning(self):
        self.channel.start_consuming()
    def reconnect(self):
        self.stop()
        time.sleep(5)
        self.connect()
    def stop(self):
        self.normal_stop = True
        if self.connexion:
            self.connexion.close()
    def callback(self,channel, method, header, body):
        self.handler.setData(body)
        self.channel.basic_ack(method.delivery_tag)

class ApplicationComponent():
    def __init__(self):
        self.component_name = None 
        self.application_name = None 
        self.replicas = None 
        self.labels = {}
        self.hostname = None 
        self.port = None 
    def setComponentName(self,component_name):
        self.component_name = component_name
    def setReplicas(self,replicas):
        self.replicas = replicas
    def setApplicationName(self,application_name):
        self.application_name = application_name
    def addLabel(self,key, value):
        self.labels[key] = value 
    def setHostname(self,hostname):
        self.hostname = hostname
    def setPort(self,port):
        self.port = port 
    def getApplicationName(self):
        return self.application_name
    def getComponentName(self):
        return self.component_name
    def getHostname(self):
        return self.hostname
    def getPort(self):
        return self.port
    def getReplicas(self):
        return self.replicas
    def getLabelValue(self,key):
        if key in self.labels:
            return self.labels[key]
        else:
            return None 
    def getKey(self):
        return self.application_name+self.component_name+self.replicas
    def toConfig(self):
        result = {}
        result["labels"] = self.labels 
        result["targets"] = [self.hostname+":"+str(self.port)]
        return result 

class Handler():
    def __init__(self):
        self.config = None 
        self.dict_applications = {}
    def setData(self,data):
        _json = None 
        try:
            _json = json.loads(data)
        except Exception as e:
            print("Cannot decode json content")
            print(e)
        if 'request' in _json:
            if _json['request'] == "add_component_monitor":
                if self.addComponent(_json):
                    print("Application <<"+_json['application_name']+">>, component <<"+_json['component_name']+">> added successfuly")
            elif _json['request'] == "remove_component_monitor":
                if self.removeComponent(_json):
                    print("Application <<"+_json['application_name']+">>, component <<"+_json['component_name']+">> removed successfuly")
            else:
                print(_json)
    def stop(self):
        pass 
    def addComponent(self,_json):
        required_fields = ['application_name','component_name','replicas','hostname','port']
        for field in required_fields:
            if not field in _json:
                print("Field <<"+field+">> is missing")
                return False 
        app = ApplicationComponent()
        app.setApplicationName(_json['application_name'])
        app.setComponentName(_json['component_name'])
        app.setReplicas(_json['replicas'])
        app.setHostname(_json['hostname'])
        app.setPort(_json['port'])
        app.addLabel('application',_json['application_name'])
        app.addLabel('component',_json['component_name'])
        if 'labels' in _json:
            if _json['labels'] != {}:
                for k in _json['labels'].keys():
                    app.addLabel(k,_json['labels'][k])
        self.dict_applications[app.getKey()] = app 
        self.updateConfig()
        return True 
    def removeComponent(self,_json):
        required_fields = ['application_name','component_name','replicas']
        for field in required_fields:
            if not field in _json:
                print("Field <<"+field+">> is missing")
                return False
        key = _json['application_name']+_json['component_name']+_json['replicas']
        if key in self.dict_applications:
            del self.dict_applications[key]
            self.updateConfig()
            return True 
        else:
            return False 
    def updateConfig(self):
        result = []
        for k in self.dict_applications.keys():
            result.append(self.dict_applications[k].toConfig())
        file = open(targets_file_path,"w")
        file.write(json.dumps(result))
        file.close()
        

def main():
    handler = Handler()
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
            rabbitmq.setHandler(handler)
            connected = True
        except (KeyboardInterrupt, SystemExit):
            connected = True
            handler.stop()
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
