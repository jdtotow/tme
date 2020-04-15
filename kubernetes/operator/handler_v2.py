import kopf, kubernetes, yaml, tme_config, time, os  

configs = tme_config.get_configs()
dict_properties = {}
list_config_field = ['image','ports','env','mounts','volumes','args','initContainers','command','resources']

_deploy_type = os.environ.get("DEPLOYMENT_TYPE","COMPONENT")
_namespace = os.environ.get("NAMESPACE","default")
_service_type = os.environ.get("SERVICETYPE","ClusterIP")


class KubeObject():
    def __init__(self, name, creation, _object, _type):
        self.name = name 
        self.creation = creation
        self._object = _object 
        self._type = _type 
    def getType(self):
        return self._type 
    def getName(self):
        return self.name 
    def getType(self):
        return self._type
    def getObject(self):
        return self._object

class Register():
    def __init__(self):
        self.collector = {}
    def createKubeObject(self,name,_object,_type):
        kube_object = KubeObject(name,time.time(),_object,_type)
        self.collector[_type+"-"+name] = kube_object
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
            return True
        return False 
    def loadKubeObject(self,name,creation,_object,_type):
        kube_object = KubeObject(name,creation,_object,_type)
        self.collector[_type+"-"+name] = kube_object

class Operator():
    def __init__(self, register):
        self.register = register 
        self.planner = tme_config.loadPlanner()
        self.configs = tme_config.get_configs()
        self.api = kubernetes.client.CoreV1Api()
        self.namespace = None 
    def prepareContainer(self,name,_type):
        #name, image,_ports,_args, _env, _mounts, _volumes
        dict_properties = self.loadComponentConfig(name)
        #adding the image
        container = { 'image': dict_properties['image'], 'name': name}
        pod = { 'containers': [ { 'image': dict_properties['image'], 'name': _type}]}
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
        return container

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
            self.register.createKubeObject(_type,pod,"pod")
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
        containers_wrapper = {'containers': containers}
        plan = {'containers': ['sidecar']}
        pod = self.preparePod(name,plan,containers_wrapper)
        #replace prometheus.url value by the provided
        pod['spec']['containers'][0]['args'][2] = '--prometheus.url='+ spec['prometheus']['url']
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
        self.register.createKubeObject(_type,pod,"pod")
        obj = self.api.create_namespaced_service(namespace, svc)
        self.register.createKubeObject(_type,svc,"svc")
        #adding new service created to the current querier
        querier_obj = self.register.getKubeObject("querier","pod").getObject()
        self.api.delete_namespaced_pod("querier", namespace)
        time.sleep(5) #sleep some moment
        #'--store='+sidecar_url
        querier_obj['spec']['containers'][0]['args'].append('--store='+_new_service_hostname)
        obj = self.api.create_namespaced_pod(namespace, querier_obj)
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
        containers_wrapper = { 'containers': containers}
        pod = self.preparePod(pod_name,plan,containers_wrapper)
        #pod creation 
        #self.createPod(pod,namespace,body,_type)
        svc = None 
        time.sleep(5)
        if "services" in plan:
            services = plan["services"]
            for service in services:
                _ports = self.getConfig(service,'ports')
                if _ports != None:
                    _ports_object = self.setSvc(_ports)
                    svc = {'apiVersion': 'v1', 'metadata': {'name' : service}, 'spec': { 'selector': {'app': pod_name}, 'type': _service_type}}
                    svc['spec']['ports'] = _ports_object
                    #self.createService(svc,namespace,body,_type)
        #return f"Object {_type} created in {namespace}"
        return (pod,svc)
        
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
        if len(res.keys()) == 0:
            return {"requests": {"memory": "64Mi","cpu": "250m"},"limits": {"memory": "128Mi","cpu": "500m"}}
        return res 
    def prepareEnvironmentVariable(self,_envs):
        if _envs == None or len(_envs.keys()) == 0:
            return None 
        else:
            result = []
            for k in _envs.keys():
                result.append({'name': k, 'value': str(_envs[k])})
            return result
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
    else:
        (pod,svc) = operator.deployType(_type,body,namespace)
        kopf.adopt(pod, owner=body)
        obj = api.create_namespaced_pod(namespace, pod) 
        if svc != None:
            kopf.adopt(svc,owner=body)
            obj = api.create_namespaced_service(namespace,svc)
    return {"message": "Object created"}
        

@kopf.on.delete('unipi.gr', 'v1', 'triplemonitoringengines')
def delete(body, **kwargs):
    msg = f"TripleMonitoringEngine {body['metadata']['name']} and its Pod / Service children deleted"
    name = body['metadata']['name']
    register.removeKubeObject(name,"pod")
    register.removeKubeObject(name,"svc")
    return {'message': msg}

@kopf.on.resume('unipi.gr', 'v1', 'triplemonitoringengines')
def resume(body, **_): 
    _date = body["metadata"]["creationTimestamp"]
    _type = body['spec']['type']
    register.loadKubeObject(_type,_date,{},"pod")
    operator.start(body['metadata']['namespace'])
    msg = f"Pod loaded into the register by TripleMonitoringEngine {_type}"
    return {"message": msg}