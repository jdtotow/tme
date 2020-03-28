import time, os, json 
from consumermanager import ConsumerManager

class Manager():
    def __init__(self, consumer_manager, publisher_manager):
        self.consumer_manager = consumer_manager
        self.publisher_manager = publisher_manager
    def start(self):
        pass 
    def addConsumer(self,consumer_name,consumer_queue, applications):
        self.consumer_manager.addConsumer(consumer_name,consumer_queue,applications)
    def findSubs(self,metric,application,replicas,labels):
        return self.consumer_manager.matchSubscriptions(metric,application,replicas,labels)
        
def main():
    consumer_manager = ConsumerManager()
    manager = Manager(consumer_manager,None)
    manager.start() 
    applications = [{'name':'app1','metric':'memory','replicas':'node-1','type':'application','labels':None},{'name':'app2','metric':'memory','replicas':'node-1','type':'metric','labels':None}]
    manager.addConsumer('consumer-1','queue',applications)
    subs = manager.findSubs('memory','app1','node-1',{})
    print(subs)
if __name__ == "__main__":
    main()