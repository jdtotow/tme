import kopf, kubernetes, yaml, tme_config, time 

configs = tme_config.get_configs()
dict_properties = {}
list_config_field = ['image','ports','env','mounts','volumes','args','initContainers','command']
list_types = ['prometheus','prometheusbeat','querier','gateway','outapi','exporter','optimizer','pdp','manager','ml', 'qos','mongodb','rabbitmq','rabbitmq_exporter','grafana','sidecar','minio','compactor','tme-prometheus']
list_services = ['prometheus','prometheusbeat','outapi','manager','gateway','mongodb','rabbitmq','grafana','sidecar','querier','minio']
_deploy_type = os.environ.get("DEPLOYMENT_TYPE","ALL")

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

register = Register()

class Operator():
    def __init__(self, register):
        self.register = register 
        self.planner = tme_config.loadPlanner()
        self.configs = tme_config.get_configs()
        self.api = kubernetes.client.CoreV1Api()
    def prepareContainer(self,name):
        #name, image,_ports,_args, _env, _mounts, _volumes
        dict_properties = self.loadComponentConfig(name)
        #adding the image
        container = { 'image': dict_properties['image'], 'name': name}
        pod = { 'containers': [ { 'image': dict_properties['image'], 'name': _type}]}
        #adding environment variables
        _envs = self.prepareEnvironmentVariable(dict_properties['env'])
        if _envs != None:
            container['env'] = _envs
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

    def preparePod(self, name, containers):
        pod = {'apiVersion': 'v1', 'metadata': {'name' : name, 'labels': {'app': name}}}
        pod['spec'] = containers
        return pod 
        
    def start(self):
        if _deploy_type == "ALL":
            pass 
    def getTypePlan(self,_type):
        for plan in self.planner["pods"]:
            if _type == plan["type"]:
                return plan 
        return None 
    def deployType(self,_type):
        plan = self.getTypePlan(_type)
        if plan == None:
            raise kopf.HandlerFatalError(f"Type does not exist")
        #making containers
        containers = []
        for container_name in plan["containers"]:
            containers.append(self.prepareContainer(container_name))
        pod_name = plan["name"]
        containers_wrapper = { 'containers': containers}
        #preparing volume
        _volumes = prepareVolumes(dict_properties['volumes'])
        if _volumes != None:
            containers_wrapper['volumes'] = _volumes
        #fix mount access right
        if dict_properties['initContainers'] != None:
            containers_wrapper['initContainers'] = dict_properties['initContainers']
        pod = self.preparePod(pod_name,containers_wrapper)
        
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

def get_config(_type,config):
    if not _type in configs:
        raise kopf.HandlerFatalError(f"Type must be set. Got {_type}.")
    if not config in configs[_type]:
        return None 
    return configs[_type][config]

def prepareEnvironmentVariable(_envs):
    if _envs == None or len(_envs.keys()) == 0:
        return None 
    else:
        result = []
        for k in _envs.keys():
            result.append({'name': k, 'value': str(_envs[k])})
        return result 
def prepareContainerPorts(_ports):
    if _ports == []:
        return None 
    else:
        result = []
        for port in _ports:
            result.append({'containerPort': port['port']})
        return result 
def prepareVolumes(volumes):
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

def set_svc(_ports):
    if _ports != None:
        svc = []
        for port in _ports:
            svc.append({ 'port': port['port'], 'targetPort': port['port'],'name':port['name']})
        return svc 
    return None 
def set_pod(_type):
    for k in list_config_field:
        _value = get_config(_type,k)
        dict_properties[k] = _value
    if dict_properties['image'] == None:
        raise kopf.HandlerFatalError(f"Image must be specified")
    #adding the image
    pod = { 'containers': [ { 'image': dict_properties['image'], 'name': _type}]}
    #adding environment variables
    _envs = prepareEnvironmentVariable(dict_properties['env'])
    if _envs != None:
        pod['containers'][0]['env'] = _envs
    #adding containers port 
    _ports = prepareContainerPorts(dict_properties['ports'])
    if _ports != None:
        pod['containers'][0]['ports'] = _ports 
    #adding volumes
    _mounts = dict_properties['mounts']
    if not _mounts == []:
        pod['containers'][0]['volumeMounts'] = _mounts
    _volumes = prepareVolumes(dict_properties['volumes'])
    if _volumes != None:
        pod['volumes'] = _volumes
    #fix mount acces right
    if dict_properties['initContainers'] != None:
        pod['initContainers'] = dict_properties['initContainers']
    #adding args if exists
    _args = dict_properties['args']
    if _args != None:
        pod['containers'][0]['args'] = _args 
    _command = dict_properties['command']
    if _command != None:
        pod['containers'][0]['command'] = _command 
    return pod
    
