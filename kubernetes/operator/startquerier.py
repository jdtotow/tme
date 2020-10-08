import json, time, kopf, kubernetes, logging 
from threading import Thread

log = logging.getLogger('werkzeug')
log.setLevel(logging.INFO)

class RestartQuerier(Thread):
    def __init__(self, kopf, querier_obj, querier_body, register, delay, namespace,main_thread):
        self.kopf = kopf 
        self.querier_obj = querier_obj
        self.querier_body = querier_body
        self.delay = delay 
        self.register = register 
        self.api = kubernetes.client.CoreV1Api()
        self.namespace = namespace
        self.main_thread = main_thread
        super(RestartQuerier, self).__init__()
    def run(self):
        _start = time.time()
        log.info("Querier will be recreated in {0} sec".format(self.delay))
        while time.time() - _start < self.delay:
            time.sleep(1)

        self.kopf.adopt(self.querier_obj, owner=self.querier_body)
        obj = self.api.create_namespaced_pod(self.namespace, self.querier_obj)
        self.register.updateKubeObject("pod","querier",obj)
        log.info("Querier recreated")
        time.sleep(10) #delay the recreation mechanism
        self.main_thread.unclockPodListCollection() #unclock the recreation mechanism 
        

    