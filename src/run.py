import logging
import yaml
import json
import argparse
import script
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
		logging.error("Invalid Config")
		print(ex)
		exit(1)

config = mqtt.create_config(config_file)
scripts = script.create_scripts(config_file)
script_broken = False
states = state.create_states(config_file)

logging.info(f"Scripts: {scripts.keys()}")
logging.info(f"States: {states.keys()}")

def determine_current_option(current_state):
    logging.info(f"Determining current option for state {current_state.name()}")
    temp_option = None
    for key, value in current_state.options().items():
        if (value.test() is True):
            logging.info(f"Test [{key}] succeeded")
            if (temp_option != None):
                logging.error(f"Test [{key}] succeeded after [{temp_option.name()}] already succeeded")
            temp_option = value
        else:
            logging.info(f"Test [{key}] failed")
    if (temp_option == None):
        return None
    logging.info(f"Determined current option as [{temp_option.name()}] for state {current_state.name()}")
    return temp_option

def publish_current_option(client, current_state, current_option):
    logging.info(f"Publishing current state [{current_option}] to [{config.topic}/{config.name}/{current_state.name()}/status]")
    client.publish(f"{config.topic}/{config.name}/{current_state.name()}/state", current_option, 2, True)

def publish_broken_option(client, current_state):
    logging.info(f"Publishing broken to [{config.topic}/{config.name}/{current_state.name()}-status/state]")
    client.publish(f"{config.topic}/{config.name}/{current_state.name()}-status/state", "ON", 2, True)

def publish_current_options(client):
    for current_state in states.values():
        current_option = determine_current_option(current_state)
        if (current_option is None):
            publish_broken_option(client, current_state)
        else:
            publish_current_option(client, current_state, current_option.name())

def publish_available_options(client, current_state):
    available_options = []
    for name in current_state.options().keys():
        available_options.append(name)
    logging.info(f"Publishing available options [{available_options}] to [homeassistant/select/{config.topic}/{current_state.name()}/config]")
    json_value = {
        "name": f"{config.name.title()} Halux {current_state.name().title()}", 
        "command_topic": f"{config.topic}/{config.name}/{current_state.name()}/activate", 
        "state_topic": f"{config.topic}/{config.name}/{current_state.name()}/state",
        "options": available_options,
        "unique_id": f"{config.id}-{current_state.name()}",
        "device": {
            "name": f"{config.name.title()} Halux",
            "manufacturer": config.topic.title(),
            "model": "Halux",
            "ids": config.id
        }
    }
    client.publish(f"homeassistant/select/{config.topic}/{config.id}-{config.name}-{current_state.name()}/config", json.dumps(json_value), 2, True)
    json_value = {
        "name": f"{config.name.title()} Halux {current_state.name().title()} Status", 
        "state_topic": f"{config.topic}/{config.name}/{current_state.name()}-status/state",
        "unique_id": f"{config.id}-{current_state.name()}-status",
        "device_class": "problem",
        "device": {
            "name": f"{config.name.title()} Halux",
            "manufacturer": config.topic.title(),
            "model": "Halux",
            "ids": config.id
        }
    }
    client.publish(f"homeassistant/binary_sensor/{config.topic}/{config.id}-{config.name}-{current_state.name()}-status/config", json.dumps(json_value), 2, True)

def publish_available_states(client):
    for current_state in states.values():
        publish_available_options(client, current_state)

def publish_not_broken_states(client):
    for current_state in states.values():
        logging.info(f"Publishing not broken to [{config.topic}/{config.name}/{current_state.name()}-status/state]")
        client.publish(f"{config.topic}/{config.name}/{current_state.name()}-status/state", "OFF", 2, True)

def subscribe_to_activate_topics(client):
    for name in scripts.keys():
        logging.info(f"Subscribing to [{config.topic}/{config.name}/scripts/{name}/activate]")
        client.subscribe(f"{config.topic}/{config.name}/scripts/{name}/activate", 2)
    for current_state in states.values():
        logging.info(f"Subscribing to [{config.topic}/{config.name}/{current_state.name()}/activate]")
        client.subscribe(f"{config.topic}/{config.name}/{current_state.name()}/activate", 2)

