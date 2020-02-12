import requests, time, random, json
from concurrent.futures import ThreadPoolExecutor

number_metrics = 500
interval_sleep = 5
url_exporter = "http://localhost:55677"
headers = {'X-Requested-With': 'Python requests', 'Content-type': 'application/json'}
url = "http://recommender-eroski.apps.openshift.bigdatastack.com/recommendations?customerId=1"


start_time = time.time()
def makeMetric(index):
    return json.dumps({'metrics':{'big_metric_value_'+index: random.randint(50,100)},'labels':{'application':'big_metric'}})

def get_url(index):
    return requests.post(url_exporter,data=makeMetric(index),headers=headers)

def sendRequest():
    with ThreadPoolExecutor(max_workers=50) as pool:
        list_of_urls = []
        for i in range(number_metrics):
            list_of_urls.append(str(i))
        pool.map(get_url,list_of_urls)
        #print(str(number_of_request)+", requests sent")

index = 0
while index < number_metrics:
    get_url(str(index))
    index +=1
