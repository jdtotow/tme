#consumer test
import pika, json, uuid, time
from datetime import datetime

credentials = pika.PlainCredentials("richardm", "bigdatastack")
connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost',credentials=credentials))
print("Connection to broker established ...")
channel = connection.channel()
queue = str(uuid.uuid1())

def addMetric():
    message = {}
    message['request'] = 'add_metric'
    data['name'] = 'monitoring-1'
    data['metric'] = 'node_netstat_Tcp_OutSegs'
    message['data'] = data
    channel.basic_publish("","manager",json.dumps(message))

def mySubscription():
    message = {}
    message['request'] = 'my_subscription'
    data['name'] = 'monitoring'
    message['data'] = data
    channel.basic_publish("","manager",json.dumps(message))

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
    channel.basic_ack(method.delivery_tag)
    """
    _message = None
    if body[0] == "\"":
        _message = str(body)[1:len(body)-1]
    else:
        _message = body
    _message = _message.replace("\\","")
    print(_message)
    _data = json.loads(_message)
    if type(_data) != type({}):
        channel.basic_ack(method.delivery_tag)
        return False
    if 'request' in _data:
        if _data['request'] == 'ping':
            pongMethod()
    print(_data)
    if _data['request'] == 'stream':
        _time = _data['data']['time']
        now = datetime.now()
        date_time = now.strftime("%m/%d/%Y, %H:%M:%S")
        print("Metric collected at "+ str(_time)+" , exposed at ->"+ date_time)
    """

message = {}
message['request'] = 'subscription'
data = {}
data['name'] = 'monitoring'
data['queue'] = queue
data['heartbeat_interval'] = 40000

metrics = []

metric1 = {}
metric1['name'] = "*"
metric1['on_change_only'] = False
metric1['labels'] = {'application':'prometheusbeat'}

metric2 = {}
metric2['name'] = "datapoints_prometheus"
metric2['on_change_only'] = False
metric2['labels'] = {'application':'prometheusbeat'}

metric3 = {}
metric3['name'] = "*"
metric3['on_change_only'] = False
metric3['labels'] = {'application':'prometheus'}

metrics.append(metric1)
metrics.append(metric2)
metrics.append(metric3)

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
