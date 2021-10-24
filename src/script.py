import util
import command
import logging

class Script():
    def __init__(self, config):
        self._name = util.required_key(config, "name")
        self._command = command.create_command(config)
    
    def run(self):
        logging.info(f"Running script [{self._name}]")
        return self._command.run(self._name)

def create_scripts(config):
    scripts = {}
    if config.get("scripts") is not None:
        for item in config["scripts"]:
            scripts[util.required_key(item, "name")] = Script(item)
    return scripts
