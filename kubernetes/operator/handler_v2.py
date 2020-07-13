import kopf, kubernetes, yaml, tme_config, time, logging, os 
from routine import Routine 

configs = tme_config.get_configs()
dict_properties = {}
list_config_field = ['image','ports','env','mounts','volumes','args','initContainers','command','resources','liveness','readyness']

_deploy_type = os.environ.get("DEPLOYMENT_TYPE","COMPONENT")
_namespace = os.environ.get("NAMESPACE","default")
_service_type = os.environ.get("SERVICETYPE","ClusterIP")
_platform = os.environ.get("PLATFORM","kubernetes")
_delete_lock = False 

log = logging.getLogger('werkzeug')
log.setLevel(logging.INFO)

class KubeObject():
    def __init__(self, name, creation, _object, _type, pod_name,body):
        self.name = name 
        self.creation = creation
        self._object = _object 
        self._type = _type 
        self.pod_name = pod_name
        self.body = body 
    def getBody(self):
        return self.body 
    def getType(self):
        return self._type 
    def getPodName(self):
        return self.pod_name
    def getName(self):
        return self.name 
    def getObject(self):
        return self._object
    def getCreationTime(self):
        return self.creation

class Register():
    def __init__(self):
        self.collector = {}
    def createKubeObject(self,name,_object,_type, pod_name, body):
        kube_object = KubeObject(name,time.time(),_object,_type,pod_name,body)
        self.collector[_type+"-"+name] = kube_object
        log.info("Object "+ name+" added to register")
    def getKubeObject(self,name,_type):
        key = _type+"-"+name 
        if key in self.collector:
            return self.collector[key]
        return None 
    def checkObjectName(self,name):
        for k in self.collector.keys():
            if name == self.collector[k].getName():
                return True 
        return False 
    def removeKubeObject(self,name,_type):
        key = _type+"-"+name 
        if key in self.collector:
            del self.collector[key]
            log.info("Object "+name+" removed from the register")
            return True
        return False 
    def loadKubeObject(self,name,creation,_object,_type):
        kube_object = KubeObject(name,creation,_object,_type)
        self.collector[_type+"-"+name] = kube_object
    def getAllPodsObject(self):
        result = []
        for key in self.collector.keys():
            if self.collector[key].getType() == "pod":
                result.append(self.collector[key])
        return result
    def getAllObjects(self):
        result = []
        for key in self.collector.keys():
            result.append(self.collector[key])
        return result 
    def getObjectPerTMEName(self, tme_name):
        for key in self.collector.keys():
            kube_object = self.collector[key]
            if kube_object.getType() != "pod":
                continue
            if kube_object.getName() == tme_name or kube_object.getPodName() == tme_name:
                return (kube_object.getObject(),kube_object.getBody())
        return (None,None) 

