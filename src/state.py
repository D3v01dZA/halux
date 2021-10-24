import logging
import command
import util

class Option():
    def __init__(self, config):
        self._name = util.required_key(config, "name")
        self._test = command.create_command(util.required_key(config, "test"))
        self._activate = command.create_command(config.get("activate"))
        self._deactivate = command.create_command(config.get("deactivate"))
    
    def name(self):
        return self._name

    def test(self):
        logging.info(f"Running test for [{self._name}]")
        return self._test.run(self._name)
    
    def activate(self):
        logging.info(f"Running activate for [{self._name}]")
        if (self._activate is None):
            logging.info(f"Running nothing to activate for [{self._name}]")
            return True
        if (self._activate.run(self._name)):
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
        if (self._deactivate.run(self._name)):
            if (self.test()):
                logging.error(f"Running deactivate for [{self._name}] succeeded but test succeeded immediately afterwards")
                return False
            else:
                logging.info(f"Running deactivate for [{self._name}] succeeded")
                return True
        else:
            logging.error(f"Running deactivate for [{self._name}] failed")
            return False

class Broken():
    def __init__(self):
        self._name = "broken"

    def name(self):
        return self._name

def create_options(config):
    states = {}
    for item in config:
        states[util.required_key(item, "name")] = Option(item)
    return states

class State():
    def __init__(self, config):
        self._name = util.required_key(config, "name")
        self._options = create_options(util.required_key(config, "options"))
    
    def name(self):
        return self._name
    
    def options(self):
        return self._options

def create_states(config):
    states = {}
    if config.get("states") is not None:
        for item in config["states"]:
            states[util.required_key(item, "name")] = State(item)
    return states