@kopf.on.create('unipi.gr', 'v1', 'triplemonitoringengines')
def create_fn(body, spec, **kwargs):
    # Get info from Database object
    name = body['metadata']['name']
    namespace = body['metadata']['namespace']
    _type = spec['type']
    # Make sure type is provided
    if not _type:
        raise kopf.HandlerFatalError(f"Type must be set. Got {_type}.")
    # Object used to communicate with the API Server
    api = kubernetes.client.CoreV1Api()
    # check tme-prometheus type
    if _type == "tme-prometheus":
        if register.checkObjectName("querier") == None:
            raise kopf.HandlerFatalError(f"Deploy first a querier type")
        #create sidecar pod 
        name = 'sidebar-'+name 
        pod = {'apiVersion': 'v1', 'metadata': {'name' : name, 'labels': {'app': name}}}
        pod['spec'] = set_pod("sidecar")
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
        svc['spec']['ports'] = set_svc(get_config("sidecar",'ports'))
        _new_service_hostname = name+"."+namespace+".svc.cluster.local:"+ str(svc['spec']['ports'][0]['port'])
        kopf.adopt(pod, owner=body)
        kopf.adopt(svc, owner=body)
        obj = api.create_namespaced_pod(namespace, pod)
        register.createKubeObject(_type,pod,"pod")
        obj = api.create_namespaced_service(namespace, svc)
        register.createKubeObject(_type,svc,"svc")
        #adding new service created to the current querier
        querier_obj = register.getKubeObject("querier","pod").getObject()
        api.delete_namespaced_pod("querier", namespace)
        time.sleep(5) #sleep some moment
        #'--store='+sidecar_url
        querier_obj['spec']['containers'][0]['args'].append('--store='+_new_service_hostname)
        obj = api.create_namespaced_pod(namespace, querier_obj)
        msg = f"Pod and Service created by TripleMonitoringEngine {name}"
        return {'message': msg}

    # Pod template
    pod = {'apiVersion': 'v1', 'metadata': {'name' : name, 'labels': {'app': name}}}
    if not _type in list_types:
        raise kopf.HandlerFatalError(f"Type {_type} is not TripleMonitoringEngine type")
    svc = None 
    if _type in list_services:
        # Service template
        svc = {'apiVersion': 'v1', 'metadata': {'name' : name}, 'spec': { 'selector': {'app': name}, 'type': 'LoadBalancer'}}
        svc['spec']['ports'] = set_svc(get_config(_type,'ports'))

    pod['spec'] = set_pod(_type)
    # Make the Pod and Service the children of the TripleMonitoringEngine object
    kopf.adopt(pod, owner=body)
    if svc != None and svc['spec']['ports'] != []:
        kopf.adopt(svc, owner=body)

    # Create Pod
    obj = api.create_namespaced_pod(namespace, pod)
    register.createKubeObject(_type,pod,"pod")
    print(f"Pod {obj.metadata.name} created")
    # Create Service
    if svc != None and svc['spec']['ports'] != []:
        obj = api.create_namespaced_service(namespace, svc)
        register.createKubeObject(_type,svc,"svc")
        print(f"NodePort Service {obj.metadata.name} created, exposing on port {obj.spec.ports[0].node_port}")
    # Update status

    msg = f"Pod and Service created by TripleMonitoringEngine {name}"
    return {'message': msg}

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
    msg = f"Pod loaded into the register by TripleMonitoringEngine {_type}"
    return {"message": msg}