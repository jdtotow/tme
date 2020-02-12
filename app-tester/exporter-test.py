import time, json, random, requests

url_exporter = "http://localhost:55671"
n_send_metrics = 1
n_get_metrics = 10

def generateMetric():
    metrics = {'index': random.randint(1,10),'time': time.time()}
    labels = {'application': str(random.randint(1,5))}
    return {'metrics': metrics,'labels': labels}

def sendToTheExporter():
    data = generateMetric()
    response = requests.post(url_exporter,data=json.dumps(data),headers={'X-Requested-With': 'Python requests', 'Content-type': 'application/json'})
    print(data)
    print(response.text)

def getMetrics():
    response = requests.get(url_exporter+"/metrics",headers={'X-Requested-With': 'Python requests', 'Content-type': 'application/json'})
    print(response.text)

def main():
    while True:
        for i in range(n_send_metrics):
            sendToTheExporter()
        for i in range(n_get_metrics):
            getMetrics()
        time.sleep(2)


if __name__=="__main__":
    main()
