import util

class Config():
    def __init__(self, config_file):
        mqtt_config = util.required_key(config_file, "mqtt")
        self.name = util.required_key(mqtt_config, "name")
        self.topic = mqtt_config.get("topic", "halux")
        self.host = mqtt_config.get("host", "mqtt")
        self.port = mqtt_config.get("port", 1883)
        self.username = mqtt_config.get("username")
        self.password = mqtt_config.get("password")
        self.id = util.required_key(mqtt_config, "id")

def create_config(config_file):
    return Config(config_file)
    