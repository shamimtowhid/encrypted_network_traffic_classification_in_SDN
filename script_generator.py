import random

import numpy as np

FLOW_NUMBER = 20
classes = ["CSi", "CSa", "VoIP -h CRTP -VAD", "Quake3", "DNS"] # for demonstration

#classes = ["CSi"] # for feature generation

PATH = "./script_1"
IPs = ["10.0.0.2", "10.0.0.3", "10.0.0.4", "10.0.0.5", "10.0.0.6"]

mean, std = 100000, 15000
_time = np.random.normal(mean, std, FLOW_NUMBER)
_time = -np.sort(-_time)
_port = 1000

with open(PATH, "a") as f:
    for i in range(FLOW_NUMBER):
        ip = random.choice(IPs)
        cls = random.choice(classes)
        t = int(_time[i])
        line = "-a"+" "+ip+" "+"-rp"+" "+str(_port)+" "+"-t"+" "+str(t)+" "+cls+"\n"
        _port += 1
        f.write(line)
