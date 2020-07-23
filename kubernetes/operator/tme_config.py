import json, os

#Global settings
namespace = os.environ.get("NAMESPACE","default")
domain = "svc.cluster.local"
prometheus_hostname = "localhost" #"prometheus-main."+namespace+"."+domain
prometheus_port = [{'port':9090,'name':'api'}]
prometheus_url = "http://" + prometheus_hostname + ":" + str(prometheus_port[0]['port'])
#///////////////////////////////////////////////////////////////////////////////////////////////
rabbitmq_hostname = "rabbitmq."+namespace+"."+domain 
rabbitmq_ports = [{'name':'server','port':5672},{'port':15672,'name':'console'}]
rabbitmq_url = "http://" + rabbitmq_hostname + ":" + str(rabbitmq_ports[1]['port'])
rabbitmq_username = "richardm"
rabbitmq_password = "bigdatastack"
#///////////////////////////////////////////////////////////////////////////////////////////////
mongodb_hostname = "mongodb."+namespace+"."+domain
mongodb_port = [{'port':27017,'name':'mongodb'}]
mongodb_uri = mongodb_hostname + ":" + str(mongodb_port[0]['port'])
mongodb_username = "uprc"
mongodb_password = "bigdatastack"
mongodb_dbname = "TPME"
#///////////////////////////////////////////////////////////////////////////////////////////////
elasticsearch_hostname = "elasticsearch."+namespace+"."+domain
logstash_hostname = "logstash."+namespace+"."+domain
#///////////////////////////////////////////////////////////////////////////////////////////////
thanos_ports = [{'port':10091,'name':'grpc'},{'port': 10902,'name':'http'}]
sidecar_hostname = "sidecar."+namespace+"."+domain
sidecar_url = sidecar_hostname+":"+str(thanos_ports[0]['port'])
gateway_hostname = "gateway."+namespace+"."+domain
gateway_url = gateway_hostname+":"+str(thanos_ports[0]['port'])
querier_url = "http://querier."+namespace+"."+domain+":"+str(thanos_ports[1]['port'])
#/////////////////////////////////////////////////////////////////////////////////////////////////
minio_ports = [{'port':9000,'name': 'service'}]
minio_hostname = "minio."+namespace+"."+domain
minio_url = minio_hostname+":"+ str(minio_ports[0]['port'])

