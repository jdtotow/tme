
def hasLabels(labels,_labels):
        if labels == None or labels == {}:
            return True
        for key in _labels.keys():
            if key in labels:
                if labels[key] != _labels[key]:
                    return False
        return True 

labels = {'app':'server1','job':'job1'}

c_labels = {'app':'server1','job':'job1'}

out = hasLabels(c_labels,labels)
print(out)