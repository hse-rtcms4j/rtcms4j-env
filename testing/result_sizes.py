import numpy as np
import matplotlib.pyplot as plt

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

result_stats = {}
for key, values in delta_grouped.items():
    values_array = np.array(values)
    result_stats[key] = {
        'count': len(values),
        'mean_ms': np.mean(values_array),
        'median_ms': np.median(values_array),
        'p95_ms': np.percentile(values_array, 95),
        'p99_ms': np.percentile(values_array, 99),
        'min_ms': np.min(values_array),
        'max_ms': np.max(values_array),
        'std_ms': np.std(values_array)
    }

# plots
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle('DTO Delivery Latency by Payload Size', fontsize=16, fontweight='bold')

sizes_kb = sorted(result_stats.keys())
size_labels = [f"{s / 1024:.0f}MB" if s >= 1024 else f"{s}KB" for s in sizes_kb]

ax1 = axes[0]
means = [result_stats[s]['mean_ms'] for s in sizes_kb]
p95s = [result_stats[s]['p95_ms'] for s in sizes_kb]

x = np.arange(len(sizes_kb))
width = 0.35

bars1 = ax1.bar(x - width / 2, means, width, label='Mean', color='steelblue', edgecolor='black')
bars2 = ax1.bar(x + width / 2, p95s, width, label='P95', color='lightblue', edgecolor='black')

for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width() / 2., height,
                 f'{height:.0f}', ha='center', va='bottom', fontsize=9)

ax1.set_xlabel('Payload Size', fontsize=12)
ax1.set_ylabel('Latency (ms)', fontsize=12)
ax1.set_title('Mean vs P95 Latency', fontsize=12)
ax1.set_xticks(x)
ax1.set_xticklabels(size_labels)
ax1.legend()
ax1.grid(True, alpha=0.3, axis='y')

ax2 = axes[1]
all_values = [delta_grouped[s] for s in sizes_kb]
bp = ax2.boxplot(all_values, labels=size_labels, patch_artist=True)

colors = plt.cm.RdYlGn_r(np.linspace(0.3, 0.8, len(sizes_kb)))
for patch, color in zip(bp['boxes'], colors):
    patch.set_facecolor(color)

ax2.set_xlabel('Payload Size', fontsize=12)
ax2.set_ylabel('Latency (ms)', fontsize=12)
ax2.set_title('Latency Distribution by Size', fontsize=12)
ax2.grid(True, alpha=0.3, axis='y')

if max(means) / min(means) > 100:
    ax2.set_yscale('log')
    ax2.set_ylabel('Latency (ms) - Log Scale', fontsize=12)

plt.tight_layout()
plt.show()