#Prometheus config 
prometheus = {'image': 'prom/prometheus','ports': prometheus_port}
prometheus['env'] = {"NAMESPACE": namespace}
prometheus['args'] = ["--config.file=/etc/prometheus/prometheus.yml","--storage.tsdb.path=/prometheus","--web.console.libraries=/etc/prometheus/console_libraries","--storage.tsdb.max-block-duration=2h","--storage.tsdb.min-block-duration=2h","--web.console.templates=/etc/prometheus/consoles","--web.enable-lifecycle"]
prometheus['mounts'] = [{"name": "prometheus-config-file-volume","mountPath":"/etc/prometheus/prometheus.yml","subPath":"prometheus.yml"},{"name":"config-volume-prometheus","mountPath":"/etc/prometheus"},{"name": "prometheus-tsdb","mountPath":"/prometheus"}]
prometheus['volumes'] = [{'name':'prometheus-config-file-volume','configMap':{'name':'configmap-prometheus','key':'prometheus.yml','path':'prometheus.yml'}},{'name':'config-volume-prometheus','persistentVolumeClaim':{'name': 'prometheus-config-claim'}},{'name':'prometheus-tsdb','persistentVolumeClaim':{'name':'prometheus-tsdb-claim'}}]
#prometheus['initContainers'] = [{"name": "prometheus-config-permission-fix","image": "busybox","command": ["/bin/chmod","-R","777","/config"],"volumeMounts": [{"name": "config-volume-prometheus","mountPath": "/config"}]},{"name": "prometheus-tsdb-permission-fix","image": "busybox","command": ["/bin/chmod","-R","777","/tsdb"],"volumeMounts": [{"name": "prometheus-tsdb","mountPath": "/tsdb"}]}]
prometheus['resources'] = {"requests": {"memory": "32Mi","cpu": "50m"},"limits": {"memory": "1Gi","cpu": "500m"}}
#thanos sidecar
sidecar = {'image': 'quay.io/thanos/thanos:v0.10.0','ports':thanos_ports}
sidecar['args'] = ['sidecar','--tsdb.path=/prometheus','--prometheus.url='+prometheus_url,'--grpc-address=0.0.0.0:'+str(sidecar['ports'][0]['port']),'--http-address=0.0.0.0:'+str(sidecar['ports'][1]['port']),'--objstore.config-file=/etc/thanos/bucket_config.yaml']
sidecar['mounts'] = [{"name": "sidecar-bucket-config","mountPath":"/etc/thanos/bucket_config.yaml","subPath":"bucket_config.yaml"},{"name":"sidecar-volume-prometheus","mountPath":"/prometheus"}]
sidecar['volumes'] = [{'name':'sidecar-bucket-config','configMap':{'name':'configmap-bucket','key':'bucket_config.yaml','path':'bucket_config.yaml'}},{'name':'sidecar-volume-prometheus','persistentVolumeClaim':{'name': 'sidecar-prometheus-volume-claim'}}]
#sidecar['initContainers'] = [{"name": "sidecar-prometheus-permission-fix","image": "busybox","command": ["/bin/chmod","-R","777","/config"],"volumeMounts": [{"name": "sidecar-volume-prometheus","mountPath": "/config"}]}]
sidecar['resources'] = {"requests": {"memory": "32Mi","cpu": "50m"},"limits": {"memory": "1Gi","cpu": "500m"}}
sidecar['env'] = {"NAMESPACE": namespace}
#thanos querier
querier = {'image':'quay.io/thanos/thanos:v0.10.0','ports': thanos_ports}
querier['args'] = ['query','--grpc-address=0.0.0.0:'+str(querier['ports'][0]['port']),'--http-address=0.0.0.0:'+str(querier['ports'][1]['port']),'--query.replica-label=monitor','--store='+sidecar_url,'--store='+gateway_url]
querier['resources'] = {"requests": {"memory": "32Mi","cpu": "50m"},"limits": {"memory": "1Gi","cpu": "500m"}}
querier['mounts'] = []
querier['volumes'] = []
querier['env'] = {}
#thanos gateway 
gateway = {'image':'quay.io/thanos/thanos:v0.10.0','ports': thanos_ports}
gateway['args'] = ['store','--grpc-address=0.0.0.0:'+str(gateway['ports'][0]['port']),'--http-address=0.0.0.0:'+str(gateway['ports'][1]['port']),'--data-dir=/tmp/thanos/store','--objstore.config-file=/etc/thanos/bucket_config.yaml']
gateway['mounts'] = [{"name": "sidecar-bucket-config","mountPath":"/etc/thanos/bucket_config.yaml","subPath":"bucket_config.yaml"}]
gateway['volumes'] = [{'name':'sidecar-bucket-config','configMap':{'name':'configmap-bucket','key':'bucket_config.yaml','path':'bucket_config.yaml'}}]
gateway['resources'] = {"requests": {"memory": "32Mi","cpu": "25m"},"limits": {"memory": "1Gi","cpu": "500m"}}
gateway['env'] = {"NAMESPACE": namespace}
#thanos compactor 
compactor = {'image':'quay.io/thanos/thanos:v0.10.0','ports': thanos_ports}
compactor['env'] = {"NAMESPACE": namespace}
compactor['mounts'] = [{"name": "sidecar-bucket-config","mountPath":"/etc/thanos/bucket_config.yaml","subPath":"bucket_config.yaml"}]
compactor['volumes'] = [{'name':'sidecar-bucket-config','configMap':{'name':'configmap-bucket','key':'bucket_config.yaml','path':'bucket_config.yaml'}}]
compactor['args'] = ['compact','--log.level=debug','--data-dir=/data','--objstore.config-file=/etc/thanos/bucket_config.yaml','--wait']
compactor['resources'] = {"requests": {"memory": "32Mi","cpu": "25m"},"limits": {"memory": "1Gi","cpu": "500m"}}
#PrometheusBeat config 
ingestor = {'image': 'jdtotow/prometheusbeat','ports': [{'port':55679,'name':'master'}]}
ingestor['env'] = {"PROMETHEUS_URL_API":querier_url,"RABBITMQ_PORT": rabbitmq_ports[0]['port'],"EXPORTER_URL":"http://localhost:55679","RABBITMQ_HOST":rabbitmq_hostname,"SLEEP":5,"COMPONENTNAME":"ingestor","UPDATEMETRICSLISTNAMEPERIOD":32,"EXPORTERPORT":55679,"DEPLOYMENT":"primary"}
ingestor['resources'] = {"requests": {"memory": "64Mi","cpu": "50m"},"limits": {"memory": "1Gi","cpu": "500m"}}
#ingestor['liveness'] = {"path":"/liveness","port": 55679}
#ingestor['readyness'] = {"path":"/readyness","port": 55679}
ingestor['mounts'] = []
ingestor['volumes'] = []
#outapi
outapi = {'image': 'jdtotow/outapi','ports': [{'port':55670,'name':'outapi'}]}
outapi['env'] = {"ELASTICSEARCHHOST":elasticsearch_hostname,"MONGODBHOST":mongodb_hostname,"PROMETHEUS_URL_API":prometheus_url,"PROCESSINGDELAY":120,"DEFAULTEND":30}
outapi['resources'] = {"requests": {"memory": "24Mi","cpu": "25m"},"limits": {"memory": "512Mi","cpu": "500m"}}
outapi['mounts'] = []
outapi['volumes'] = []
#manager
manager = {'image':'jdtotow/manager','ports': [{'port':55671,'name':'manager'}]}
manager['env'] = {"MONGODB_HOST":mongodb_uri,"RABBITMQHOST":rabbitmq_hostname,"URLEXPORTER":"http://localhost:55671","COMPONENTNAME":"manager","NTHREADSCONSUMER":1}
manager['mounts'] = [] #[{"name":"volume-manager","mountPath":"/config"}]
manager['volumes'] = [] #[{'name':'volume-manager','persistentVolumeClaim':{'name': 'volume-manager-claim'}}]
#manager['initContainers'] = [{"name": "manager-permission-fix","image": "busybox","command": ["/bin/chmod","-R","777","/data"],"volumeMounts": [{"name": "volume-manager","mountPath": "/data"}]}]
manager['resources'] = {"requests": {"memory": "24Mi","cpu": "25m"},"limits": {"memory": "512Mi","cpu": "500m"}}
#manager['liveness'] = {"path":"/liveness","port": 55671}
#manager['readyness'] = {"path":"/readyness","port": 55671}
#exporter
exporter = {'image':'jdtotow/exporter','ports': [{'port':55684,'name':'exporter'}]}
exporter['resources'] = {"requests": {"memory": "24Mi","cpu": "25m"},"limits": {"memory": "512Mi","cpu": "500m"}}
exporter['env'] = {"RABBITMQHOSTNAME":rabbitmq_hostname}
#exporter['liveness'] = {"path":"/liveness","port": 55684}
#exporter['readyness'] = {"path":"/readyness","port": 55684}
exporter['mounts'] = []
exporter['volumes'] = []

