import util
import logging
import subprocess

class Shell():
    def __init__(self, name, config_file):
        self._name = name
        self._command = util.required_key(config_file, "command")
        self._return_code = util.required_key(config_file, "return_code")
        self._return_value = config_file.get("return_value")
    
    def run(self):
        logging.info(f"Running [{self._command}] for [{self._name}]")
        result = subprocess.run(self._command, shell=True, capture_output=True)
        logging.info(f"Result of running [{self._command}] for [{self._name}] is [{result}]")
        stdout = result.stdout.decode("utf-8").strip();
        if (self._return_code == result.returncode):
            if (self._return_value is not None):
                return self._return_value == stdout
            return True
        else:
            logging.info(f"{self._return_value} {stdout}")
            return False

def create_command(name, config):
    if (config is None):
        return None
    elif (util.required_key(config, "type") == "shell"):
        return Shell(name, config)
    else:
        logging.error(f"Type [{config}] not recognized")
        exit (1)