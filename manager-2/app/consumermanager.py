import time, os, json, hashlib 

class ApplicationSubscription():
    def __init__(self, name, replicas, metric,_type, labels):
        self.name = name 
        self.replicas = replicas
        self.metric = metric
        self.type = _type 
        self.labels = labels 
    def getApplicationName(self):
        return self.name 
    def getReplicasName(self):
        return self.replicas
    def getMetricName(self):
        return self.metric 
    def getType(self):
        return self.type 
    def getLabels(self):
        return self.labels 
    def isValid(self):
        if self.type == "metric":
            if self.metric != "":
                return True 
        elif self.type == "application":
            if self.name != None and self.name !="":
                return True 
        else:
            return False 
        return False 
    def labelsMatch(self,labels):
        for key in self.labels.keys():
            if key in labels:
                if labels[key] != self.labels[key]:
                    return False
        return True
    def match(self,metric,application,replicas,labels):
        if self.type == "metric":
            if self.labels == {} or self.labels == None:
                if self.metric == metric:
                    return True 
                else:
                    return False 
            else:
                return self.labelsMatch(labels)
        elif self.type == "application":
            if self.replicas == "":
                if self.name == application:
                    return True 
                else:
                    return False 
            else:
                if self.name == application and self.replicas == replicas:
                    return True 
                else:
                    return False 


class Consumer():
    def __init__(self):
        self.consumer_name = None 
        self.queue_name = None
        self.applications = {} 
    def getConsumerName(self):
        return self.consumer_name
    def getQueueName(self):
        return self.queue_name
    def setConsumerName(self, name):
        self.consumer_name = name 
    def setQueueName(self,queue):
        self.queue_name = queue
    def addApplication(self,name,replicas, metric, _type,labels):
        if not name in self.applications:
            app = ApplicationSubscription(name,replicas,metric,_type,labels)
            if app.isValid():
                self.applications[name+replicas+metric] = app 
                return True
        return False 
    def getApplicationSubscription(self, name, replicas, metric):
        if name+replicas+metric in self.applications:
            return self.applications[name+replicas+metric]
        return None
    def getApplicationSubscriptionByMetricName(self,metric):
        result = []
        for k in self.applications.keys():
            if self.applications[k].getMetricName() == metric:
                result.append(self.applications[k])
        return result 
    def getApplicationSubscriptionByApplicationName(self,application_name):
        result = []
        for k in self.applications.keys():
            if self.applications[k].getApplicationName() == application_name:
                result.append(self.applications[k])
        return result
    def getApplications(self):
        result = []
        for k in self.applications:
            result.append(self.applications[k])
        return result 

class ConsumerManager():
    def __init__(self):
        self.consumers = {}
        self.cache = {}
        self.new_subscription_not_cached = False 
    def addConsumer(self, consumer_name, queue_name, applications):
        consumer = Consumer()
        consumer.setConsumerName(consumer_name)
        consumer.setQueueName(queue_name)
        for application in applications:
            required_field = ["name","replicas","metric","type","labels"]
            application_format_valid = True 
            for field in required_field:
                if not field in application:
                    print("required field misses <<"+field+">>")
                    application_format_valid = False 
            if application_format_valid:
                consumer.addApplication(application["name"],application["replicas"],application["metric"],application["type"],application["labels"])
                print("Application subscription added <<"+application["name"]+">>")
                self.new_subscription_not_cached = True 
        if consumer.getApplications() != []:
            self.consumers[consumer_name] = consumer
            return True 
        return False 
    def getApplicationSubscriptions(self):
        result = []
        for c in self.consumers:
            consumer = self.consumers[c]
            result.extend(consumer.getApplications())
        return result 
    def removeConsumer(self,name):
        if name in self.consumers:
            del self.consumers[name]
            return True 
        return False 
    
    def matchSubscriptions(self,metric,application,replicas,labels):
        k = metric+application+replicas+json.dumps(labels)
        subs = [] 
        if k in self.cache:
            subs = self.cache[k] 
        if subs == [] or self.new_subscription_not_cached:
            all_app_subs = self.getApplicationSubscriptions()
            for app in all_app_subs:
                if app.match(metric,application,replicas,labels):
                    subs.append(app)
            self.cache[k] = subs
            self.new_subscription_not_cached = False
        return subs   

