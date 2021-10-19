import util
import logging
import paho.mqtt.client as paho

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

def run(config, on_connect, on_message):
    logging.info("MQTT connecting")
    client = paho.Client()
    if (config.username is not None):
        client.username_pw_set(config.username, config.password)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(config.host, config.port, 60)
    client.loop_forever()
        