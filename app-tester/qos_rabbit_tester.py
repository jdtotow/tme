#consumer test
import pika, json, uuid

credentials = pika.PlainCredentials("richardm", "bigdatastack")
connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost',credentials=credentials))
print("Connection to broker established ...")
channel = connection.channel()
queue = str(uuid.uuid1())


def callback(channel, method, header, body):
    print(body)
    channel.basic_ack(method.delivery_tag)

queue = 'qos-evaluator-queue'
message = {}
message['request'] = 'qos'
message['queue'] = 'qos-evaluator-queue'
metrics = []
metric1 = {'name': 'scrape_duration_seconds', 'interval': 20, 'percentage': 50, 'application':'tester'}
metric2 = {'name': 'datapoints_prometheus', 'interval': 20, 'percentage': 50, 'application':'tester'}
metric3 = {'name': 'request_rate', 'interval': 20, 'percentage': 50, 'application':'tester'}
metrics.append(metric1)
metrics.append(metric2)
metrics.append(metric3)
message['metrics'] = metrics

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
