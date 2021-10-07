#!/usr/bin/python3

import yaml

with open("/root/config.yml", "r") as file:
	try:
		config = yaml.safe_load(file)
	except yaml.YAMLError as ex:
		print("Invalid Config")
		print(ex)
		exit(1)

print(config)
