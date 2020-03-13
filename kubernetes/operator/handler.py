import kopf, kubernetes, yaml, tme_config, time 

configs = tme_config.get_configs()
dict_properties = {}
list_config_field = ['image','ports','env','mounts','volumes','args','initContainers']
list_types = ['prometheus','prometheusbeat','querier','gateway','outapi','exporter','optimizer','pdp','manager','ml', 'qos','mongodb','rabbitmq','rabbitmq_exporter','grafana','sidecar']
list_services = ['prometheus','prometheusbeat','outapi','manager','gateway','mongodb','rabbitmq','grafana','sidecar','querier']

class KubeObject():
    def __init__(self, name, creation, _object, _type):
        self.name = name 
        self.creation = creation
        self._object = _object 
        self._type = _type 
    def getName(self):
        return self.name 
    def getType(self):
        return self._type

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
    def removeKubeObject(self,name,_type):
        key = _type+"-"+name 
        if key in self.collector:
            del self.collector[key]
            return True
        return False 

register = Register()

def get_config(_type,config):
    if not _type in configs:
        raise kopf.HandlerFatalError(f"Type must be set. Got {_type}.")
    if not config in configs[_type]:
        return None 
    return configs[_type][config]

def prepareEnvironmentVariable(_envs):
    if len(_envs.keys()) == 0:
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

    # Object used to communicate with the API Server
    api = kubernetes.client.CoreV1Api()
    # Create Pod
    obj = api.create_namespaced_pod(namespace, pod)
    register.createKubeObject(_type,obj,"pod")
    print(f"Pod {obj.metadata.name} created")
    # Create Service
    if svc != None and svc['spec']['ports'] != []:
        obj = api.create_namespaced_service(namespace, svc)
        register.createKubeObject(_type,obj,"svc")
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
