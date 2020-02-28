import kopf, kubernetes, yaml, tme_config, time 

configs = tme_config.get_configs()
dict_properties = {}
list_config_field = ['image','ports','env','mounts','volumes']
list_types = ['prometheus','prometheusbeat','outapi','exporter','optimizer','pdp','manager','ml', 'qos','mongodb','rabbitmq','rabbitmq_exporter','grafana']
pod = {}
svc = []

def get_config(_type,config):
    if not _type in configs:
        raise kopf.HandlerFatalError(f"Type must be set. Got {_type}.")
    if not config in configs[_type]:
        return None 
    return configs[_type][config]

def prepareEnvironmentVariable(_envs):
    if _envs.keys() == []:
        return None 
    else:
        return _envs 
def prepareContainerPorts(_ports):
    if _ports == []:
        return None 
    else:
        result = []
        for port in _ports:
            result.append({'containerPort': port})
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
                volume['persistentVolumeClaim'] = {'claimName': v['persistentVolumClaim']['name']}
            result.append(volume)
        return result 

def set_pod_svc(_type):
    for k in list_config_field:
        _value = get_config(_type,k)
        dict_properties[k] = _value
    if dict_properties['image'] == None:
        raise kopf.HandlerFatalError(f"Image must be specified")
    #adding the image
    pod = { 'containers': [ { 'image': dict_properties['image'], 'name': type}]}
    #adding environment variables
    _envs = prepareEnvironmentVariable(dict_properties['env'])
    if _envs != None:
        pod['env'] = _envs 
    #adding containers port 
    _ports = prepareContainerPorts(dict_properties['ports'])
    if _ports != None:
        pod['ports'] = _ports 
    #adding volumes
    _mounts = dict_properties['mounts']
    if not _mounts == []:
        pod['volumeMounts'] = _mounts
    _volumes = prepareVolumes(dict_properties['volumes'])
    if _volumes != None:
        pod['volumes'] = _volumes 
    if _ports != None:
        for port in _ports:
            svc.append({ 'port': port, 'targetPort': port}) 
    return pod, svc
    
@kopf.on.create('unipi.gr', 'v1', 'triplemonitoringengines')
def create_fn(body, spec, **kwargs):
    # Get info from Database object
    name = body['metadata']['name']
    namespace = body['metadata']['namespace']
    type = spec['type']
    # Make sure type is provided
    if not type:
        raise kopf.HandlerFatalError(f"Type must be set. Got {type}.")
    # Pod template
    pod = {'apiVersion': 'v1', 'metadata': {'name' : name, 'labels': {'app': 'tme'}}}
    # Service template
    svc = {'apiVersion': 'v1', 'metadata': {'name' : name}, 'spec': { 'selector': {'app': 'tme'}, 'type': 'NodePort'}}
    if not type in list_types:
        raise kopf.HandlerFatalError(f"Type {type} is not TripleMonitoringEngine type")
    pod['spec'], svc['spec']['ports'] = set_pod_svc(type)

    # Make the Pod and Service the children of the Database object
    kopf.adopt(pod, owner=body)
    if svc['spec']['ports'] != []:
        kopf.adopt(svc, owner=body)

    # Object used to communicate with the API Server
    api = kubernetes.client.CoreV1Api()
    # Create Pod
    obj = api.create_namespaced_pod(namespace, pod)
    print(f"Pod {obj.metadata.name} created")
    # Create Service
    if svc['spec']['ports'] != []:
        obj = api.create_namespaced_service(namespace, svc)
        print(f"NodePort Service {obj.metadata.name} created, exposing on port {obj.spec.ports[0].node_port}")
    # Update status
    msg = f"Pod and Service created by TripleMonitoringEngine {name}"
    return {'message': msg}

@kopf.on.delete('unipi.gr', 'v1', 'triplemonitoringengines')
def delete(body, **kwargs):
    msg = f"TripleMonitoringEngine {body['metadata']['name']} and its Pod / Service children deleted"
    return {'message': msg}
