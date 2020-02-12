#consumer test
import pika, json, uuid, time

credentials = pika.PlainCredentials("richardm", "bigdatastack")
connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost',credentials=credentials))
print("Connection to broker established ...")
channel = connection.channel()
queue = str(uuid.uuid1())

application = 'prometheusbeat'
n_fields = 9

class Basket():
    def __init__(self):
        self.fields = None
        self.hash_baskets = {}
        self.limit = None
        self.list_baskets = []
    def setLimit(self,limit):
        self.limit  = limit
    def setFields(self,fields):
        self.fields = fields
    def getBasket(self,_time):
        return self.hash_baskets[_time]
    def ifKeyExist(self,_time):
        return _time in self.hash_baskets
    def fieldInBasket(self,field, _time):
        if _time in self.hash_baskets:
            basket = self.hash_baskets[_time]
            if field in basket:
                return True
        return False
    def backetIsCompleted(self,backet):
        result = True
        for field in self.fields:
            if not field in backet:
                result = False
        return result
    def evaluation(self):
        if len(self.hash_baskets.keys()) == 0:
            return False
        for _time in self.hash_baskets.keys():
            backet = self.hash_baskets[_time]
            if self.backetIsCompleted(backet):
                print("-------------------Completed------------------")
                print(backet)
                print("----------------------------------------------")
                self.list_baskets.append(json.dumps(backet))
                del self.hash_baskets[_time]
        if len(self.list_baskets) >= self.limit:
            self.saveInFile()
    def addElement(self,element):
        name = element['data']['name']
        _time = element['data']['time']
        _time = _time[:-8]
        if self.ifKeyExist(_time):
            basket = self.getBasket(_time)
            if not name in basket:
                basket[name] = element['data']['value']
                self.hash_baskets[_time] = basket
        else:
            basket = {'time': _time}
            basket[name] = element['data']['value']
            self.hash_baskets[_time] = basket
        self.evaluation()
    def jsonToCvs(self,entry):
        result = ""
        _json = json.loads(entry)
        for k in _json.keys():
            result+= _json[k]+","
        return result[:-1]

basket = Basket()
basket.setLimit(20)
basket.setFields(fields)

def handleData(body):
    _json = json.loads(body)
    if 'request' in _json.keys():
        if _json['request'] == "stream":
            basket.addElement(_json)


def callback(channel, method, header, body):
    handleData(body)
    channel.basic_ack(method.delivery_tag)

message = {}
message['request'] = 'subscription'
data = {}
data['name'] = queue
data['queue'] = queue
data['heartbeat_interval'] = 0

metrics = []

metric1 = {}
metric1['name'] = "*"
metric1['on_change_only'] = False
metric1['labels'] = {'application':'prometheusbeat'}

#metrics.append(metric1)
metrics.append(metric1)
#metrics.append(metric3)

data['metrics'] = metrics
message['data'] = data


channel.queue_declare(queue=queue,auto_delete=True)
channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue=queue,on_message_callback=callback)
channel.basic_publish("","manager",json.dumps(message))
channel.start_consuming()
