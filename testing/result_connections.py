import json
import numpy as np
import matplotlib.pyplot as plt


def load_sse_results(json_file: str):
    with open(json_file, 'r') as f:
        data = json.load(f)

    clients = []
    success_rates = []
    avg_latencies = []
    p95_latencies = []
    last_recv_avg = []
    last_recv_p95 = []

    for clients_str, metrics in sorted(data.items(), key=lambda x: int(x[0])):
        clients.append(int(clients_str))
        summary = metrics['summary']
        success_rates.append(summary['avg_received_rate'])
        avg_latencies.append(summary['avg_latency_ms'])
        p95_latencies.append(summary.get('p95_latency_ms', summary['avg_latency_ms']))
        last_recv_avg.append(summary['avg_last_receiver_ms'])
        last_recv_p95.append(summary.get('p95_last_receiver_ms', summary['avg_last_receiver_ms']))

    return {
        'clients': clients,
        'success_rates': success_rates,
        'avg_latencies': avg_latencies,
        'p95_latencies': p95_latencies,
        'last_recv_avg': last_recv_avg,
        'last_recv_p95': last_recv_p95
    }


def plot_comparative_barchart(data: dict):
    clients = data['clients']
    avg_lat = data['avg_latencies']
    p95_lat = data['p95_latencies']
    last_avg = data['last_recv_avg']

    fig, ax = plt.subplots(figsize=(12, 6))

    x = np.arange(len(clients))
    width = 0.25

    bars1 = ax.bar(x - width, avg_lat, width, label='Average Latency', color='steelblue', edgecolor='black')
    bars2 = ax.bar(x, p95_lat, width, label='P95 Latency', color='lightblue', edgecolor='black')
    bars3 = ax.bar(x + width, last_avg, width, label='Last Receiver (avg)', color='orange', edgecolor='black')

    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2., height,
                    f'{height:.0f}', ha='center', va='bottom', fontsize=8)

    ax.set_xlabel('Number of Simultaneous Clients', fontsize=12)
    ax.set_ylabel('Latency (ms)', fontsize=12)
    ax.set_title('SSE Delivery Latency vs Concurrent Clients', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([f'{c}\nclients' for c in clients])
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

    if max(avg_lat + p95_lat + last_avg) / min(avg_lat + p95_lat + last_avg) > 100:
        ax.set_yscale('log')
        ax.set_ylabel('Latency (ms) - Log Scale', fontsize=12)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    data = load_sse_results("sse_load_test_results.json")

    plot_comparative_barchart(data)