#logstash
logstash = {'image':'docker.elastic.co/logstash/logstash:6.4.3','ports': [{'port':8081,'name':'http'}]}
logstash['env'] = {"RABBITMQHOST":rabbitmq_hostname,"RABBITMQEXCHANGETYPE":"direct","RABBITMQQEUEU":"export_metrics","RABBITMQUSER":rabbitmq_username,"RABBITMQPASSWORD":rabbitmq_password,"LOGSTASH2HOST":logstash_hostname}
logstash['mounts'] = [{"name": "logstash-config","mountPath":"/usr/share/logstash/pipeline/logstash.conf","subPath":"logstash.conf"}]
logstash['volumes'] = [{'name':"logstash-config",'configMap':{'name':'configmap-logstash','key':'logstash-2.conf','path':'logstash.conf'}}]
logstash['resources'] = {"requests": {"memory": "1024Mi","cpu": "50m"},"limits": {"memory": "8048Mi","cpu": "900m"}}
#rabbitmq-exporter
rabbitmq_exporter = {'image':'kbudde/rabbitmq-exporter','ports':[{'port':9419,'name':'exporter'}]}
rabbitmq_exporter['env'] = {"RABBIT_URL":rabbitmq_url,"RABBIT_USER":rabbitmq_username,"RABBIT_PASSWORD":rabbitmq_password}
rabbitmq_exporter['mounts'] = []
rabbitmq_exporter['volumes'] = []

