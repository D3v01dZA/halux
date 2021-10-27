# halux
Control a system through MQTT and Home Assistant

# docker
Modify the dockerfile to install anything extra you may need
Mount config.yml at /root/config.yml

# systemd
apt-get install -y python3 python3-pip python3-venv
python3 -m venv ./venv
source ./venv/bin/activate
pip3 install pyyaml paho-mqtt

Modify halux.service as needed
Copy halux.service to /etc/systemd/system/
