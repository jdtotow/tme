#consumer test
import pika, json, uuid

credentials = pika.PlainCredentials("richardm", "bigdatastack")
connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost',credentials=credentials))
print("Connection to broker established ...")
channel = connection.channel()
queue = str(uuid.uuid1())

def pongMethod():
    message = {}
    message['request'] = 'pong'
    data = {}
    data['queue'] = queue
    message['data'] = data
    channel.basic_publish("","manager",json.dumps(message))

def sendHeartbeat():
    message = {}
    message['request'] = 'heartbeat'
    data['name'] = 'monitoring'
    data['queue'] = queue
    message['data'] = data
    channel.basic_publish("","manager",json.dumps(message))

def callback(channel, method, header, body):
    print(body)
    _data = json.loads(body)
    if type(_data) != type({}):
        channel.basic_ack(method.delivery_tag)
        return False
    if 'request' in _data:
        if _data['request'] == 'ping':
            pongMethod()
    channel.basic_ack(method.delivery_tag)

message = {}
message['request'] = 'subscription'
data = {}
data['name'] = 'monitoring-2'
data['queue'] = queue
data['heartbeat_interval'] = 40000

metrics = []

metric1 = {}
metric1['name'] = "datapoints_prometheus"
metric1['on_change_only'] = False

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

########Request format###################################
###########Subscription##################
"""
{
    "request":"subscription",
    "data":{
        "name": "consumer_name",
        "queue": "queue_name"
        "metrics": ['name1','name2','name3']
    }
}
"""
##########set_metrics####################
#declaring subscribed metrics
