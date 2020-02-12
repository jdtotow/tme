import multiprocessing.pool, requests, time, random

recommender_url = "http://localhost:7070/recommendations?customerId=1&limit=3"

def startWorkers(max_thread_sender, func, _list):
    pool = multiprocessing.pool.ThreadPool(processes=max_thread_sender)
    pool.map(func,_list,chunksize=1)
    pool.close()

def sender(url):
    requests.get(url)


def prepareList(_size):
    result = []
    for i in range(_size):
        result.append(recommender_url)
    return result

#////////////////////////////////////////////////
_size = 2
_sleep = 1
_workers = 10

index = 0
while index < 10:
    _list = prepareList(_size)
    startWorkers(_workers, sender, _list)
    time.sleep(_sleep)
    index +=1

time.sleep(10)
#////////////////////////////////////////////////
_size = 400
_sleep = 0.1
_workers = 100

_list = prepareList(_size)
startWorkers(_workers, sender, _list)
#/////////////////////////////////////////////////
time.sleep(10)
_size = 2
_sleep = 1
_workers = 10

index = 0
while index < 10:
    _list = prepareList(_size)
    startWorkers(_workers, sender, _list)
    time.sleep(_sleep)
    index +=1