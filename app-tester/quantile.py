import random, time 

_red_color = '\033[93m'
_green_color = '\033[92m'
_end_color = '\033[0m'
def computeQuantile(percentage, _list):
    index = None 
    index = int((percentage/100.0)*(len(_list)+1))
    if index == len(_list):
        index = len(_list) - 1
    return _list[index]

def qos(quantile, threshold):
    if quantile > threshold:
        print(_red_color+ "Contract violated, Quantile ="+str(quantile)+", threshold="+str(threshold)+ _end_color)
        return False
    else:
        print(_green_color+ "OK, quantile="+ str(quantile)+ _end_color)
        return True 

def generateArray(size):
    result = []
    for i in range(size):
        result.append(random.randint(60,150))
    return result 

def main():
    while True:
        _list = generateArray(20)
        _list.sort()
        percentage = 60
        threshold = 120
        quantile = computeQuantile(percentage,_list)
        if not qos(quantile,threshold):
            print(_list)
        time.sleep(1)

if __name__=="__main__":
    main()