#rabbitmq
rabbitmq = {'image':'jdtotow/rabbitmq','ports': rabbitmq_ports}
rabbitmq['resources'] = {"requests": {"memory": "32Mi","cpu": "50m"},"limits": {"memory": "8000Mi","cpu": "500m"}}
rabbitmq['env'] = {}
rabbitmq['mounts'] = []
rabbitmq['volumes'] = []

#mongodb
mongodb = {'image':'mongo','ports':mongodb_port}
mongodb['env'] = {"MONGO_INITDB_ROOT_USERNAME":mongodb_username,"MONGO_INITDB_ROOT_PASSWORD":mongodb_password,"MONGO_INITDB_DATABASE":mongodb_dbname}
mongodb['mounts'] = [{"name": "mongodb-data-volume","mountPath":"/data/db"}]
mongodb['volumes'] = [{'name':'mongodb-data-volume','persistentVolumeClaim':{'name':'mongodb-data'}}]

#optimizer
optimizer = {'image':'jdtotow/optimizer','ports':[{'port':55674,'name':'optimizer'}]}
optimizer['env'] = {"PROMETHEUSCONFIPATH":"/config/prometheus.yml","PROMETHEUSAPI":prometheus_url,"HANDLINGINTERVAL":5,"MONGODBHOST":"mongodb:27017","MONGODBUSER":mongodb_username,"MONGODBPASSWORD":mongodb_password,"MONGODBDBNAME":mongodb_dbname,"LOGSTASHINPUTHTTP":"http://logstash2:8089/","LOWPERFORMANCETOLERANCE":75}
optimizer['mounts'] = []
optimizer['volumes'] = []

#grafana 
grafana = {'image': 'grafana/grafana','ports':[{'port':3000,'name':'grafana'}]}
grafana['resources'] = {"requests": {"memory": "64Mi","cpu": "50m"},"limits": {"memory": "2Gi","cpu": "500m"}}
grafana['env'] = {"GF_AUTH_ANONYMOUS_ENABLED":True}
grafana['mounts'] = []
grafana['volumes'] = []

#slalite
slalite = {'image': 'fermenreq/slalite:test','ports':[{'port': 8090,'name':'slalite'}]}
slalite['env'] = {'RABBITMQ_HOSTNAME': rabbitmq_hostname,'RABBITMQ_USER': rabbitmq_username,'RABBITMQ_PASS': rabbitmq_password}
slalite['mounts'] = []
slalite['volumes'] = []
#pdp
pdp = {'image':'jdtotow/pdp'}
pdp['env'] = {"RABBITMQHOSTNAME":rabbitmq_hostname,"CONFIGFILEPATH":"/config","EVALUATIONINTERVAL":60}
pdp['resources'] = {"requests": {"memory": "24Mi","cpu": "50m"},"limits": {"memory": "128Mi","cpu": "500m"}}
pdp['mounts'] = [{"name":"volume-pdp","mountPath":"/config"}]
pdp['volumes'] = [{'name':'volume-pdp','persistentVolumeClaim':{'name': 'volume-pdp-claim'}}]
#pdp['initContainers'] = [{"name": "pdp-permission-fix","image": "busybox","command": ["/bin/chmod","-R","777","/data"],"volumeMounts": [{"name": "volume-pdp","mountPath": "/data"}]}]

