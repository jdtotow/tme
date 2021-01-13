from threading import Thread
import sys, os, time,json, requests, multiprocessing.pool
import random, requests  

max_thread_sender = int(os.environ.get("NTHREADS","10"))
n_request = int(os.environ.get("NREQUEST","2"))
base_url = os.environ.get("FEEDBACKS_HOSTNAME","grss-srv-feedbackcollector-0.realization.svc")
feedback_url = base_url
feedback_types = ['PRODUCT_VISUALIZED','PRODUCT_ADDED_TO_BASKET','PRODUCT_RECOMMENDATION_REMOVED','PRODUCT_REMOVED_FROM_BASKET']
post_data = {"customerId":"718","productId":"542","feedbackType":"PRODUCT_REMOVED_FROM_BASKET"}
sleep_time = int(os.environ.get("SLEEP_TIME","5"))
logstash = os.environ.get("LOGSTASH","http://logstash.tme.svc:8081")

def exportMetrics(name, value, response_time_type):
    message = {'metrics': {}, 'labels': {'application': 'apptester'}}
    message['metrics'][name] = value 
    message['labels']['type'] = response_time_type
    try:
        requests.post(logstash,data=json.dumps(message), headers={'Content-Type': 'application/json'})
    except:
        pass 

def makeDataToSend():
    #customer_id = '{0}'.format(random.randint(0,542))
    #product_id = '{0}'.format(random.randint(0,720))
    post_data = []
    for _type in feedback_types:
        post_data.append({"customerId":"718","productId":"542","feedbackType":_type})
    return post_data

def startWorkers(func, _list):
    pool = multiprocessing.pool.ThreadPool(processes=max_thread_sender)
    results = pool.map(func,_list,chunksize=1)
    if len(results) > 0:
        max_response_time = max(results)
        avg_response_time = sum(results)/len(results)
        exportMetrics('responseTime', max_response_time, 'max')
        exportMetrics('responseTime', avg_response_time,'average')
    pool.close()
    pool.join()

def requestFeedbacks(_data):
    try:
        _start = time.time()
        student = requests.post(url=feedback_url, data=json.dumps(_data),headers={'Content-Type':'application/json'})
        return time.time() - _start
    except Exception as e:
        return 0
        print(e)

def main():
    _list = []
    for i in range(n_request):
        _list.extend(makeDataToSend())
    print("List data created, size = {0}".format(n_request))
    while True:
        _start = time.time()
        startWorkers(requestFeedbacks,_list)
        duration = time.time() - _start
        print("Response time : {0}".format(duration))
        time.sleep(sleep_time)

if __name__ == "__main__":
    main()