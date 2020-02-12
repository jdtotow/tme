import time
import random
from prometheus_client import Metric

class Collector(object):
    def __init__(self,labels, metrics=dict):
        self._labels = {}
        self._labels.update(labels)
        self._metrics = metrics

    def _get_metrics(self):
        return self._metrics

    def collect(self):
        metrics = self._get_metrics()

        if metrics:
            for k, v in metrics.items():
                metric = Metric(k, k, 'gauge')
                labels = {}
                labels.update(self._labels)
                metric.add_sample(k, value=v, labels=labels)
                if metric.samples:
                    yield metric
                else:
                    pass

class MultiCollector(object):
    def __init__(self,collections):
        self.collections = collections
    def collect(self):
        if self.collections != []:
            for collection in self.collections:
                metrics = collection.getMetrics()
                labels = collection.getLabels()
                for k,v in metrics.items():
                    metric = Metric(k, k, 'gauge')
                    metric.add_sample(k,value=v, labels=labels)
                    if metric.samples:
                        yield metric
                    else:
                        pass
