import os
import time
import random
import numpy as np

# settings
PATH = "/home/mininet/D-ITG-2.8.1-r1023/bin/ITGSend"
FLOW_COUNT = 100
TRAFFIC = "CSi" #DNS, CSi, CSa, Quake3, VoIP -h CRTP -VAD
IPs = ["10.0.0.2", "10.0.0.3", "10.0.0.4", "10.0.0.5", "10.0.0.6"]
# mean, std = 180000, 60000 # 3 m, 1m
mean, std = 100000, 15000 # 1.67 m, 15s
_time = np.random.normal(mean, std, FLOW_COUNT)


if __name__ == '__main__':

    for i in range(FLOW_COUNT):
        time.sleep(20)
        ip = random.choice(IPs)
        print("Flow Number: ", i)
        print("Destination: ", ip)
        t = int(_time[i])
        # to handle negative random numbers
        if t < 0:
            t = -1 * int(time[i])

        try:
            os.system(PATH+" "+"-a"+" "+ ip + " " + "-t"+" "+str(t)+" "+TRAFFIC)
        except Exception as ex:
            print("Exception: ", ex)
