import requests, time, random, json, config

outapi_url = config.outapi['url']

_requests = ["http://localhost:55670/v2/api/metrics?name=memory","http://localhost:55670/v2/api/metrics?name=memory&limit=5&labels=job,outapi","http://localhost:55670/v2/api/metrics?name=go_memstats_alloc_bytes&limit=10","http://localhost:55670/v2/api/metrics?name=throughput&labels=job,prometheus&limit=2","http://localhost:55670/v2/api/metrics?name=responseTime&labels=job,outapi,instance,outapi&limit=2"]
#result = requests.get("http://localhost:55670/v2/api/metrics?name=go_memstats_alloc_bytes")
start_time = time.time()
index = 0
while True:
    if index == 1000000:
        break
    t_sleep = 2
    if time.time() - start_time >= 60*5:
        t_sleep +=1
        start_time = time.time()
    for req in _requests:
        resp = requests.get(req)
        index +=1
        print("index : "+ str(index))
    time.sleep(t_sleep)
