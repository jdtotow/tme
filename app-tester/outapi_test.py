import json, time, requests, random

headers = {'X-Requested-With': 'Python requests', 'Content-type': 'text/json'}
url_outapi = "http://localhost:55670/v2/api/metrics"
url_exporter = "http://localhost:55677"

value_exported = None
label_exported = None
file = open("latency_320.csv","w+")
file.write("monitoring_delay,total_delay\n")
def export(value, index_label):
    measurement = {'metrics':{'number_latency': random.randint(100,1000),'indexer_latency': value},'labels':{'time': str(time.time()),'application':'latency','label_index': index_label}}
    response = requests.post(url_exporter,data=json.dumps(measurement),headers=headers)
    #print(response.text)

def compare(data):
    global file
    results = data['result']
    for beat in results:
        if beat['_source']['labels']['label_index'] == label_exported:
            #print(beat)
            time_exposed = float(beat['_source']['time'])
            now = time.time()
            total_delay = now - float(beat['_source']['labels']['time'])
            monitoring_delay = now - time_exposed
            print("Latency :"+ str(now - time_exposed))
            file.write(str(monitoring_delay)+","+str(total_delay)+"\n")
            return True
    return False

index = 0
while index < 100:
    value_exported = random.randint(1,1000)
    label_exported = 'label_latency_'+ str(value_exported)
    print("Value exported: "+ str(value_exported))
    print("Label exporter: "+ label_exported)
    export(value_exported,label_exported)
    while True:
        data = requests.get(url_outapi+"?name=indexer_latency").json()
        if compare(data):
            break
    index +=1
file.close()
print("End process")
