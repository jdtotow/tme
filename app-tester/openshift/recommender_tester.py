import multiprocessing.pool, requests, time, random, os 

base_url = os.environ.get("RECOMMENDER_HOSTNAME","localhost")
recommender_url = "http://"+base_url+":7070/recommendations?customerId=1&limit=3"

def startWorkers(max_thread_sender, func, _list):
    pool = multiprocessing.pool.ThreadPool(processes=max_thread_sender)
    pool.map(func,_list,chunksize=50)
    pool.close()

def sender(url):
    try:
        requests.get(url)
    except Exception as e:
        print("Request not sent")
        time.sleep(20)


def prepareList(_size):
    result = []
    for i in range(_size):
        result.append(recommender_url)
    return result

_sleep = 0.01
_workers = 60

up_period = 10
down_period = 5

def high():
    _size = 30000
    _start = time.time()
    while True:
        _list = prepareList(_size)
        startWorkers(_workers, sender, _list)
        #print(str(_size)+" request sent, sleep ...")
        #time.sleep(_sleep)
        if time.time() - _start > up_period*60:
            break

def down():
    _size = 3000
    _start = time.time()
    while True:
        _list = prepareList(_size)
        startWorkers(_workers, sender, _list)
        #print(str(_size)+" request sent, sleep ...")
        time.sleep(_sleep)
        if time.time() - _start > down_period*60:
            break

def demo():
    while True:
        _list = prepareList(30000)
        startWorkers(300, sender, _list)
        #print(str(_size)+" request sent, sleep ...")
        #time.sleep(_sleep)

def main():
    while True:
        down()
        high()
        time.sleep(_sleep)

#demo()
main()