#ml
ml = {'image':'jdtotow/ml'}
ml['env'] = {"RABBITMQHOST":rabbitmq_hostname}
ml['mounts'] = [{"name": "ml-volume","mountPath":"/dataset","subPath":""}]
ml['resources'] = {"requests": {"memory": "24Mi","cpu": "50m"},"limits": {"memory": "128Mi","cpu": "500m"}}
ml['volumes'] = [{'name':'ml-volume','persistentVolumeClaim':{'name':'ml-volume-claim'}}]
#ml['initContainers'] = [{"name": "ml-volume-permission-fix","image": "busybox","command": ["/bin/chmod","-R","777","/data"],"volumeMounts": [{"name": "ml-volume","mountPath": "/data"}]}]

#qos
qos = {'image':'jdtotow/qos','ports': [{'port':55682,'name':'qos'}]}
qos['env'] = {"RABBITMQHOSTNAME":rabbitmq_hostname,"CONFIGFILEPATH":"/config","EXPORTERPORT":55682,"EXPORTER_URL":"http://qos:55682"}
qos['mounts'] = [{"name":"volume-qos","mountPath":"/config"}]
qos['volumes'] = [{'name':'volume-qos','persistentVolumeClaim':{'name': 'volume-qos-claim'}}]
qos['initContainers'] = [{"name": "qos-permission-fix","image": "busybox","command": ["/bin/chmod","-R","777","/data"],"volumeMounts": [{"name": "volume-qos","mountPath": "/data"}]}]
qos['resources'] = {"requests": {"memory": "24Mi","cpu": "50m"},"limits": {"memory": "128Mi","cpu": "500m"}}
#minio
minio = {'image': 'minio/minio:RELEASE.2020-01-03T19-12-21Z', 'ports': minio_ports}
minio['command'] = ['/bin/sh']
minio['args'] = ['-c','mkdir -p /data/thanos-bucket && /usr/bin/minio server /data']
minio['env'] = {'MINIO_ACCESS_KEY':'smth','MINIO_SECRET_KEY':'Need8Chars'}
minio['mounts'] = [{"name": "minio-volume","mountPath":"/data","subPath":""}]
minio['volumes'] = [{'name':'minio-volume','persistentVolumeClaim':{'name':'minio-volume-claim'}}]
#minio['initContainers'] = [{"name": "minio-volume-permission-fix","image": "busybox","command": ["/bin/chmod","-R","777","/data"],"volumeMounts": [{"name": "minio-volume","mountPath": "/data"}]}]
minio['resources'] = {"requests": {"memory": "64Mi","cpu": "50m"},"limits": {"memory": "8256Mi","cpu": "500m"}}
def get_configs():
    return {'prometheus': prometheus,'compactor':compactor,'gateway':gateway,'minio':minio,'sidecar': sidecar,'querier':querier,'ingestor': ingestor,'outapi': outapi,'slalite': slalite,'exporter': exporter,'optimizer': optimizer,'pdp': pdp,'manager': manager,'ml': ml, 'qos': qos, 'mongodb': mongodb,'rabbitmq':rabbitmq,'rabbitmq_exporter': rabbitmq_exporter,'grafana': grafana,'logstash': logstash}

def loadPlanner():
    _file = None
    try:
        _file = open("/config/planner.json","r")
    except:
        raise FileExistsError("Planner file not found")
    content = _file.read()
    _json = None 
    try:
        _json = json.loads(content)
    except:
        raise ValueError("JSON content is not correct")
    return _json 


