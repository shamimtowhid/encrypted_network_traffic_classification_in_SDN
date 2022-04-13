#!/usr/bin/python
import subprocess, sys #to handle the Ryu output
import signal #for timer
import os #for process handling
import time

import numpy as np #for model features
import pandas as pd
import torch
from network import Net
#from pickle import load
#from sklearn.neural_network import MLPClassifier
from prettytable import PrettyTable #to display output from ML model

## command to run ##
cmd = "sudo ryu run /home/mininet/Desktop/encrypted_network_traffic_classification_in_SDN/monitor.py"
flows = {} #empty flow dictionary
FEATURE_COLLECTION = False
FEATURE_SIZE = 45
FLOW_COUNTER = 0
IDLE_TIMEOUT = 10


#model_path = "/home/mininet/Desktop/assignment/course_project/MLP_model.pkl"
model_path = "/home/mininet/Desktop/encrypted_network_traffic_classification_in_SDN/self_supervised.pth"
MEAN = 1195.9200582772974
STD = 3418.9485095351115
class_names = ["CSa", "CSi", "VoIP", "DNS", "Quake3"]

class Flow:
    def __init__(self, time_start, datapath, inport, ethsrc, ethdst, outport, packets, bytes):
        self.start_time = time_start
        self.datapath = datapath
        self.inport = inport
        self.ethsrc = ethsrc
        self.ethdst = ethdst
        self.outport = outport

        # for controlling the status of flow
        self.flag = True
        self.counter = 0
        self.feature_container = {"delta_forward_packet": [], "delta_forward_byte":[], 
                                  "delta_reverse_packet":[], "delta_reverse_byte":[]}

        #attributes for forward flow direction (source -> destination)
        self.forward_packets = packets
        self.forward_bytes = bytes
        self.forward_delta_packets = 0
        self.forward_delta_bytes = 0
        self.forward_status = 'ACTIVE'
        
        #attributes for reverse flow direction (destination -> source)
        self.reverse_packets = 0
        self.reverse_bytes = 0
        self.reverse_delta_packets = 0
        self.reverse_delta_bytes = 0
        self.reverse_status = 'INACTIVE'
        
    #updates the attributes in the forward flow direction
    def updateforward(self, packets, bytes):
        self.forward_delta_packets = packets - self.forward_packets
        self.forward_packets = packets
        
        self.forward_delta_bytes = bytes - self.forward_bytes
        self.forward_bytes = bytes
        
        if (self.forward_delta_bytes==0 or self.forward_delta_packets==0): #if the flow did not receive any packets of bytes
            self.forward_status = 'INACTIVE'
        else:
            self.forward_status = 'ACTIVE'

    #updates the attributes in the reverse flow direction
    def updatereverse(self, packets, bytes):
        self.reverse_delta_packets = packets - self.reverse_packets
        self.reverse_packets = packets
        
        self.reverse_delta_bytes = bytes - self.reverse_bytes
        self.reverse_bytes = bytes

        if (self.reverse_delta_bytes==0 or self.reverse_delta_packets==0): #if the flow did not receive any packets of bytes
            self.reverse_status = 'INACTIVE'
        else:
            self.reverse_status = 'ACTIVE'


def classify_feature(flow, model):
    t = PrettyTable(["Source IP", "Source Port", "Destination IP", "Destination Port", "Predicted Class", "Inference Time (s)"])
    features = pd.DataFrame.from_dict(flow.feature_container).to_numpy().reshape((-1, 4, 45))
    # normalization
    normalized_features = torch.tensor((features - MEAN)/STD)
    #normalized_features = (features - MEAN)/STD
    start_time = time.time()
    with torch.no_grad():
        predictions = model(normalized_features.float())
        _, predicted = torch.max(predictions.data, 1)
    #probabilities = model.predict_proba(normalized_features.reshape((-1, 180)))
    #predicted_class = class_names[np.argmax(probabilities)]
    predicted_class = class_names[predicted.data]
    #print("Flow between "+flow.ethsrc+":"+flow.inport+" and "+flow.ethdst+":"+flow.outport+" is: "+predicted_class)
    t.add_row([flow.ethsrc, flow.inport, flow.ethdst, flow.outport, predicted_class, round(time.time()-start_time, 5)])
    print(t)


def save_feature(features, fid, traffic_type):
    global FLOW_COUNTER
    df = pd.DataFrame.from_dict(features)
    fname = "./"+traffic_type+"/"+traffic_type+"_"+str(fid)+"_"+str(FLOW_COUNTER)+".csv"
    FLOW_COUNTER += 1
    df.to_csv(fname, index=False)


