import time, os, json 
from consumermanager import ConsumerManager
from rabbitmq import RabbitMQ

rabbitmq_username = os.environ.get("RABBITMQ_USERNAME","richardm")
rabbitmq_password = os.environ.get("RABBITMQ_PASSWORD","bigdatastack")
rabbitmq_host = os.environ.get("RABBITMQ_HOSTNAME","localhost")
rabbitmq_port = int(os.environ.get("RABBITMQ_PORT","5672"))
rabbitmq_exchanger = os.environ.get("RABBITMQ_EXCHANGER","")
manager_queue_name = os.environ.get("MANAGER_QUEUE_NAME","manager")

class MainManager():
    def __init__(self, consumer_manager, publisher_manager):
        self.consumer_manager = consumer_manager
        self.publisher_manager = publisher_manager
    def start(self):
        while True:
            print("Manager is running")
            time.sleep(10)

    def addConsumer(self,consumer_name,consumer_queue, applications):
        self.consumer_manager.addConsumer(consumer_name,consumer_queue,applications)
    def findSubs(self,metric,application,replicas,labels):
        return self.consumer_manager.matchSubscriptions(metric,application,replicas,labels)
    def setData(self,data):
        self.consumer_manager.setRabbitMQData(data)
        
def main():
    consumer_manager = ConsumerManager()
    manager = MainManager(consumer_manager,None)
    rabbitmq = RabbitMQ(rabbitmq_exchanger,manager_queue_name,rabbitmq_username,rabbitmq_password,rabbitmq_host,rabbitmq_port)
    rabbitmq.setManager(manager)
    rabbitmq.start()
    manager.start() 

    #applications = [{'name':'app1','metric':'memory','replicas':'node-1','type':'application','labels':None},{'name':'app2','metric':'memory','replicas':'node-1','type':'application','labels':None}]
    #manager.addConsumer('consumer-1','queue',applications)
    #subs = manager.findSubs('memory','app1','node-1',{})
    #print(subs)
if __name__ == "__main__":
    main()