class Operator():
    def __init__(self, register):
        self.register = register 
        self.planner = tme_config.loadPlanner()
        self.configs = tme_config.get_configs()
        self.api = kubernetes.client.CoreV1Api() #to optimize
        self.namespace = _namespace
        self.routine = Routine(self.api, self)
        self.list_pods = []
        self.routine.start()
    def prepareContainer(self,name,_type):
        #name, image,_ports,_args, _env, _mounts, _volumes
        dict_properties = self.loadComponentConfig(name)
        #adding the image
        container = { 'image': dict_properties['image'], 'name': name}
        #adding environment variables
        _envs = self.prepareEnvironmentVariable(dict_properties['env'])
        if _envs != None:
            container['env'] = _envs
        #resource constraint 
        container['resources'] = self.prepareResourceConstraint(dict_properties['resources'])
        #adding containers port 
        _ports = self.prepareContainerPorts(dict_properties['ports'])
        if _ports != None:
            container['ports'] = _ports 
        #adding volumes
        _mounts = dict_properties['mounts']
        if not _mounts == []:
            container['volumeMounts'] = _mounts
        #adding args if exists
        _args = dict_properties['args']
        if _args != None:
            container['args'] = _args 
        #adding command
        _command = dict_properties['command']
        if _command != None:
            container['command'] = _command 
        #liveness 
        _liveness = dict_properties['liveness']
        if _liveness != None:
            container['livenessProbe'] = self.prepareLivenessOrReadyness(_liveness)
        _readyness = dict_properties['readyness']
        if _readyness != None:
            container['readynessProbe'] = self.prepareLivenessOrReadyness(_readyness)
        return container
    def getPodsList(self):
        if _delete_lock:
            return None 
        api = kubernetes.client.CoreV1Api()
        pod_list = api.list_namespaced_pod(self.namespace)
        del self.list_pods[:]
        for pod in pod_list.items:
            #log.info("Pod name : "+pod.metadata.name+", status :"+ pod.status.phase)
            if not pod.metadata.name in self.list_pods:
                self.list_pods.append(pod.metadata.name)
        return self.list_pods
    def createMissingPods(self, missing_pods):
        for name in missing_pods:
            log.info(name+ " pod is missing, it will be created")
            (_object,body) = self.register.getObjectPerTMEName(name)
            if _object == None:
                log.error("Object to recreate is null ...")
                continue
            api = kubernetes.client.CoreV1Api()
            #log.info("Deleting "+ name +" from the api ...")
            #self.api.delete_namespaced_pod(name, self.namespace)
            log.info("Creation process will start in 10s")
            #time.sleep(10)
            kopf.adopt(_object, owner=body)
            obj = api.create_namespaced_pod(self.namespace, _object)
            log.info("Pod "+ _object['metadata']['name']+" recreated")

    def getAllObjects(self):
        return self.register.getAllPodsObject()
    def preparePod(self, name,plan, containers):
        containers_name = plan['containers']
        all_volumes = []
        all_init_containers = []
        for container_name in containers_name:
            dict_properties = self.loadComponentConfig(container_name)
            #preparing volume
            _volumes = self.prepareVolumes(dict_properties['volumes'])
            if _volumes != None:
                all_volumes.extend(_volumes)
            #fix mount access right
            if dict_properties['initContainers'] != None:
                all_init_containers.extend(dict_properties['initContainers'])

        pod = {'apiVersion': 'v1', 'metadata': {'name' : name, 'labels': {'app': name}}}
        containers['volumes'] = all_volumes
        if _platform != "openshift":
            containers['initContainers'] = all_init_containers
        pod['spec'] = containers
        return pod 
    def getAllTypes(self):
        _types = []
        for plan in self.planner["pods"]:
            _types.append(plan["type"])
        return _types 
    def start(self,namespace):
        self.namespace = namespace
        if _deploy_type == "ALL":
            _types = self.getAllTypes()
            for _type in _types:
                self.deployType(_type)
                time.sleep(10)
    def getTypePlan(self,_type):
        for plan in self.planner["pods"]:
            if _type == plan["type"]:
                return plan 
        return None 
    def createPod(self,pod,namespace,body,_type):
        try:
            kopf.adopt(pod, owner=body)
            obj = self.api.create_namespaced_pod(namespace, pod) 
            self.register.createKubeObject(_type,pod,"pod")
            return True 
        except Exception as e:
            raise kopf.HandlerFatalError(e)
    def createService(self,svc,namespace,body,_type):
        try:
            kopf.adopt(svc, owner=body)
            obj = self.api.create_namespaced_service(namespace, svc) 
            self.register.createKubeObject(_type,svc,"svc")
            return True 
        except Exception as e:
            raise kopf.HandlerFatalError(e)
    def deployPrometheusWripper(self, spec, name, namespace, _type, body):
        if self.register.checkObjectName("querier") == None:
            raise kopf.HandlerFatalError(f"Deploy first a querier type")
        #create sidecar pod 
        name = 'sidecar-'+name 
        #pod = {'apiVersion': 'v1', 'metadata': {'name' : name, 'labels': {'app': name}}}
        containers = []
        containers.append(self.prepareContainer('sidecar',_type))
        sa = 'default'
        if 'serviceAccountName' in spec:
            sa = spec['serviceAccountName']
        containers_wrapper = {'containers': containers}
        plan = {'containers': ['sidecar']}
        pod = self.preparePod(name,plan,containers_wrapper)
        #replace prometheus.url value by the provided
        pod['spec']['containers'][0]['args'][2] = '--prometheus.url='+ spec['prometheus']['url']
        pod['spec']['serviceAccountName'] = sa 
        #replace mounts and volumes 
        # mounts {"name":"sidecar-volume-prometheus","mountPath":"/prometheus"}
        # volumes {'name':'sidecar-volume-prometheus','persistentVolumeClaim':{'name': 'sidecar-prometheus-volume-claim'}}
        pod['spec']['containers'][0]['volumeMounts'][1] = {"name": spec['volume']['name'], "mountPath":"/prometheus"}
        pod['spec']['volumes'][1] = {"name": spec['volume']['name'],'persistentVolumeClaim':{'claimName': spec['volume']['claim_name']}}
        pod['spec']['initContainers'][0]["volumeMounts"][0]["name"] = spec['volume']['name']
        #creation of a service
        svc = {'apiVersion': 'v1', 'metadata': {'name' : name}, 'spec': { 'selector': {'app': name}, 'type': 'LoadBalancer'}}
        svc['spec']['ports'] = self.setSvc(self.getConfig("sidecar",'ports'))
        
        _new_service_hostname = name+"."+namespace+".svc.cluster.local:"+ str(svc['spec']['ports'][0]['port'])
        kopf.adopt(pod, owner=body)
        kopf.adopt(svc, owner=body)
        obj = self.api.create_namespaced_pod(namespace, pod)
        self.register.createKubeObject(_type,pod,"pod",pod['metadata']['name'],body)
        obj = self.api.create_namespaced_service(namespace, svc)
        self.register.createKubeObject(_type,svc,"svc")
        #adding new service created to the current querier
        querier_obj = self.register.getKubeObject("querier","pod").getObject()
        global _delete_lock
        _delete_lock = True 
        self.api.delete_namespaced_pod("querier", namespace)
        time.sleep(10) #sleep some moment
        #'--store='+sidecar_url
        querier_obj['spec']['containers'][0]['args'].append('--store='+_new_service_hostname)
        obj = self.api.create_namespaced_pod(namespace, querier_obj)
        _delete_lock = False 
        return f"Pod and Service created by TripleMonitoringEngine {name}"
    def deployType(self,_type, body, namespace):
        plan = self.getTypePlan(_type)
        if plan == None:
            raise kopf.HandlerFatalError(f"Type does not exist")
        #making containers
        containers = []
        for container_name in plan["containers"]:
            containers.append(self.prepareContainer(container_name,_type))
        pod_name = plan["name"]
        sa = 'default'
        if 'serviceAccountName' in body['spec']:
            sa = body['spec']['serviceAccountName']
        containers_wrapper = { 'containers': containers, 'serviceAccountName': sa}
        pod = self.preparePod(pod_name,plan,containers_wrapper)
        #pod creation 
        #self.createPod(pod,namespace,body,_type)
        svcs = [] 
        time.sleep(5)
        if "services" in plan:
            if 'serviceType' in body['spec']:
                global _service_type
                _service_type = body['spec']['serviceType']
            services = plan["services"]
            for service in services:
                _ports = self.getConfig(service,'ports')
                if _ports != None:
                    _ports_object = self.setSvc(_ports)
                    svc = {'apiVersion': 'v1', 'metadata': {'name' : service,'labels':{'app': pod_name}}, 'spec': { 'selector': {'app': pod_name}, 'type': _service_type}}
                    svc['spec']['ports'] = _ports_object
                    svcs.append(svc)
                    #self.createService(svc,namespace,body,_type)
        #return f"Object {_type} created in {namespace}"
        return (pod,svcs)
        
    def loadComponentConfig(self,component):
        component_config = {}
        for k in list_config_field:
            _value = self.getConfig(component,k)
            component_config[k] = _value
        if component_config['image'] == None:
            raise kopf.HandlerFatalError(f"Image must be specified")
        return component_config

    def getConfig(self,_type,config):
        if not _type in self.configs:
            raise kopf.HandlerFatalError(f"Type must be set. Got {_type}.")
        if not config in self.configs[_type]:
            return None 
        return self.configs[_type][config]
    def setSvc(self,_ports):
        if _ports != None:
            svc = []
            for port in _ports:
                svc.append({ 'port': port['port'], 'targetPort': port['port'],'name':port['name']})
            return svc 
        return None
    #//////////////////////////////////////////////////////////////////////////////////////
    def prepareResourceConstraint(self,res):
        if res == None or len(res.keys()) == 0:
            return {"requests": {"memory": "64Mi","cpu": "250m"},"limits": {"memory": "1Gi","cpu": "500m"}}
        return res 
    def prepareEnvironmentVariable(self,_envs):
        if _envs == None or len(_envs.keys()) == 0:
            return None 
        else:
            result = []
            for k in _envs.keys():
                result.append({'name': k, 'value': str(_envs[k])})
            return result
    def prepareLivenessOrReadyness(self,_data):
        return {"httpGet": {"path": _data["path"],"port": _data["port"]},"initialDelaySeconds": 20,"periodSeconds": 20}

    def prepareContainerPorts(self,_ports):
        if _ports == []:
            return None 
        else:
            result = []
            for port in _ports:
                result.append({'containerPort': port['port']})
            return result
    def prepareVolumes(self,volumes):
        if volumes == []:
            return None 
        else:
            result = []
            for v in volumes:
                if not 'name' in v:
                    raise kopf.HandlerFatalError(f"Volume declaration incorrect")
                volume = {}
                volume['name'] = v['name']
                if 'configMap' in v:
                    volume['configMap'] = {'name': v['configMap']['name'],'items': [{'key': v['configMap']['key'],'path':v['configMap']['path']}]}
                elif 'persistentVolumeClaim' in v:
                    volume['persistentVolumeClaim'] = {'claimName': v['persistentVolumeClaim']['name']}
                else:
                    kopf.HandlerFatalError(f"Volume declaration not recognized")
                result.append(volume)
            return result 

