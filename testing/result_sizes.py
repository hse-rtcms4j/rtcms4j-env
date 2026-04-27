from more_itertools.more import unzip
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

# Group all latency values by size
delta_grouped = {}
for key, value in delta:
    delta_grouped.setdefault(key, []).append(value)

# Calculate multiple statistics for each size
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

# Print formatted statistics
print("\n" + "=" * 80)
print("DTO SIZE PERFORMANCE STATISTICS")
print("=" * 80)
print(
    f"{'Size':<10} {'Count':<8} {'Mean (ms)':<12} {'Median (ms)':<12} {'P95 (ms)':<12} {'P99 (ms)':<12} {'Std (ms)':<12}")
print("-" * 80)

for size_kb in sorted(result_stats.keys()):
    stats = result_stats[size_kb]
    size_label = f"{size_kb / 1024:.0f}MB" if size_kb >= 1024 else f"{size_kb}KB"
    print(f"{size_label:<10} {stats['count']:<8} {stats['mean_ms']:<12.2f} {stats['median_ms']:<12.2f} "
          f"{stats['p95_ms']:<12.2f} {stats['p99_ms']:<12.2f} {stats['std_ms']:<12.2f}")

# Plot comparison
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle('DTO Delivery Latency by Payload Size', fontsize=16, fontweight='bold')

# Prepare data for plotting
sizes_kb = sorted(result_stats.keys())
size_labels = [f"{s / 1024:.0f}MB" if s >= 1024 else f"{s}KB" for s in sizes_kb]

# Plot 1: Mean vs P95
ax1 = axes[0]
means = [result_stats[s]['mean_ms'] for s in sizes_kb]
p95s = [result_stats[s]['p95_ms'] for s in sizes_kb]

x = np.arange(len(sizes_kb))
width = 0.35

bars1 = ax1.bar(x - width / 2, means, width, label='Mean', color='steelblue', edgecolor='black')
bars2 = ax1.bar(x + width / 2, p95s, width, label='P95', color='lightblue', edgecolor='black')

# Add value labels
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

# Plot 2: Box plot showing distribution
ax2 = axes[1]
all_values = [delta_grouped[s] for s in sizes_kb]
bp = ax2.boxplot(all_values, labels=size_labels, patch_artist=True)

# Color boxes by latency
colors = plt.cm.RdYlGn_r(np.linspace(0.3, 0.8, len(sizes_kb)))
for patch, color in zip(bp['boxes'], colors):
    patch.set_facecolor(color)

ax2.set_xlabel('Payload Size', fontsize=12)
ax2.set_ylabel('Latency (ms)', fontsize=12)
ax2.set_title('Latency Distribution by Size', fontsize=12)
ax2.grid(True, alpha=0.3, axis='y')

# Optional: Use log scale if values span wide range
if max(means) / min(means) > 100:
    ax2.set_yscale('log')
    ax2.set_ylabel('Latency (ms) - Log Scale', fontsize=12)

plt.tight_layout()
plt.show()

# Print summary statistics table
print("\n" + "=" * 80)
print("PERFORMANCE SUMMARY")
print("=" * 80)

# Find best and worst performance
best_size = min(result_stats.items(), key=lambda x: x[1]['mean_ms'])
worst_size = max(result_stats.items(), key=lambda x: x[1]['mean_ms'])

print(
    f"\n✅ Best performance: {best_size[0] / 1024:.0f}MB payload -> {best_size[1]['mean_ms']:.2f}ms (P95: {best_size[1]['p95_ms']:.2f}ms)")
print(
    f"❌ Worst performance: {worst_size[0] / 1024:.0f}MB payload -> {worst_size[1]['mean_ms']:.2f}ms (P95: {worst_size[1]['p95_ms']:.2f}ms)")

# Analyze consistency (low std deviation is good)
print("\n📊 Consistency Analysis (lower std = more predictable):")
for size_kb in sorted(result_stats.keys()):
    stats = result_stats[size_kb]
    size_label = f"{size_kb / 1024:.0f}MB" if size_kb >= 1024 else f"{size_kb}KB"
    cv = (stats['std_ms'] / stats['mean_ms']) * 100  # Coefficient of variation
    consistency = "✅ Excellent" if cv < 15 else "⚠️ Moderate" if cv < 30 else "❌ Variable"
    print(f"  {size_label:<8} Std: {stats['std_ms']:.2f}ms (CV: {cv:.1f}%) - {consistency}")

# Analyze scaling (cost per MB)
print("\n📈 Cost per MB Analysis:")
prev_size = None
prev_mean = None
for size_kb in sorted(result_stats.keys()):
    size_mb = size_kb / 1024
    stats = result_stats[size_kb]
    cost_per_mb = stats['mean_ms'] / size_mb if size_mb > 0 else 0

    if prev_size is not None:
        incremental_mb = (size_kb - prev_size) / 1024
        incremental_latency = stats['mean_ms'] - prev_mean
        throughput_mbps = incremental_mb / (incremental_latency / 1000) if incremental_latency > 0 else 0
        print(
            f"  {size_mb:.0f}MB: {stats['mean_ms']:.2f}ms total, {cost_per_mb:.2f}ms/MB, {throughput_mbps:.1f}MB/s incremental")
    else:
        print(f"  {size_mb:.0f}MB: {stats['mean_ms']:.2f}ms total, {cost_per_mb:.2f}ms/MB")

    prev_size = size_kb
    prev_mean = stats['mean_ms']
