#consumer test
import pika, json, uuid, time

credentials = pika.PlainCredentials("richardm", "bigdatastack")
connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost',credentials=credentials))
print("Connection to broker established ...")
channel = connection.channel()
queue = str(uuid.uuid1())

def callback(channel, method, header, body):
    print(body)
    channel.basic_ack(method.delivery_tag)

message = {'request': 'define_qos','application': 'provide-recomendation-service','percentage': 60,'slo':'responseTime','type':'>','queue': queue,'deployment':'tester','threshold':200,'prediction':True,'interval':20,'under_utilization_threshold': 20,'dependencies':['prometheus','node_exporter','manager'],'target':{'application':'atos-ml','component':'recommender','host':'pushgateway','port':9091,'labels':{"provider":"atos-wordline"}}}

channel.queue_declare(queue=queue,auto_delete=True)
channel.queue_bind(queue=queue,exchange="qos-fanout")
channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue=queue,on_message_callback=callback)
channel.basic_publish("","qos_evaluator",json.dumps(message))
#message = {'request': 'define_qos','application': 'rabbitmq','slo':'rabbitmq_queue_messages','percentage': 60,'type':'>','queue': queue,'deployment':'rabbitmq','threshold':1000,'prediction':True,'under_utilization_threshold': 20,'dependencies':['node_exporter','manager','grafana']}
#channel.basic_publish("","qos_evaluator",json.dumps(message))
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
