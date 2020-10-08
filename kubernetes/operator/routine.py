import json, os, time, logging 
from threading import Thread

_routine_interval = int(os.environ.get("ROUTINE_INTERVAL","10"))

log = logging.getLogger('werkzeug')
log.setLevel(logging.INFO)

class Routine(Thread):
    def __init__(self, api, handler):
        self.api = api 
        self.handler = handler
        super(Routine, self).__init__()
    def collectMissingPods(self,_list_pods, _list_tme):
        #print(_list_pods)
        #print(_list_tme)
        result = []
        for tme in _list_tme:
            tme_name = tme.getPodName()
            if not tme_name in _list_pods:
                if not tme_name in result:
                    result.append(tme_name)
        return result
    def run(self):
        log.info("Watch routine started")
        while True:
            pods_list = None 
            objects_list = None 
            error = False
            try:
                pods_list = self.handler.getPodsList()
                if pods_list == None: #method lock by the main thread
                    continue
                objects_list = self.handler.getAllObjects()
            except Exception as e:
                log.info(e)
                error = True
            if error:
                continue
            missing_pods = self.collectMissingPods(pods_list,objects_list)
            if missing_pods != []:
                self.handler.createMissingPods(missing_pods)
            time.sleep(_routine_interval)
