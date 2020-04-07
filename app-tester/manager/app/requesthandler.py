import time, json, os 


class RequestHandler():
    def __init__(self):
        self.manager = None
        self.queueing_manager = None
        self.previous_config = None
    def handle(self,_body):
        data = None
        if type(_body) == type({}):
            data = _body
        else:
            try:
                data = json.loads(_body)
            except Exception as e:
                print(e)
                return None
        if not 'request' in data:
            return False 
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
                    _list_data_to_save = []
                    for metric in metrics:
                        _job_name = "all"
                        if 'labels' in metric:
                            if 'application' in metric['labels']:
                                _job_name = metric['labels']['application']
                        _list_data_to_save.append({'index':hashlib.md5(metric['name']+_job_name).hexdigest(),'type':'stream','last': int(time.time()),'name': name,'n_access':0,'from':int(time.time()),'job': _job_name})
                    saveMetrics(_list_data_to_save)
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