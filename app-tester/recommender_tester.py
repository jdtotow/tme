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
"""
No violation
_size = 50
_sleep = 0.1
_workers = 20
Mild violation
_size = 500
_sleep = 0.1
_workers = 200
"""

_size = 500
_sleep = 0.1
_workers = 100

while True:
    _list = prepareList(_size)
    startWorkers(_workers, sender, _list)
    print(str(_size)+" request sent, sleep ...")
    time.sleep(_sleep)