register = Register()
operator = Operator(register)

@kopf.on.resume('unipi.gr', 'v1', 'triplemonitoringengines')
@kopf.on.create('unipi.gr', 'v1', 'triplemonitoringengines')
def create_fn(body, spec, **kwargs):
    # Get info from Database object
    name = body['metadata']['name']
    namespace = body['metadata']['namespace']
    _type = spec['type']
    msg = None 
    api = kubernetes.client.CoreV1Api()
    if _type == "tme-prometheus":
        msg = operator.deployPrometheusWripper(spec,name,namespace,_type,body)
    elif _type == "all-tme":
        interval = int(body['spec']['interval'])
        if interval < 10:
            interval = 10 
        components = body['spec']['components']
        for component_type in components.keys():
            component_spec = components[component_type]
            body['metadata']['name'] = component_spec['name']
            body['spec']['type'] = component_spec
            (pod,svcs) = operator.deployType(component_type,body,namespace)
            kopf.adopt(pod, owner=body)

            register.createKubeObject(name,pod,"pod",pod['metadata']['name'],body)
            obj = api.create_namespaced_pod(namespace, pod) 
            if svcs != []:
                for svc in svcs:
                    kopf.adopt(svc,owner=body)
                    obj = api.create_namespaced_service(namespace,svc)
                    register.createKubeObject(name,svc,"svc","None",body)
            time.sleep(interval)
    else:
        (pod,svcs) = operator.deployType(_type,body,namespace)
        kopf.adopt(pod, owner=body)

        register.createKubeObject(name,pod,"pod",pod['metadata']['name'],body)
        obj = api.create_namespaced_pod(namespace, pod) 
        if svcs != []:
            for svc in svcs:
                kopf.adopt(svc,owner=body)
                obj = api.create_namespaced_service(namespace,svc)
                register.createKubeObject(name,svc,"svc","None",body)
    return {"message": "Object created"}
        

@kopf.on.delete('unipi.gr', 'v1', 'triplemonitoringengines')
def delete(body, **kwargs):
    msg = f"TripleMonitoringEngine {body['metadata']['name']} and its Pod / Service children deleted"
    name = body['metadata']['name']
    register.removeKubeObject(name,"pod")
    register.removeKubeObject(name,"svc")
    return {'message': msg}

"""
@kopf.on.resume('unipi.gr', 'v1', 'triplemonitoringengines')
def resume(body, **_): 
    _date = body["metadata"]["creationTimestamp"]
    _type = body['spec']['type']
    register.loadKubeObject(_type,_date,{},"pod")
    operator.start(body['metadata']['namespace'])
    msg = f"Pod loaded into the register by TripleMonitoringEngine {_type}"
    return {"message": msg}
"""