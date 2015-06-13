import json
import pandas as pd

f = open('ardupilot.log','r')

l = []

for line in f.readlines():
    l.append(json.loads(line.split('\n')[0]))

df = pd.DataFrame(l)
