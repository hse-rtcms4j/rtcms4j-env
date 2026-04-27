import asyncio
import aiohttp
import json
import random
import string
import time
import statistics
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
import requests


# ============ EXISTING CODE (adapted for async) ============
class DTOPayloadGenerator:
    def __init__(self):
        self.enum_values = ["GRASS", "DIRT"]

    def _generate_string(self, min_len: int = 5, max_len: int = 20) -> str:
        length = random.randint(min_len, max_len)
        return ''.join(random.choices(string.ascii_letters, k=length))

    def _generate_array(self, item_type: str, target_size_bytes: int, current_total_bytes: int) -> List:
        array = []
        estimated_item_size = 0

        if item_type == "string":
            test_item = self._generate_string()
            estimated_item_size = len(json.dumps(test_item)) + 1
        elif item_type in ["integer", "boolean"]:
            test_item = random.randint(0, 1000) if item_type == "integer" else random.choice([True, False])
            estimated_item_size = len(str(test_item)) + 1
        elif item_type == "number":
            test_item = round(random.uniform(0, 1000), 2)
            estimated_item_size = len(str(test_item)) + 1

        needed_bytes = target_size_bytes - current_total_bytes
        num_items = max(1, needed_bytes // max(1, estimated_item_size))

        for _ in range(min(num_items, 10000)):
            if item_type == "string":
                array.append(self._generate_string(10, 50))
            elif item_type == "integer":
                array.append(random.randint(0, 1000000))
            elif item_type == "number":
                array.append(round(random.uniform(0, 1000000), 2))
            elif item_type == "boolean":
                array.append(random.choice([True, False]))

        return array

    def generate_payload(self, version: str, target_size_kb: int) -> Dict[str, Any]:
        target_bytes = target_size_kb * 1024

        payload = {
            "intVal": random.randint(0, 1000),
            "enumVal": random.choice(self.enum_values),
            "intList": [random.randint(0, 1000) for _ in range(5)],
            "longVal": random.randint(0, 1000000),
            "version": version,
            "enumList": [random.choice(self.enum_values) for _ in range(5)],
            "floatVal": round(random.uniform(0, 1000), 2),
            "longList": [random.randint(0, 1000000) for _ in range(5)],
            "doubleVal": round(random.uniform(0, 1000000), 2),
            "floatList": [round(random.uniform(0, 1000), 2) for _ in range(5)],
            "stringVal": self._generate_string(20, 100),
            "booleanVal": random.choice([True, False]),
            "doubleList": [round(random.uniform(0, 1000000), 2) for _ in range(5)],
            "booleanList": [random.choice([True, False]) for _ in range(5)],
            "stringList": []
        }

        current_bytes = len(json.dumps(payload))

        if target_bytes > current_bytes:
            times = max(1, round(math.log2(target_bytes)))
            while current_bytes < target_bytes:
                payload["stringList"].extend([self._generate_string(20, 100) for _ in range(times)])
                current_bytes = len(json.dumps(payload))

        return payload


class KeycloakAuthenticator:
    def __init__(self, keycloak_url: str, realm: str, client_id: str, client_secret: Optional[str] = None):
        self.token_url = f"{keycloak_url}/realms/{realm}/protocol/openid-connect/token"
        self.client_id = client_id
        self.client_secret = client_secret

    def authenticate(self, username: str, password: str) -> Dict[str, str]:
        data = {
            "client_id": self.client_id,
            "grant_type": "password",
            "username": username,
            "password": password
        }

        if self.client_secret:
            data["client_secret"] = self.client_secret

        response = requests.post(self.token_url, data=data)
        response.raise_for_status()

        tokens = response.json()
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token"),
            "expires_in": tokens.get("expires_in", 300)
        }