def publish_available_scripts(client):
    if scripts:
        for name in scripts.keys():
            logging.info(f"Publishing available scripts [name] to [homeassistant/button/{config.topic}/{config.id}-{config.name}-{name}-script/config]")
            json_value = {
                "name": f"{config.name.title()} Halux {name.replace('-', ' ').title()} Script", 
                "command_topic": f"{config.topic}/{config.name}/scripts/{name}/activate", 
                "unique_id": f"{config.id}-{name}-script",
                "device": {
                    "name": f"{config.name.title()} Halux",
                    "manufacturer": config.topic.title(),
                    "model": "Halux",
                    "ids": config.id
                }
            }
            client.publish(f"homeassistant/button/{config.topic}/{config.id}-{config.name}-{name}-script/config", json.dumps(json_value), 2, True)
        json_value = {
            "name": f"{config.name.title()} Halux Scripts Status", 
            "state_topic": f"{config.topic}/{config.name}/scripts_status/state",
            "unique_id": f"{config.id}-scripts-status",
            "device_class": "problem",
            "device": {
                "name": f"{config.name.title()} Halux",
                "manufacturer": config.topic.title(),
                "model": "Halux",
                "ids": config.id
            }
        }
        client.publish(f"homeassistant/binary_sensor/{config.topic}/{config.id}-{config.name}-scripts-status/config", json.dumps(json_value), 2, True)

def publish_default_script(client):
    logging.info(f"Publishing current script [idle] to [{config.topic}/{config.name}/scripts/status]")
    client.publish(f"{config.topic}/{config.name}/scripts/state", "idle", 2, True)

def publish_not_broken_script(client):
    logging.info(f"Publishing not broken to [{config.topic}/{config.name}/scripts_status/status]")
    client.publish(f"{config.topic}/{config.name}/scripts_status/state", "OFF", 2, True)
    publish_default_script(client)

def publish_broken_script(client):
    logging.info(f"Publishing broken to [{config.topic}/{config.name}/scripts_status/status]")
    client.publish(f"{config.topic}/{config.name}/scripts_status/state", "ON", 2, True)
    publish_default_script(client)

def publish_current_script(client, script):
    logging.info(f"Publishing current script [{script}] to [{config.topic}/{config.name}/scripts/status]")
    client.publish(f"{config.topic}/{config.name}/scripts/state", script, 2, True)

def on_connect(client, userdata, flags, rc):
    if (rc != 0):
        logging.error(f"MQTT connection dailed with [{rc}]")
        exit(1)
    logging.info("MQTT connected")
    publish_available_scripts(client)
    publish_default_script(client)
    publish_not_broken_script(client)
    publish_available_states(client)
    publish_not_broken_states(client)
    publish_current_options(client)
    subscribe_to_activate_topics(client)

def activate_script(client, name):
    if (script_broken):
        logging.warning(f"Script was previously broken")
        publish_broken_script(client)
    elif (name == "idle"):
        logging.warning(f"Cannot activate script none")
        publish_default_script(client)
    else:
        script = scripts.get(name)
        if (script is None):
            logging.warning(f"Tried to activate unknown script [{name}] in [{scripts.keys()}]")
            publish_default_script(client)
        else:
            publish_current_script(client, name)
            if script.run():
                publish_default_script(client)
            else:
                publish_broken_script(client)

def activate_option(client, current_state, name):
    current_option = determine_current_option(current_state)
    if (name == "broken"):
        logging.warning(f"Cannot activate option broken")
        publish_current_option(client, current_state, current_option.name())
    elif (current_option is None):
        logging.warning(f"Cannot change because currently broken")
        publish_broken_option(client, current_state)
    elif (current_option.name() == name):
        logging.info(f"Current option is already [{name}]")
        publish_current_option(client, current_state, current_option.name())
    else:
        option = current_state.options().get(name)
        if (option is None):
            logging.warning(f"Tried to activate unknown option [{name}] in [{current_state.options().keys()}]")
            publish_current_option(client, current_state, current_option.name())
        elif (current_option.deactivate() is False):
            logging.warning(f"Failed to deactivate current state [{current_option.name()}]")
            publish_broken_option(client, current_state)
        else:
            if (option.activate()):
                publish_current_option(client, current_state, name)
            else:
                publish_broken_option(client, current_state)

def on_message(client, userdata, msg):
    handled = False
    for name in scripts.keys():
        if (msg.topic == f"{config.topic}/{config.name}/scripts/{name}/activate"):
            handled = True
            activate_script(client, name)
    for current_state in states.values():
        if (msg.topic == f"{config.topic}/{config.name}/{current_state.name()}/activate"):
            handled = True
            activate_option(client, current_state, msg.payload.decode("utf-8"))
    if not handled:
        logging.warning(f"MQTT message received but not recognized [{msg.topic}] [{msg.payload}]")

mqtt.run(config, on_connect, on_message)
