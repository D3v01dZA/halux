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
        temp_option = state.Broken()
    logging.info(f"Determined current option as [{temp_option.name()}] for state {current_state.name()}")
    return temp_option

def publish_current_option(client, current_state, current_option):
    logging.info(f"Publishing current state [{current_option}] to [{config.topic}/{config.name}/{current_state.name()}/status]")
    client.publish(f"{config.topic}/{config.name}/{current_state.name()}/state", current_option, 2, True)

def publish_current_options(client):
    for current_state in states.values():
        publish_current_option(client, current_state, determine_current_option(current_state).name())

def publish_available_options(client, current_state):
    available_options = []
    for name in current_state.options().keys():
        available_options.append(name)
    available_options.append("broken")
    logging.info(f"Publishing available options [{available_options}] to [homeassistant/select/{config.topic}/{current_state.name()}/config]")
    json_value = {
        "name": f"{config.name}-{current_state.name()}", 
        "command_topic": f"{config.topic}/{config.name}/{current_state.name()}/activate", 
        "state_topic": f"{config.topic}/{config.name}/{current_state.name()}/state",
        "options": available_options,
        "unique_id": f"{config.id}-{current_state.name()}",
        "device": {
            "name": config.name.capitalize(),
            "manufacturer": config.topic.capitalize(),
            "model": "Halux",
            "ids": config.id
        }
    }
    client.publish(f"homeassistant/select/{config.topic}/{current_state.name()}/config", json.dumps(json_value), 2, True)

def publish_available_states(client):
    for current_state in states.values():
        publish_available_options(client, current_state)

def subscribe_to_activate_topics(client):
    client.subscribe(f"{config.topic}/{config.name}/scripts/activate", 2)
    for current_state in states.values():
        logging.info(f"Subscribing to [{config.topic}/{config.name}/{current_state.name()}/activate]")
        client.subscribe(f"{config.topic}/{config.name}/{current_state.name()}/activate", 2)

def publish_available_scripts(client):
    if scripts:
        available_scripts = []
        for name in scripts.keys():
            available_scripts.append(name)
        available_scripts.append("idle")
        available_scripts.append("broken")
        logging.info(f"Publishing available scripts [{available_scripts}] to [homeassistant/select/{config.topic}/scripts/config]")
        json_value = {
            "name": f"{config.name}-scripts", 
            "command_topic": f"{config.topic}/{config.name}/scripts/activate", 
            "state_topic": f"{config.topic}/{config.name}/scripts/state",
            "options": available_scripts,
            "unique_id": f"{config.id}-scripts",
            "device": {
                "name": config.name.capitalize(),
                "manufacturer": config.topic.capitalize(),
                "model": "Halux",
                "ids": config.id
            }
        }
        client.publish(f"homeassistant/select/{config.topic}/scripts/config", json.dumps(json_value), 2, True)

def publish_default_script(client):
    logging.info(f"Publishing current script [none] to [{config.topic}/{config.name}/scripts/status]")
    client.publish(f"{config.topic}/{config.name}/scripts/state", "idle", 2, True)

def publish_broken_script(client):
    script_broken = True
    logging.info(f"Publishing current script [broken] to [{config.topic}/{config.name}/scripts/status]")
    client.publish(f"{config.topic}/{config.name}/scripts/state", "broken", 2, True)

def on_connect(client, userdata, flags, rc):
    if (rc != 0):
        logging.error(f"MQTT connection dailed with [{rc}]")
        exit(1)
    logging.info("MQTT connected")
    publish_available_scripts(client)
    publish_default_script(client)
    publish_available_states(client)
    publish_current_options(client)
    subscribe_to_activate_topics(client)

def activate_script(client, name):
    if (script_broken):
        logging.warning(f"Script was previously broken")
        publish_broken_script(client)
    elif (name == "broken"):
        logging.warning(f"Cannot activate script broken")
        publish_default_script(client)
    elif (name == "idle"):
        logging.warning(f"Cannot activate script none")
        publish_default_script(client)
    else:
        script = scripts.get(name)
        if (script is None):
            logging.warning(f"Tried to activate unknown script [{name}] in [{scripts.keys()}]")
            publish_default_script(client)
        else:
            if script.run():
                publish_default_script(client)
            else:
                publish_broken_script(client)

def activate_option(client, current_state, name):
    current_option = determine_current_option(current_state)
    if (name == "broken"):
        logging.warning(f"Cannot activate option broken")
        publish_current_option(client, current_state, current_option.name())
    elif (current_option.name() == "broken"):
        logging.warning(f"Cannot change, already broken")
        publish_current_option(client, current_state, current_option.name())
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
            publish_current_option(client, current_state, "broken")
        else:
            if (option.activate()):
                publish_current_option(client, current_state, name)
            else:
                publish_current_option(client, current_state, "broken")

def on_message(client, userdata, msg):
    handled = False
    if (msg.topic == f"{config.topic}/{config.name}/scripts/activate"):
        handled = True
        activate_script(client, msg.payload.decode("utf-8"))
    for current_state in states.values():
        if (msg.topic == f"{config.topic}/{config.name}/{current_state.name()}/activate"):
            handled = True
            activate_option(client, current_state, msg.payload.decode("utf-8"))
    if not handled:
        logging.warning(f"MQTT message received but not recognized [{msg.topic}] [{msg.payload}]")

mqtt.run(config, on_connect, on_message)
