#!/bin/bash

docker build . -t pulsecontrol-dev
docker run --rm -v $(pwd)/config.yml:/root/config.yml pulsecontrol-dev
