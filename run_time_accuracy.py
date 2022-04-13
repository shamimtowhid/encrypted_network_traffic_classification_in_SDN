from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

script_path = "./script_1"
log_path = "./log.txt"

classes = ["CSi", "DNS", "CSa", "Quake3", "VoIP"]

actual_cls = {}
predicted_cls = {}

infer_time = []
with open(log_path, "r") as f:
    line = f.readlines()
    for l in line:
        if l[0] == '|':
            l_line = l[:-1].split('|')
            #print(l_line[1])
            if l_line[1].strip() == "Source IP":
                continue
            unique_id = hash("".join([l_line[3].strip(), l_line[4].strip()]))
            infer_time.append(float(l_line[6].strip()))
            if unique_id in predicted_cls.keys():
                predicted_cls[unique_id].append(classes.index(l_line[5].strip()))
            else:
                predicted_cls[unique_id] = [classes.index(l_line[5].strip())]
#print(predicted_cls)

with open(script_path, "r") as f:
    line = f.readlines()
    for l in line:
        l_line = l[:-1].split(" ")
        unique_id = hash("".join([l_line[1], l_line[3]]))
        if unique_id in actual_cls.keys():
            print("duplicate flows in script")
        else:
            actual_cls[unique_id] = classes.index(l_line[6])
#print(actual_cls)

# accuracy calculation
y_pred = []
y_true = []
for k,v in predicted_cls.items():
    for p in v:
        y_pred.append(p)
        y_true.append(actual_cls[k])

print("Accuracy: ", round(accuracy_score(y_true, y_pred)*100,2))
print("Precision: ", round(precision_score(y_true, y_pred, average='macro')*100,2))
print("Recall: ", round(recall_score(y_true, y_pred, average='macro')*100,2))
print("F1: ", round(f1_score(y_true, y_pred, average='macro')*100,2))
print("Avg inference time: ", round(sum(infer_time)/len(infer_time), 5))
