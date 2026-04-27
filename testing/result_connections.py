import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


def load_sse_results(json_file: str = "sse_load_test_results.json"):
    """Load SSE load test results from JSON file"""
    with open(json_file, 'r') as f:
        data = json.load(f)

    # Extract data
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


def plot_latency_vs_clients(data: dict):
    """Plot latency metrics vs number of clients"""
    clients = data['clients']
    avg_lat = data['avg_latencies']
    p95_lat = data['p95_latencies']
    last_avg = data['last_recv_avg']
    last_p95 = data['last_recv_p95']

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('SSE Load Test Results', fontsize=16, fontweight='bold')

    # Plot 1: Average vs P95 Latency
    ax1 = axes[0, 0]
    ax1.plot(clients, avg_lat, 'o-', label='Average Latency', linewidth=2, markersize=8)
    ax1.plot(clients, p95_lat, 's-', label='P95 Latency', linewidth=2, markersize=8)
    ax1.set_xlabel('Number of Simultaneous Clients', fontsize=10)
    ax1.set_ylabel('Latency (ms)', fontsize=10)
    ax1.set_title('Average vs P95 Latency', fontsize=12)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_xscale('log')
    ax1.set_yscale('log')

    # Plot 2: Last Receiver Latency
    ax2 = axes[0, 1]
    ax2.plot(clients, last_avg, 'o-', label='Average Last Receiver', linewidth=2, markersize=8)
    ax2.plot(clients, last_p95, 's-', label='P95 Last Receiver', linewidth=2, markersize=8)
    ax2.set_xlabel('Number of Simultaneous Clients', fontsize=10)
    ax2.set_ylabel('Latency (ms)', fontsize=10)
    ax2.set_title('Last Receiver Latency (Slowest Client)', fontsize=12)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_xscale('log')
    ax2.set_yscale('log')

    # Plot 3: Success Rate
    ax3 = axes[1, 0]
    success_rates = data['success_rates']
    colors = ['green' if rate >= 95 else 'orange' if rate >= 80 else 'red' for rate in success_rates]
    ax3.bar(clients, success_rates, color=colors, alpha=0.7, edgecolor='black')
    ax3.axhline(y=95, color='green', linestyle='--', label='Target (95%)', alpha=0.7)
    ax3.axhline(y=80, color='orange', linestyle='--', label='Minimum (80%)', alpha=0.7)
    ax3.set_xlabel('Number of Simultaneous Clients', fontsize=10)
    ax3.set_ylabel('Success Rate (%)', fontsize=10)
    ax3.set_title('Message Delivery Success Rate', fontsize=12)
    ax3.legend()
    ax3.grid(True, alpha=0.3, axis='y')
    ax3.set_ylim(0, 105)

    # Plot 4: Scaling Factor (how latency grows with clients)
    ax4 = axes[1, 1]
    baseline_clients = clients[0]
    baseline_latency = avg_lat[0]
    scaling_factors = [lat / baseline_latency for lat in avg_lat]
    client_ratios = [c / baseline_clients for c in clients]

    ax4.plot(client_ratios, scaling_factors, 'o-', linewidth=2, markersize=8, label='Actual Scaling')
    ax4.plot([1, max(client_ratios)], [1, max(client_ratios)], 'r--', alpha=0.5, label='Linear Scaling (Ideal)')
    ax4.set_xlabel('Client Multiplier (x baseline)', fontsize=10)
    ax4.set_ylabel('Latency Multiplier (x baseline)', fontsize=10)
    ax4.set_title('Latency Scaling Analysis\n(lower is better)', fontsize=12)
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


def plot_comparative_barchart(data: dict):
    """Create bar chart comparing latencies at different client counts"""
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

    # Add value labels on bars
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

    # Use log scale if data spans wide range
    if max(avg_lat + p95_lat + last_avg) / min(avg_lat + p95_lat + last_avg) > 100:
        ax.set_yscale('log')
        ax.set_ylabel('Latency (ms) - Log Scale', fontsize=12)

    plt.tight_layout()
    plt.show()


def print_summary_table(data: dict):
    """Print formatted summary table"""
    print("\n" + "=" * 100)
    print("SSE LOAD TEST SUMMARY")
    print("=" * 100)
    print(f"{'Clients':<10} {'Success':<10} {'Avg Lat':<12} {'P95 Lat':<12} {'Last Recv':<15} {'Recommendation':<15}")
    print("-" * 100)

    for i, clients in enumerate(data['clients']):
        success = data['success_rates'][i]
        avg_lat = data['avg_latencies'][i]
        p95_lat = data['p95_latencies'][i]
        last_recv = data['last_recv_avg'][i]

        if success >= 95:
            rec = "✅ SAFE"
        elif success >= 80:
            rec = "⚠️ DEGRADED"
        else:
            rec = "❌ OVERLOAD"

        print(f"{clients:<10} {success:<9.1f}% {avg_lat:<12.2f} {p95_lat:<12.2f} {last_recv:<15.2f} {rec:<15}")

    # Find optimal capacity
    print("\n" + "=" * 100)
    print("CAPACITY RECOMMENDATION")
    print("=" * 100)

    safe_capacity = None
    for i, (clients, success) in enumerate(zip(data['clients'], data['success_rates'])):
        if success >= 95:
            safe_capacity = clients

    if safe_capacity:
        print(f"✅ Maximum stable connections: {safe_capacity}")
        print(f"💡 Recommended operating limit: {safe_capacity}")
        print(f"📊 P95 latency at this level: {data['p95_latencies'][data['clients'].index(safe_capacity)]:.2f}ms")
    else:
        print("⚠️ Unable to determine safe capacity - test more client counts")


def analyze_scalability(data: dict):
    """Analyze how well the system scales"""
    print("\n" + "=" * 100)
    print("SCALABILITY ANALYSIS")
    print("=" * 100)

    clients = data['clients']
    latencies = data['avg_latencies']

    # Calculate efficiency
    print(f"{'Clients':<10} {'Efficiency':<15} {'Interpretation':<40}")
    print("-" * 100)

    for i in range(1, len(clients)):
        client_ratio = clients[i] / clients[0]
        latency_ratio = latencies[i] / latencies[0]
        efficiency = (client_ratio / latency_ratio) * 100

        if efficiency > 80:
            interpretation = "✅ Excellent scaling"
        elif efficiency > 50:
            interpretation = "⚠️ Moderate scaling"
        else:
            interpretation = "❌ Poor scaling (bottleneck found)"

        print(f"{clients[i]:<10} {efficiency:<14.1f}% {interpretation:<40}")

    # Find bottleneck
    for i in range(1, len(clients)):
        if latencies[i] / clients[i] > latencies[i - 1] / clients[i - 1] * 2:
            print(f"\n⚠️ Potential bottleneck detected at {clients[i]} clients")
            print(
                f"   Latency per client increased by {latencies[i] / clients[i] / (latencies[i - 1] / clients[i - 1]):.1f}x")
            break


# Main execution
if __name__ == "__main__":
    # Load your results
    try:
        data = load_sse_results("sse_load_test_results.json")

        # Print summary
        print_summary_table(data)

        # Analyze scalability
        analyze_scalability(data)

        # Create plots
        plot_latency_vs_clients(data)
        plot_comparative_barchart(data)

    except FileNotFoundError:
        print("❌ sse_load_test_results.json not found!")
        print("Please run the load test first to generate results.")
    except Exception as e:
        print(f"❌ Error loading results: {e}")
        import traceback

        traceback.print_exc()
