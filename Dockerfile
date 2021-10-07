FROM ubuntu:20.04

ENV TZ=America/New_York
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && apt-get install -y pulseaudio python3 python3-pip

RUN pip3 install pyyaml

ADD ./run.py /root/run.py

ENTRYPOINT ["/root/run.py"]
