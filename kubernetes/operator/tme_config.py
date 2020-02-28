#Global settings
namespace = "tme"
domain = "svc.cluster.local"
prometheus_hostname = "prometheus."+namespace+"."+domain
prometheus_port = 9090
prometheus_url = "http://" + prometheus_hostname + ":" + str(prometheus_port)
rabbitmq_hostname = "rabbitmq."+namespace+"."+domain 
rabbitmq_ports = [5671,5672,15672]
rabbitmq_url = "http://" + rabbitmq_hostname + ":" + str(rabbitmq_ports[1])
rabbitmq_username = "richardm"
rabbitmq_password = "bigdatastack"
mongodb_hostname = "mongodb"
mongodb_port = 27017
mongodb_uri = mongodb_hostname + ":" + str(mongodb_port)
mongodb_username = "uprc"
mongodb_password = "bigdatastack"
mongodb_dbname = "TPME"
elasticsearch_hostname = "elasticsearch"


#Prometheus config 
prometheus = {'image': 'prom/prometheus','ports': [prometheus_port]}
prometheus['env'] = {}
prometheus['containerPorts'] = [{"containerPort": prometheus_port}]
prometheus['args'] = ["--config.file=/etc/prometheus/prometheus.yml","--storage.tsdb.path=/prometheus","--web.console.libraries=/etc/prometheus/console_libraries","--storage.tsdb.retention.time=48h","--web.console.templates=/etc/prometheus/consoles","--web.enable-lifecycle"]
prometheus['volumes'] = [{"name": "prometheus-config-file","mountPath":"/etc/prometheus/prometheus.yml","subPath":"prometheus.yml"},{"name":"config-volume","mountPath":"/etc/prometheus"},{"name": "prometheus-tsdb","mountPath":"/prometheus"}]

#PrometheusBeat config 
prometheusbeat = {'image': 'jdtotow/prometheusbeat','ports': [55679,55680],'containers': 2}
prometheusbeat['env'] = {"PROMETHEUS_URL_API":prometheus_url,"EXPORTER_URL":"http://localhost:55679","METRICS_SOURCE":"manager,qos,optimizer,prometheusbeat,outapi,rabbitmq,pushgateway,exporter","RABBITMQ_HOST":rabbitmq_hostname,"SLEEP":0.1,"COMPONENTNAME":"prometheusbeat","UPDATEMETRICSLISTNAMEPERIOD":32,"HTTP_OUT_URL":"http://optimizer:55674/beats","EXPORTERPORT":55679,"DEPLOYMENT":"primary"}
prometheusbeat['2'] = {"EXPORTER_URL":"http://localhost:55680","COMPONENTNAME":"prometheusbeat-2","EXPORTERPORT":55680,"DEPLOYMENT":"secondary"}

#outapi
outapi = {'image': 'jdtotow/outapi','ports': [55670]}
outapi['env'] = {"ELASTICSEARCHHOST":elasticsearch_hostname,"MONGODBHOST":mongodb_hostname,"PROMETHEUS_URL_API":prometheus_url,"PROCESSINGDELAY":120,"DEFAULTEND":30}

#manager
manager = {'image':'jdtotow/manager','ports': [55671]}
manager['env'] = {"MONGODB_HOST":mongodb_uri,"RABBITMQHOST":rabbitmq_hostname,"URLEXPORTER":"http://localhost:55671","COMPONENTNAME":"manager","NTHREADSCONSUMER":5}

#exporter
exporter = {'image':'jdtotow/exporter','ports': [55684]}
exporter['env'] = {"RABBITMQHOSTNAME":rabbitmq_hostname}

#rabbitmq-exporter
rabbitmq_exporter = {'image':'kbudde/rabbitmq-exporter','ports':[9419]}
rabbitmq_exporter['env'] = {"RABBIT_URL":rabbitmq_url,"RABBIT_USER":rabbitmq_username,"RABBIT_PASSWORD":rabbitmq_password}

#rabbitmq
rabbitmq = {'image':'jdtotow/rabbitmq','ports': rabbitmq_ports}
rabbitmq['env'] = {}

#mongodb
mongodb = {'image':'mongo','ports':[27017]}
mongodb['env'] = {"MONGO_INITDB_ROOT_USERNAME":mongodb_username,"MONGO_INITDB_ROOT_PASSWORD":mongodb_password,"MONGO_INITDB_DATABASE":mongodb_dbname}

#optimizer
optimizer = {'image':'jdtotow/optimizer','ports':[55674]}
optimizer['env'] = {"PROMETHEUSCONFIPATH":"/config/prometheus.yml","PROMETHEUSAPI":prometheus_url,"HANDLINGINTERVAL":5,"MONGODBHOST":"mongodb:27017","MONGODBUSER":mongodb_username,"MONGODBPASSWORD":mongodb_password,"MONGODBDBNAME":mongodb_dbname,"LOGSTASHINPUTHTTP":"http://logstash2:8089/","LOWPERFORMANCETOLERANCE":75}

#grafana 
grafana = {'image': 'grafana/grafana','ports':[3000]}
grafana['env'] = {}

#pdp
pdp = {'image':'jdtotow/pdp'}
pdp['env'] = {"RABBITMQHOSTNAME":rabbitmq_hostname,"CONFIGFILEPATH":"/config","EVALUATIONINTERVAL":60}

#ml
ml = {'image':'jdtotow/ml'}
ml['env'] = {"RABBITMQHOST":rabbitmq_hostname}

#qos
qos = {'image':'jdtotow/qos','ports': [55682]}
qos['env'] = {"RABBITMQHOSTNAME":rabbitmq_hostname,"CONFIGFILEPATH":"/config","EXPORTERPORT":55682,"EXPORTER_URL":"http://qos:55682"}

def get_configs():
    return {'prometheus': prometheus,'prometheusbeat': prometheusbeat,'outapi': outapi,'exporter': exporter,'optimizer': optimizer,'pdp': pdp,'manager': manager,'ml': ml, 'qos': qos, 'mongodb': mongodb,'rabbitmq':rabbitmq,'rabbitmq_exporter': rabbitmq_exporter,'grafana': grafana}

