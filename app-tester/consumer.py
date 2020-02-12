#consumer test
import pika, json, uuid, config, random, requests, time, base64, psutil, os

user = config.rabbitmq['user']
password = config.rabbitmq['password']
host = config.rabbitmq['host']
port = int(config.rabbitmq['port'])
manager_queue = config.rabbitmq['queue']
heartbeat_interval = int(config.rabbitmq['heartbeat_interval'])
outapi_url = config.outapi['url']
exporter_url = config.exporter['url']
name = config.tester['name']


list_metrics = ["beats_rate","memory","scrape_duration_seconds","responseTime","process_max_fds","process_open_fds","prometheus_sd_kubernetes_cache_list_items_count","go_memstats_alloc_bytes"]
def main():
    while True:
        iteration = random.randint(300,400)
        counter = 0
        start_time = time.time()
        while counter < iteration:
            index = int((random.random()*100)%len(list_metrics))
            headers = {'X-Requested-With': 'Python requests', 'Content-type': 'text/xml'}
            try:
                resp = requests.get(outapi_url+"?name="+list_metrics[index],headers=headers)
                print(resp.text)
            except Exception as e:
                print(e)
            counter +=1
        interval = time.time() - start_time
        request_rate = iteration/interval
        process = psutil.Process(os.getpid())
        memory_usage = process.memory_info().rss
        data_to_exporter = {'metrics':{'throughput': request_rate,'memory_usage':memory_usage,'latency':interval*1000},'labels':{'engine':'tpme','component':'tester'}}
        try:
            requests.post(exporter_url,data=json.dumps(data_to_exporter),headers=headers)
        except Exception as e:
            print(e)
        time.sleep(1)


main()

"""
connection_max_trie = 10
connection_counter = 0
connection_state = False
channel = None

while not connection_state:
    try:
        credentials = pika.PlainCredentials(user,password)
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=host,port=port,credentials=credentials))
        channel = connection.channel()
        print("Connection to broker established")
        connection_state = True
    except:
        connection_counter +=1
        if connection_counter == connection_max_trie:
            break
        time.sleep(10)


queue = str(uuid.uuid1())

def sendRequests():
    iteration = random.randint(100,200)
    counter = 0
    index = int((random.random()*100)%len(list_metrics))
    while counter < iteration:
        headers = {'X-Requested-With': 'Python requests', 'Content-type': 'text/xml'}
        try:
            resp = requests.get(outapi_url+"?name="+list_metrics[index],headers=headers)
            print(resp.text)
        except Exception as e:
            print(e)
        counter +=1
    sendHeartbeat()
    return iteration

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
    data['name'] = name
    data['queue'] = queue
    message['data'] = data
    channel.basic_publish("",manager_queue,json.dumps(message))

def callback(channel, method, header, body):
    print(body)
    _data = json.loads(body)
    if type(_data) != type({}):
        channel.basic_ack(method.delivery_tag)
        return False
    if 'request' in _data:
        if _data['request'] == 'ping':
            pongMethod()
    _start = time.time()
    headers = {'X-Requested-With': 'Python requests', 'Content-type': 'text/xml'}
    process = psutil.Process(os.getpid())
    memory_usage = process.memory_info().rss
    channel.basic_ack(method.delivery_tag)
    iteration = sendRequests()
    _elapsed_time = time.time() - _start #s
    throughput = 0
    if _elapsed_time > 0:
        throughput = iteration/_elapsed_time
    data_to_exporter = {'metrics':{'elaspsed_time': _elapsed_time,'memory_usage': memory_usage,'throughput': throughput},'labels':{'engine':'tpme','component':'tester'}}
    try:
        requests.post(exporter_url,data=json.dumps(data_to_exporter),headers=headers)
    except Exception as e:
        print(e)

message = {}
message['request'] = 'subscription'
data = {}
data['name'] = name
data['queue'] = queue
data['heartbeat_interval'] = heartbeat_interval

metrics = []

for metric_name in list_metrics:
    metric = {'name': metric_name,'on_change_only': False}
    metrics.append(metric)

data['metrics'] = metrics
message['data'] = data

if connection_state:
    channel.queue_declare(queue=queue,auto_delete=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=queue,on_message_callback=callback)
    channel.basic_publish("",manager_queue,json.dumps(message))
    print("Start consuming")
    channel.start_consuming()
"""
