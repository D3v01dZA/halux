import logging
import command
import util

class State():
    def __init__(self, name, config):
        self._name = name
        self._test = command.create_command(name, util.required_key(config, "test"))
        self._activate = command.create_command(name, config.get("activate"))
        self._deactivate = command.create_command(name, config.get("deactivate"))
    
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

def create_state(config):
    states = {}
    for name, value in config["states"].items():
        states[name] = State(name, value)
    return states