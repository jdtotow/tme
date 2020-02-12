import time

class Manager():
    def __init__(self, broker_host, port, username, password, queue_name):
        self.broker_host = broker_host
        self.port = port 
        self.username = username 
        self.password = password
        self.queue_name = queue_name
        self.queuing_system = "rabbitmq"

    def setQueuingManager(self, queuing_system):
        self.queuing_system = queuing_system
    def 
def main():
    pass 
if __name__=="__main__":
    main()