# ============ SSE LOAD TESTING CODE ============
@dataclass
class SSEConnection:
    client_id: int
    namespace_id: str
    application_id: str
    access_token: str
    sse_base_url: str

    received_time: Optional[float] = None
    session: Optional[aiohttp.ClientSession] = None
    response: Optional[aiohttp.ClientResponse] = None

    async def connect_and_listen(self, received_event: asyncio.Event, commit_version: str):
        """Establish SSE connection and wait for specific commit"""
        self.session = aiohttp.ClientSession()

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache"
        }

        sse_url = f"{self.sse_base_url}/namespace/{self.namespace_id}/application/{self.application_id}/sse-stream"

        try:
            self.response = await self.session.get(sse_url, headers=headers)

            # Process SSE stream
            async for line in self.response.content:
                if line:
                    decoded = line.decode('utf-8').strip()
                    if decoded.startswith('data:'):
                        # Parse the event data
                        event_data = decoded[5:].strip()  # Remove 'data:' prefix
                        try:
                            event_json = json.loads(event_data)

                            # Check if this is a configuration update event (not heartbeat)
                            if not event_json.get('isHeartbeat', True):
                                config_event = event_json.get('configurationUpdateEvent')
                                if config_event:
                                    # Check if this is our commit by version
                                    content = config_event.get('content', '')
                                    if f'"version":"{commit_version}"' in content or commit_version in content:
                                        self.received_time = time.time()
                                        received_event.set()
                                        break
                        except json.JSONDecodeError:
                            pass

        except Exception as e:
            print(f"Client {self.client_id} SSE error: {e}")

    async def disconnect(self):
        """Close SSE connection"""
        if self.response:
            self.response.close()
        if self.session:
            await self.session.close()


class AsyncCommitHelper:
    """Helper to make commits asynchronously"""

    def __init__(self, backend_url: str, generator: DTOPayloadGenerator):
        self.backend_url = backend_url
        self.generator = generator

    async def commit_dto_version(self,
                                 nid: str, aid: str, cid: str,
                                 access_token: str,
                                 version: str,
                                 payload: dict) -> Dict[str, Any]:
        """Async version of commit"""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        request = {'jsonValues': json.dumps(payload)}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                    f"{self.backend_url}/namespace/{nid}/application/{aid}/configuration/{cid}/commit",
                    json=request,
                    headers=headers
            ) as response:
                return {
                    "version": version,
                    "status_code": response.status,
                    "success": response.status == 200,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }


