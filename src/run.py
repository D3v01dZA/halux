import logging
import yaml
import json
import argparse
import state
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
states = state.create_states(config_file)

def determine_current_option(state):
    logging.info(f"Determining current option for state {state.name()}")
    temp_option = None
    for key, value in state.options().items():
        if (value.test() is True):
            logging.info(f"Test [{key}] succeeded")
            if (temp_option != None):
                logging.error(f"Test [{key}] succeeded after [{temp_option.name()}] already succeeded")
            temp_option = value
        else:
            logging.info(f"Test [{key}] failed")
    if (temp_option == None):
        temp_option = "broken"
    logging.info(f"Determined current option as [{temp_option.name()}] for state {state.name()}")
    return temp_option

def publish_current_option(client, state, current_option):
    logging.info(f"Publishing current state [{current_option}] to [{config.topic}/{config.name}/{state.name()}/status]")
    client.publish(f"{config.topic}/{config.name}/{state.name()}/state", current_option, 2, True)

def publish_current_options(client):
    for state in states.values():
        publish_current_option(client, state, determine_current_option(state).name())

def publish_available_options(client, state):
    available_states = []
    for name in state.options().keys():
        available_states.append(name)
    available_states.append("error")
    logging.info(f"Publishing available states [{available_states}] to [{config.topic}/{config.name}/status]")
    json_value = {
        "name": config.name, 
        "command_topic": f"{config.topic}/{config.name}/{state.name()}/activate", 
        "state_topic": f"{config.topic}/{config.name}/{state.name()}/state",
        "options": available_states,
        "unique_id": f"{config.id}-{state.name()}"
    }
    client.publish(f"homeassistant/select/{config.topic}/{config.name}/config", json.dumps(json_value), 2, True)

def publish_available_states(client):
    for state in states.values():
        publish_available_options(client, state)

def subscribe_to_activate_topics(client):
    for state in states.values():
        logging.info(f"Subscribing to [{config.topic}/{config.name}/{state.name()}/activate]")
        client.subscribe(f"{config.topic}/{config.name}/{state.name()}/activate", 2)

def on_connect(client, userdata, flags, rc):
    if (rc != 0):
        logging.error(f"MQTT connection dailed with [{rc}]")
        exit(1)
    logging.info("MQTT connected")
    publish_available_states(client)
    publish_current_options(client)
    subscribe_to_activate_topics(client)

def activate_option(client, state, name):
    current_option = determine_current_option(state)
    if (name == "broken"):
        logging.warning(f"Cannot activate option broken")
        publish_current_option(client, current_option.name())
    elif (current_option.name() == name):
        logging.info(f"Current option is already [{name}]")
        publish_current_option(client, state, current_option.name())
    else:
        option = state.options().get(name)
        if (option is None):
            logging.warning(f"Tried to activate unknown option [{name}] in [{state.options().keys()}]")
            publish_current_option(client, state, current_option.name())
        elif (current_option.deactivate() is False):
            logging.warning(f"Failed to deactivate current state [{current_option.name()}]")
            publish_current_option(client, state, "broken")
        else:
            if (option.activate()):
                publish_current_option(client, state, name)
            else:
                publish_current_option(client, state, "broken")

def on_message(client, userdata, msg):
    handled = False
    for state in states.values():
        if (msg.topic == f"{config.topic}/{config.name}/{state.name()}/activate"):
            handled = True
            activate_option(client, state, msg.payload.decode("utf-8"))
    if not handled:
        logging.warning(f"MQTT message received but not recognized [{msg.topic}] [{msg.payload}]")

mqtt.run(config, on_connect, on_message)