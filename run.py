#!/usr/bin/python3

import logging
import yaml
import paho.mqtt.client as mqtt
import subprocess
import json

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

with open("/root/config.yml", "r") as file:
	try:
		config = yaml.safe_load(file)
	except yaml.YAMLError as ex:
		print("Invalid Config")
		print(ex)
		exit(1)

def required_key(config, key):
    value = config.get(key)
    if (value is not None):
        return value
    else:
        logging.error(f"Key [{key}] is required on [{config}]")
        exit(1)

mqtt_config = required_key(config, "mqtt")
mqtt_name = required_key(mqtt_config, "name")
mqtt_topic = mqtt_config.get("topic", "halux")
mqtt_host = mqtt_config.get("host", "localhost")
mqtt_port = mqtt_config.get("port", "1883")
mqtt_username = mqtt_config.get("username")
mqtt_password = mqtt_config.get("password")
mqtt_id = required_key(mqtt_config, "id")

def create_command(name, config):
    if (config is None):
        return None
    elif (required_key(config, "type") == "shell"):
        return Shell(name, config)
    else:
        logging.error(f"Type [{config}] not recognized")
        exit (1)

class State():
    def __init__(self, name, config):
        self._name = name
        self._test = create_command(name, required_key(config, "test"))
        self._activate = create_command(name, config.get("activate"))
        self._deactivate = create_command(name, config.get("deactivate"))
    
    def test(self):
        logging.info(f"Running test for [{self._name}]")
        return self._test.run()
    
    def activate(self):
        logging.info(f"Running activate for [{self._name}]")
        if (self._activate is None):
            logging.info(f"Running nothing to activate for [{self._name}]")
            return True
        if (self._activate.run()):
            if (self.test()):
                logging.info(f"Running activate for [{self._name}] succeeded")
                return True
            else:
                logging.error(f"Running activate for [{self._name}] succeeded but test failed immediately afterwards")
                return False
        else:
            logging.error(f"Running activate for [{self._name}] failed")
            return False

    def deactivate(self):
        logging.info(f"Running deactivate for [{self._name}]")
        if (self._deactivate is None):
            logging.info(f"Running nothing to deactivate for [{self._name}]")
            return True
        if (self._deactivate.run()):
            if (self.test()):
                logging.error(f"Running deactivate for [{self._name}] succeeded but test succeeded immediately afterwards")
                return False
            else:
                logging.info(f"Running deactivate for [{self._name}] succeeded")
                return True
        else:
            logging.error(f"Running deactivate for [{self._name}] failed")
            return False

class Shell():
    def __init__(self, name, config):
        self._name = name
        self._command = required_key(config, "command")
        self._return_code = required_key(config, "return_code")
        self._return_value = config.get("return_value")
    
    def run(self):
        logging.info(f"Running [{self._command}] for [{self._name}]")
        result = subprocess.run(self._command, shell=True, capture_output=True)
        logging.info(f"Result of running [{self._command}] for [{self._name}] is [{result}]")
        if (self._return_code == result.returncode):
            if (self._return_value is not None):
                return self._return_value == result.stdout.decode('utf-8').strip()
            return True
        else:
            logging.info(f"{self._return_value} {result.stdout.decode('utf-8').strip()}")
            return False

states = {}
for name, value in config["states"].items():
    states[name] = State(name, value)

def determine_current_state():
    logging.info("Determining current state")
    temp_state = None
    for key, value in states.items():
        if (value.test() is True):
            logging.info(f"Test [{key}] succeeded")
            if (temp_state != None):
                logging.error(f"Test [{key}] succeeded after [{temp_state}] already succeeded")
            temp_state = key
        else:
            logging.info(f"Test [{key}] failed")
    if (temp_state == None):
        temp_state = "broken"
    logging.info(f"Determined current state as [{temp_state}]")
    return temp_state

def publish_current_state(current_state):
    logging.info(f"Publishing current state [{current_state}] to [{mqtt_topic}/{mqtt_name}/status]")
    client.publish(f"{mqtt_topic}/{mqtt_name}/state", current_state, 2, False)

def publish_available_states():
    available_states = []
    for name in states.keys():
        available_states.append(name)
    available_states.append("error")
    logging.info(f"Publishing available states [{available_states}] to [{mqtt_topic}/{mqtt_name}/status]")
    config = {
        "name": mqtt_name, 
        "command_topic": f"{mqtt_topic}/{mqtt_name}/activate", 
        "state_topic": f"{mqtt_topic}/{mqtt_name}/state",
        "options": available_states,
        "unique_id": mqtt_id
    }
    client.publish(f"homeassistant/select/{mqtt_topic}/{mqtt_name}/config", json.dumps(config), 2, True)

def on_connect(client, userdata, flags, rc):
    if (rc != 0):
        logging.error(f"MQTT connection dailed with {rc}")
        exit(1)
    logging.info("MQTT connected")
    publish_available_states()
    publish_current_state(determine_current_state())
    logging.info(f"Subscribing to [{mqtt_topic}/{mqtt_name}/activate]")
    client.subscribe(f"{mqtt_topic}/{mqtt_name}/activate", 2)

def activate_state(name):
    current_state = determine_current_state()
    if (current_state == name):
        logging.info(f"Current state is already [{name}]")
    else:
        if (states.get(current_state).deactivate() is False):
            logging.warn(f"Failed to deactivate current state [{current_state}]")
            publish_current_state("broken")
        else:
            state = states.get(name)
            if (state is None):
                logging.warning(f"Tried to activate unknown state [{name}] in [{states.keys()}]")
            else:
                if (state.activate()):
                    publish_current_state(name)
                else:
                    publish_current_state("broken")

def on_message(client, userdata, msg):
    if (msg.topic == f"{mqtt_topic}/{mqtt_name}/activate"):
        activate_state(msg.payload.decode('utf-8'))
    else:
        logging.warning(f"MQTT message received but not recognized [{msg.topic}] [{msg.payload}]")

logging.info("MQTT connecting")
client = mqtt.Client()
if (mqtt_username is not None):
    client.username_pw_set(mqtt_config["username"], mqtt_config["password"])
client.on_connect = on_connect
client.on_message = on_message
client.connect(mqtt_config["host"], mqtt_config["port"], 60)
client.loop_forever()
