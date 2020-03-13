#Global settings
namespace = "default"
domain = "svc.cluster.local"
prometheus_hostname = "prometheus."+namespace+"."+domain
prometheus_port = [{'port':9090,'name':'api'}]
prometheus_url = "http://" + prometheus_hostname + ":" + str(prometheus_port[0]['port'])
rabbitmq_hostname = "rabbitmq."+namespace+"."+domain 
rabbitmq_ports = [{'name':'server','port':5672},{'port':15672,'name':'console'}]
rabbitmq_url = "http://" + rabbitmq_hostname + ":" + str(rabbitmq_ports[1]['port'])
rabbitmq_username = "richardm"
rabbitmq_password = "bigdatastack"
mongodb_hostname = "mongodb."+namespace+"."+domain
mongodb_port = [{'port':27017,'name':'mongodb'}]
mongodb_uri = mongodb_hostname + ":" + str(mongodb_port[0]['port'])
mongodb_username = "uprc"
mongodb_password = "bigdatastack"
mongodb_dbname = "TPME"
elasticsearch_hostname = "elasticsearch."+namespace+"."+domain


#Prometheus config 
prometheus = {'image': 'prom/prometheus','ports': prometheus_port}
prometheus['env'] = {}
prometheus['args'] = ["--config.file=/etc/prometheus/prometheus.yml","--storage.tsdb.path=/prometheus","--web.console.libraries=/etc/prometheus/console_libraries","--storage.tsdb.retention.time=48h","--web.console.templates=/etc/prometheus/consoles","--web.enable-lifecycle"]
prometheus['mounts'] = [{"name": "prometheus-config-file-volume","mountPath":"/etc/prometheus/prometheus.yml","subPath":"prometheus.yml"},{"name":"config-volume-prometheus","mountPath":"/etc/prometheus"},{"name": "prometheus-tsdb","mountPath":"/prometheus"}]
prometheus['volumes'] = [{'name':'prometheus-config-file-volume','configMap':{'name':'configmap-prometheus','key':'prometheus.yml','path':'prometheus.yml'}},{'name':'config-volume-prometheus','persistentVolumeClaim':{'name': 'prometheus-config-claim'}},{'name':'prometheus-tsdb','persistentVolumeClaim':{'name':'prometheus-tsdb-claim'}}]
prometheus['initContainers'] = [{"name": "prometheus-config-permission-fix","image": "busybox","command": ["/bin/chmod","-R","777","/config"],"volumeMounts": [{"name": "config-volume-prometheus","mountPath": "/config"}]},{"name": "prometheus-tsdb-permission-fix","image": "busybox","command": ["/bin/chmod","-R","777","/tsdb"],"volumeMounts": [{"name": "prometheus-tsdb","mountPath": "/tsdb"}]}]
#PrometheusBeat config 
prometheusbeat = {'image': 'jdtotow/prometheusbeat','ports': [{'port':55679,'name':'master'},{'port':55680,'name':'secondary'}]}
prometheusbeat['env'] = {"PROMETHEUS_URL_API":prometheus_url,"EXPORTER_URL":"http://localhost:55679","METRICS_SOURCE":"manager,qos,optimizer,prometheusbeat,outapi,rabbitmq,pushgateway,exporter","RABBITMQ_HOST":rabbitmq_hostname,"SLEEP":0.1,"COMPONENTNAME":"prometheusbeat","UPDATEMETRICSLISTNAMEPERIOD":32,"EXPORTERPORT":55679,"DEPLOYMENT":"primary"}
prometheusbeat['mounts'] = []
prometheusbeat['volumes'] = []
#outapi
outapi = {'image': 'jdtotow/outapi','ports': [{'port':55670,'name':'outapi'}]}
outapi['env'] = {"ELASTICSEARCHHOST":elasticsearch_hostname,"MONGODBHOST":mongodb_hostname,"PROMETHEUS_URL_API":prometheus_url,"PROCESSINGDELAY":120,"DEFAULTEND":30}
outapi['mounts'] = []
outapi['volumes'] = []
#manager
manager = {'image':'jdtotow/manager','ports': [{'port':55671,'name':'manager'}]}
manager['env'] = {"MONGODB_HOST":mongodb_uri,"RABBITMQHOST":rabbitmq_hostname,"URLEXPORTER":"http://localhost:55671","COMPONENTNAME":"manager","NTHREADSCONSUMER":5}
manager['mounts'] = [{"name": "manager-config-file","mountPath":"/config/config.json","subPath":"config.json"}]
manager['volumes'] = [{'name':'manager-config-file','configMap':{'name':'configmap-manager','key':'config.json','path':'config.json'}}]
#exporter
exporter = {'image':'jdtotow/exporter','ports': [{'port':55684,'name':'exporter'}]}
exporter['env'] = {"RABBITMQHOSTNAME":rabbitmq_hostname}
exporter['mounts'] = []
exporter['volumes'] = []

#rabbitmq-exporter
rabbitmq_exporter = {'image':'kbudde/rabbitmq-exporter','ports':[{'port':9419,'name':'exporter'}]}
rabbitmq_exporter['env'] = {"RABBIT_URL":rabbitmq_url,"RABBIT_USER":rabbitmq_username,"RABBIT_PASSWORD":rabbitmq_password}
rabbitmq_exporter['mounts'] = []
rabbitmq_exporter['volumes'] = []

#rabbitmq
rabbitmq = {'image':'jdtotow/rabbitmq','ports': rabbitmq_ports}
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
grafana['env'] = {}
grafana['mounts'] = []
grafana['volumes'] = []

#pdp
pdp = {'image':'jdtotow/pdp'}
pdp['env'] = {"RABBITMQHOSTNAME":rabbitmq_hostname,"CONFIGFILEPATH":"/config","EVALUATIONINTERVAL":60}
pdp['mounts'] = [{"name": "pdp-config-file-volume","mountPath":"/config/config.json","subPath":"config.json"}]
pdp['volumes'] = [{'name':'pdp-config-file-volume','configMap':{'name':'configmap-pdp','key':'config.json','path':'config.json'}}]

#ml
ml = {'image':'jdtotow/ml'}
ml['env'] = {"RABBITMQHOST":rabbitmq_hostname}
ml['mounts'] = [{"name": "ml-dataset-volume","mountPath":"/dataset","subPath":""}]
ml['volumes'] = [{'name':'ml-dataset-volume','persistentVolumeClaim':{'name':'ml-dataset-volume'}}]

#qos
qos = {'image':'jdtotow/qos','ports': [{'port':55682,'name':'qos'}]}
qos['env'] = {"RABBITMQHOSTNAME":rabbitmq_hostname,"CONFIGFILEPATH":"/config","EXPORTERPORT":55682,"EXPORTER_URL":"http://qos:55682"}
qos['mounts'] = [{"name": "qos-config-file-volume","mountPath":"/config/config.json","subPath":"config.json"}]
qos['volumes'] = [{'name':'qos-config-file-volume','configMap':{'name':'configmap-qos','key':'config.json','path':'config.json'}}]

def get_configs():
    return {'prometheus': prometheus,'prometheusbeat': prometheusbeat,'outapi': outapi,'exporter': exporter,'optimizer': optimizer,'pdp': pdp,'manager': manager,'ml': ml, 'qos': qos, 'mongodb': mongodb,'rabbitmq':rabbitmq,'rabbitmq_exporter': rabbitmq_exporter,'grafana': grafana}