class SSELoadTester:
    def __init__(self,
                 backend_url: str,
                 sse_base_url: str,
                 namespace_id: str,
                 application_id: str,
                 configuration_id: str,
                 authenticator: KeycloakAuthenticator,
                 username: str,
                 password: str):
        self.global_counter = 0

        self.backend_url = backend_url
        self.sse_base_url = sse_base_url
        self.namespace_id = namespace_id
        self.application_id = application_id
        self.configuration_id = configuration_id
        self.authenticator = authenticator
        self.username = username
        self.password = password

        self.generator = DTOPayloadGenerator()
        self.commit_helper = AsyncCommitHelper(backend_url, self.generator)
        self.results = []

    def get_access_token(self) -> str:
        """Get fresh access token (synchronous wrapper)"""
        token_info = self.authenticator.authenticate(self.username, self.password)
        return token_info["access_token"]

    async def create_connections(self, num_clients: int) -> List[SSEConnection]:
        """Create N SSE connections with their own tokens"""
        connections = []

        # For load testing, we can either:
        # 1. Use same token for all (simpler, tests real limit)
        # 2. Get unique token per client (more realistic)

        # Option 1: Same token (faster, tests notification service limit)
        master_token = self.get_access_token()

        for i in range(num_clients):
            conn = SSEConnection(
                client_id=i,
                namespace_id=self.namespace_id,
                application_id=self.application_id,
                access_token=master_token,  # Same token for all
                sse_base_url=self.sse_base_url
            )
            connections.append(conn)

        return connections

    async def run_test_round(self,
                             connections: List[SSEConnection],
                             payload_size_kb: int,
                             round_num: int) -> Optional[Dict]:
        """
        Run one round: make commit, wait for all connections to receive it
        """
        # Reset received times
        for conn in connections:
            conn.received_time = None

        # Create events for each connection
        events = [asyncio.Event() for _ in connections]

        # Generate unique version for this round
        self.global_counter += 1
        version = f"1.8.{self.global_counter}"

        # Generate payload of specified size
        payload = self.generator.generate_payload(version, payload_size_kb)
        actual_size_bytes = len(json.dumps(payload))

        # Start all SSE listeners
        listen_tasks = []
        for conn, event in zip(connections, events):
            task = asyncio.create_task(conn.connect_and_listen(event, version))
            listen_tasks.append(task)

        # Give connections time to establish
        await asyncio.sleep(1)

        # Trigger commit and record start time
        commit_start = time.time()
        commit_result = await self.commit_helper.commit_dto_version(
            self.namespace_id,
            self.application_id,
            self.configuration_id,
            connections[0].access_token,  # Use first connection's token
            version,
            payload
        )
        commit_end = time.time()
        commit_duration = commit_end - commit_start

        if not commit_result['success']:
            print(f"  ❌ Commit failed with status {commit_result['status_code']}")
            return None

        # Wait for all clients to receive (with timeout based on size)
        timeout = max(30, payload_size_kb / 100)  # Longer timeout for larger payloads
        try:
            await asyncio.wait_for(asyncio.gather(*[event.wait() for event in events]), timeout=timeout)
        except asyncio.TimeoutError:
            timeout_count = sum(1 for event in events if not event.is_set())
            print(f"  ⚠️ Timeout: {timeout_count}/{len(connections)} clients didn't receive")

        # Collect received times
        received_times = [conn.received_time for conn in connections if conn.received_time is not None]

        if not received_times:
            return None

        # Calculate metrics
        first_received = min(received_times)
        last_received = max(received_times)

        # Latency from commit start to each client
        latencies = [(recv - commit_start) * 1000 for recv in received_times]

        # Close all connections for this round
        for task in listen_tasks:
            task.cancel()
        for conn in connections:
            await conn.disconnect()

        return {
            'round': round_num,
            'payload_size_kb': payload_size_kb,
            'actual_size_bytes': actual_size_bytes,
            'total_clients': len(connections),
            'clients_received': len(received_times),
            'received_rate': len(received_times) / len(connections) * 100,
            'commit_duration_ms': commit_duration * 1000,
            'avg_latency_ms': statistics.mean(latencies),
            'median_latency_ms': statistics.median(latencies),
            'p95_latency_ms': statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies),
            'p99_latency_ms': statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies),
            'min_latency_ms': min(latencies),
            'max_latency_ms': max(latencies),
            'first_receiver_delay_ms': (first_received - commit_start) * 1000,
            'last_receiver_delay_ms': (last_received - commit_start) * 1000,  # Key metric
            'timestamp': datetime.utcnow().isoformat()
        }

    async def run_load_test(self,
                            client_counts: List[int],
                            payload_size_kb: int = 1,
                            rounds_per_config: int = 5,
                            delay_between_rounds: float = 2.0):
        """
        Run complete load test with different client counts

        Args:
            client_counts: e.g., [10, 50, 100, 250, 500, 1000]
            payload_size_kb: Size of DTO payload in KB
            rounds_per_config: Number of test rounds per client count
            delay_between_rounds: Seconds to wait between rounds
        """
        all_results = {}

        print(f"\n{'=' * 80}")
        print(f"LOAD TEST CONFIGURATION")
        print(f"{'=' * 80}")
        print(f"Payload size: {payload_size_kb} KB")
        print(f"Rounds per config: {rounds_per_config}")
        print(f"Namespace: {self.namespace_id}")
        print(f"Application: {self.application_id}")
        print(f"SSE URL: {self.sse_base_url}")

        for num_clients in client_counts:
            print(f"\n{'=' * 60}")
            print(f"📊 Testing with {num_clients} simultaneous clients")
            print(f"{'=' * 60}")

            # Create connections once for this test config
            print(f"  Creating {num_clients} SSE connections...")
            connections = await self.create_connections(num_clients)
            round_results = []

            for round_num in range(1, rounds_per_config + 1):
                print(f"  🔄 Round {round_num}/{rounds_per_config}...")
                result = await self.run_test_round(connections, payload_size_kb, round_num)

                if result:
                    round_results.append(result)
                    print(f"    ✅ Received: {result['clients_received']}/{result['total_clients']} "
                          f"({result['received_rate']:.1f}%)")
                    print(f"    📈 Avg latency: {result['avg_latency_ms']:.2f}ms, "
                          f"Last receiver: {result['last_receiver_delay_ms']:.2f}ms")
                else:
                    print(f"    ❌ Round failed")

                if delay_between_rounds > 0 and round_num < rounds_per_config:
                    await asyncio.sleep(delay_between_rounds)

            # Aggregate results for this client count
            if round_results:
                all_results[num_clients] = {
                    'rounds': round_results,
                    'summary': {
                        'avg_latency_ms': statistics.mean([r['avg_latency_ms'] for r in round_results]),
                        'p95_latency_ms': statistics.quantiles([r['avg_latency_ms'] for r in round_results], n=20)[18],
                        'avg_last_receiver_ms': statistics.mean([r['last_receiver_delay_ms'] for r in round_results]),
                        'p95_last_receiver_ms':
                            statistics.quantiles([r['last_receiver_delay_ms'] for r in round_results], n=20)[18],
                        'avg_received_rate': statistics.mean([r['received_rate'] for r in round_results]),
                        'max_commit_duration_ms': max([r['commit_duration_ms'] for r in round_results])
                    }
                }

            # Cleanup
            for conn in connections:
                await conn.disconnect()

            await asyncio.sleep(2)  # Wait before next config

        return all_results

    def print_report(self, results: dict):
        """Pretty print the test results"""
        print("\n" + "=" * 100)
        print("📊 LOAD TEST REPORT")
        print("=" * 100)

        # Table header
        print(f"{'Clients':<10} {'Success %':<10} {'Avg Latency':<15} {'P95 Latency':<15} "
              f"{'Last Recv (avg)':<20} {'Last Recv (p95)':<20}")
        print("-" * 100)

        breaking_point = None
        prev_success = 100

        for num_clients, data in sorted(results.items()):
            summary = data['summary']
            success_rate = summary['avg_received_rate']

            # Mark potential breaking point
            warning = "⚠️ " if success_rate < 95 else "   "

            print(f"{warning}{num_clients:<9} {success_rate:<9.1f}% "
                  f"{summary['avg_latency_ms']:<15.2f} "
                  f"{summary['p95_latency_ms']:<15.2f} "
                  f"{summary['avg_last_receiver_ms']:<20.2f} "
                  f"{summary['p95_last_receiver_ms']:<20.2f}")

            if success_rate < 95 and prev_success >= 95:
                breaking_point = num_clients
            prev_success = success_rate

        # Analysis
        print("\n" + "=" * 100)
        print("📈 ANALYSIS")
        print("=" * 100)

        if breaking_point:
            print(f"⚠️  System starts degrading significantly at {breaking_point} simultaneous clients")
            print(f"   ✅ Recommended max: {breaking_point // 2} clients for stable operation")
        else:
            max_tested = max(results.keys())
            print(f"✅ System stable up to {max_tested} clients (limit not reached)")
            print(f"   💡 Consider testing higher values to find the breaking point")

        # Best performing config
        best_config = min(results.items(),
                          key=lambda x: x[1]['summary']['avg_last_receiver_ms']
                          if x[1]['summary']['avg_received_rate'] > 95 else float('inf'))
        print(f"\n🏆 Best performance: {best_config[0]} clients with "
              f"{best_config[1]['summary']['avg_last_receiver_ms']:.2f}ms avg last receiver latency")

    def save_results(self, results: dict, filename: str = "sse_load_test_results.json"):
        """Save results to JSON file"""
        serializable_results = {}
        for k, v in results.items():
            serializable_results[str(k)] = {
                'summary': v['summary'],
                'rounds': [
                    {key: val for key, val in round.items()
                     if isinstance(val, (int, float, str, bool, type(None)))}
                    for round in v['rounds']
                ]
            }

        with open(filename, 'w') as f:
            json.dump(serializable_results, f, indent=2)
        print(f"\n💾 Results saved to {filename}")