def append_flow(flow, fid, traffic_type, model):
    flow.feature_container["delta_forward_packet"].append(flow.forward_delta_packets)
    flow.feature_container["delta_forward_byte"].append(flow.forward_delta_bytes)
    flow.feature_container["delta_reverse_packet"].append(flow.reverse_delta_packets)
    flow.feature_container["delta_reverse_byte"].append(flow.reverse_delta_bytes)

    if len(flow.feature_container["delta_forward_packet"]) == FEATURE_SIZE:
        if FEATURE_COLLECTION and traffic_type:
            save_feature(flow.feature_container, fid, traffic_type)
        else:
            classify_feature(flow, model)

        flow.feature_container = {"delta_forward_packet": [], "delta_forward_byte":[],
                                  "delta_reverse_packet":[], "delta_reverse_byte":[]}



def flow_status(traffic_type, model):
    global flows
    for k, flow in flows.items():
        if flow.forward_status=='ACTIVE' or flow.reverse_status=='ACTIVE':
            flow.counter = 0
            flow.flag = True
            #  append to feature container here
            append_flow(flow, k, traffic_type, model)
            #print("Flow between "+flow.ethsrc+" and "+flow.ethdst+" is active.")
        elif flow.forward_status=='INACTIVE' and flow.reverse_status=='INACTIVE':
            flow.counter += 1
            # this block will be executed for the first time only when permanent INACTIVE state is detected for the first time
            if flow.counter >= IDLE_TIMEOUT and flow.flag:
                flow.flag=False
                append_flow(flow, k, traffic_type, model)
                #print("Permanent INACTIVE status detected for the first time")
            elif flow.counter < IDLE_TIMEOUT:
                # append to feature container here
                append_flow(flow, k, traffic_type, model)
                #print("Flow between "+flow.ethsrc+" and "+flow.ethdst+" is temporary inactive.")
            else:
                del flow # deleting the permanently deactivated flow
                # print("Flow between "+flow.ethsrc+" and "+flow.ethdst+" is INACTIVE")
        else:
            print("Flow status can not be determined")


def run_ryu(p,traffic_type=None, model=None):
    ## run it ##
    global flows
    while True:
        #print 'going through loop'
        out = p.stdout.readline()
        if out == '' and p.poll() != None: # poll returns None if the process hasn't completed
            print("breaking")
            break
        if out != '' and out.startswith(b'data'): #when Ryu 'simple_monitor_AK.py' script returns output
            fields = out.split(b'\t')[1:] #split the flow details
            
            fields = [f.decode(encoding='utf-8', errors='strict') for f in fields] #decode flow details 
            # print(fields)
            unique_id = hash(''.join([fields[2],fields[3],fields[4],fields[5]])) #create unique ID using src_port, src_ip, dst_ip, dst_port
            #print("Unique ID: ", unique_id)
            if unique_id in flows.keys():
                flows[unique_id].updateforward(int(fields[6]),int(fields[7])) #update forward attributes with packet, and byte count
                flow_status(traffic_type, model)
            else:
                rev_unique_id = hash(''.join([fields[5],fields[4],fields[3],fields[2]])) #switch source and destination to generate same hash for src/dst and dst/src
                #print("Reverse Unique ID: ", rev_unique_id)
                if rev_unique_id in flows.keys():
                    flows[rev_unique_id].updatereverse(int(fields[6]),int(fields[7])) #update reverse attributes with packet, and byte count
                    flow_status(traffic_type, model)
                else:
                    flows[unique_id] = Flow(int(fields[0]), fields[1], fields[2], fields[3], fields[4], fields[5], int(fields[6]), int(fields[7])) #create new flow object
                    flow_status(traffic_type, model)
    
if __name__ == '__main__':
# Running the script with the traffic type parameter
    if len(sys.argv) == 2:
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) #start Ryu process
        traffic_type = sys.argv[1]
        print("Process started for ", traffic_type)
        try:
            run_ryu(p,traffic_type=traffic_type)
        except Exception as ex:
            print("Exiting ", ex)
            os.killpg(os.getpgid(p.pid), signal.SIGTERM) #kill ryu process on exit
    else:
        try:
            FEATURE_COLLECTION = False
            net = Net(5)
            net.load_state_dict(torch.load(model_path))
            net.eval()
            #MODEL = load(open(model_path, "rb"))
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) #start Ryu process
            print("Waiting for traffic!!")
            #run_ryu(p, model=MODEL)
            run_ryu(p, model=net)
        except Exception as ex:
            print("Model can not loaded successfully!")
            print("Terminating Process")
            os.killpg(os.getpgid(p.pid), signal.SIGTERM)

    sys.exit();
