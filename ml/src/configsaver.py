import os, json  

config_file_path = os.environ.get("CONFIGFILEPATH","../config")
class ConfigSaver():
    def __init__(self,handler):
        self.current_config = None
        self.handler = handler
    def setHandler(self,handler):
        self.handler = handler 
    def remove(self,key):
        if key in self.current_config:
            del self.current_config[key]
        self.save()

    def getConfig(self):
        return self.current_config

    def save(self):
        _file = open(config_file_path+'/config.json','w')
        _file.write(json.dumps(self.current_config))
        _file.close()

    def mergeConfig(self,config):
        for key in config.keys():
            if not self.hasKeyInConfig(key):
                self.current_config[key] = config
        self.save()
    def hasKeyInConfig(self,key):
        return key in self.current_config

    def checkPreviousConfig(self):
        _file = open(config_file_path+'/config.json','r')
        _content = _file.read()
        if _content == "":
            self.current_config = {}
        else:
            self.current_config = {}
            try:
                self.current_config = json.loads(_content)
            except Exception as e:
                pass 
            if self.current_config == {}:
                print("No previous config found")
                return None
            self.handler.setPreviousConfig(self.current_config)
        _file.close()
    def setConfig(self, key,value):
        self.current_config[key] = value 
        self.save()