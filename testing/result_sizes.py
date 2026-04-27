from more_itertools.more import unzip

with open('sizes_start.txt') as f:
    start_str = f.readlines()

with open('sizes_end.txt') as f:
    end_str = f.readlines()


import ast
def parse_json(line: str):
    j = ast.literal_eval(line)

    version = j['version']
    timestamp = j['timestamp']
    target_size_kb = j['target_size_kb']

    return version, timestamp, target_size_kb

import re
pattern = r'(.+) \[rtcms4j-sse\].* version=(.+)\)\.'
def parse_log(line: str):
    match = re.search(pattern, line)
    timestamp = match.group(1)
    version = match.group(2)

    return version, timestamp


start_parsed = [parse_json(s) for s in start_str]
end_parsed = [parse_log(s) for s in end_str]

from datetime import datetime
start = [(v, datetime.fromisoformat(t), kb) for (v, t, kb) in start_parsed]
end_map = {v: datetime.fromisoformat(t) for (v, t) in end_parsed}

delta = [(kb, (end_map[v] - stamp).total_seconds() * 1_000) for (v, stamp, kb) in start]
delta_grouped = {}
for key, value in delta:
    delta_grouped.setdefault(key, []).append(value)

import numpy as np
result_avg = {}
for key, values in delta_grouped.items():
    result_avg[key] = np.array(values).mean()
print(result_avg)

import matplotlib.pyplot as plt
x = ["1KB", "500KB", "1MB", "5MB", "10MB"]
y = np.array(list(map(lambda x: round(x, 1), result_avg.values())))

fig, ax = plt.subplots()
norm = plt.Normalize(y.min(), y.max() + 50)
bars = ax.bar(x, y, color=plt.cm.RdYlGn_r(norm(y)))
ax.bar_label(bars, padding=3)
ax.set_ylabel('time, ms')
ax.set_xlabel('payload size')
ax.set_ylim(0, y.max() * 1.1)
plt.show()
