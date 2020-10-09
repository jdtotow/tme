from urllib.parse import urlparse
from threading import Thread
import sys, os, time 
from http.client import HTTPConnection
from queue import Queue

concurrent = 200
base_url = os.environ.get("RECOMMENDER_HOSTNAME","localhost")
recommender_url = "http://"+base_url+":7070/recommendations?customerId=1&limit=3"

def sendRequest():
    while True:
        url = q.get()
        status, url = getStatus(url)
        printResult(status, url)
        q.task_done()

def getStatus(ourl):
    try:
        url = urlparse(ourl)
        conn = HTTPConnection(url.netloc)   
        conn.request("HEAD", url.path)
        res = conn.getresponse()
        return res.status, ourl
    except:
        return "error", ourl

def printResult(status, url):
    print(status, url)

q = Queue(concurrent * 2)
for i in range(concurrent):
    t = Thread(target=sendRequest)
    t.daemon = True
    t.start()

total_number_request = 200
while True:
    try:
        for i in range(total_number_request):
            q.put(recommender_url)
        q.join()
    except KeyboardInterrupt:
        sys.exit(1)
        time.sleep(2)