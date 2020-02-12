import random 

def computeQuantile( _list, percentage):
    _size = len(_list)
    if _size == 0:
        return None
    _list.sort()
    position = int((percentage/100.0)*(_size+1))
    if position == _size:
        position -=1
    return _list[position]

_list = [int(random.random()*100) for i in range(30)]
percentage = 50
print(_list)
print(computeQuantile(_list,percentage))