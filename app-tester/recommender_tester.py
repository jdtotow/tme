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

_sleep = 0.01
_workers = 50

up_period = 10
down_period = 30

def high():
    _size = 100
    _start = time.time()
    while True:
        _list = prepareList(_size)
        startWorkers(_workers, sender, _list)
        print(str(_size)+" request sent, sleep ...")
        time.sleep(_sleep)
        if time.time() - _start > up_period*60:
            break

def down():
    _size = 30
    _start = time.time()
    while True:
        _list = prepareList(_size)
        startWorkers(_workers, sender, _list)
        print(str(_size)+" request sent, sleep ...")
        time.sleep(_sleep)
        if time.time() - _start > down_period*60:
            break

def main():
    while True:
        down()
        high()
        time.sleep(_sleep)

main()
