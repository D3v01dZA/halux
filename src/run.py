import logging
import yaml
import json
import argparse
import state
import paho.mqtt.client as paho
import mqtt

logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)

parser = argparse.ArgumentParser(prog="Halux", description="Control a system through MQTT and Home Assistant")
parser.add_argument("--config", required=True, help="location of the config file")
args = parser.parse_args()

with open(args.config, "r") as file:
	try:
		config_file = yaml.safe_load(file)
	except yaml.YAMLError as ex:
		print("Invalid Config")
		print(ex)
		exit(1)

config = mqtt.create_config(config_file)
states = state.create_state(config_file)

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
    logging.info(f"Publishing current state [{current_state}] to [{config.topic}/{config.name}/status]")
    client.publish(f"{config.topic}/{config.name}/state", current_state, 2, True)

def publish_available_states():
    available_states = []
    for name in states.keys():
        available_states.append(name)
    available_states.append("error")
    logging.info(f"Publishing available states [{available_states}] to [{config.topic}/{config.name}/status]")
    json_value = {
        "name": config.name, 
        "command_topic": f"{config.topic}/{config.name}/activate", 
        "state_topic": f"{config.topic}/{config.name}/state",
        "options": available_states,
        "unique_id": config.id
    }
    client.publish(f"homeassistant/select/{config.topic}/{config.name}/config", json.dumps(json_value), 2, True)

def on_connect(client, userdata, flags, rc):
    if (rc != 0):
        logging.error(f"MQTT connection dailed with [{rc}]")
        exit(1)
    logging.info("MQTT connected")
    publish_available_states()
    publish_current_state(determine_current_state())
    logging.info(f"Subscribing to [{config.topic}/{config.name}/activate]")
    client.subscribe(f"{config.topic}/{config.name}/activate", 2)

def activate_state(name):
    current_state = determine_current_state()
    if (name == "error"):
        logging.warning(f"Cannot activate state error")
        publish_current_state(current_state)
    elif (current_state == name):
        logging.info(f"Current state is already [{name}]")
        publish_current_state(current_state)
    else:
        if (states.get(current_state).deactivate() is False):
            logging.warn(f"Failed to deactivate current state [{current_state}]")
            publish_current_state("broken")
        else:
            state = states.get(name)
            if (state is None):
                logging.warning(f"Tried to activate unknown state [{name}] in [{states.keys()}]")
                publish_current_state(current_state)
            else:
                if (state.activate()):
                    publish_current_state(name)
                else:
                    publish_current_state("broken")

def on_message(client, userdata, msg):
    if (msg.topic == f"{config.topic}/{config.name}/activate"):
        activate_state(msg.payload.decode("utf-8"))
    else:
        logging.warning(f"MQTT message received but not recognized [{msg.topic}] [{msg.payload}]")

logging.info("MQTT connecting")
client = paho.Client()
if (config.username is not None):
    client.username_pw_set(config.username, config.password)
client.on_connect = on_connect
client.on_message = on_message
client.connect(config.host, config.port, 60)
client.loop_forever()