async def main():
    # Configuration
    KEYCLOAK_URL = "http://XXX:8080"
    REALM = "rtcms4j"
    CLIENT_ID = "rtcms4j-web"
    BACKEND_URL = "http://XXX:8000/core/api/v1"
    SSE_BASE_URL = "http://XXX:8000/notify/api/v1"

    USERNAME = "admin"
    PASSWORD = "admin"

    NAMESPACE_ID = "1"
    APPLICATION_ID = "1"
    CONFIGURATION_ID = "1"

    # Test parameters
    PAYLOAD_SIZE_KB = 50  # Start with small payload
    CLIENT_COUNTS = [10, 50, 100, 250, 500]
    # CLIENT_COUNTS = [10, 50, 100, 250, 500, 1000]
    ROUNDS_PER_CONFIG = 3  # Number of test rounds per client count

    # Initialize
    generator = DTOPayloadGenerator()
    authenticator = KeycloakAuthenticator(KEYCLOAK_URL, REALM, CLIENT_ID, None)

    # Create load tester
    tester = SSELoadTester(
        backend_url=BACKEND_URL,
        sse_base_url=SSE_BASE_URL,
        namespace_id=NAMESPACE_ID,
        application_id=APPLICATION_ID,
        configuration_id=CONFIGURATION_ID,
        authenticator=authenticator,
        username=USERNAME,
        password=PASSWORD
    )

    # Run the test
    results = await tester.run_load_test(
        client_counts=CLIENT_COUNTS,
        payload_size_kb=PAYLOAD_SIZE_KB,
        rounds_per_config=ROUNDS_PER_CONFIG,
        delay_between_rounds=2.0
    )

    # Print report
    tester.print_report(results)

    # Save results
    tester.save_results(results)


if __name__ == "__main__":
    import math  # For the generator

    asyncio.run(main())
