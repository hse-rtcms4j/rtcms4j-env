import json
import random
import string
from typing import Dict, Any, List


class DTOPayloadGenerator:
    def __init__(self):
        self.enum_values = ["GRASS", "DIRT"]

    def _generate_string(self, min_len: int = 5, max_len: int = 20) -> str:
        length = random.randint(min_len, max_len)
        return ''.join(random.choices(string.ascii_letters, k=length))

    def _generate_array(self, item_type: str, target_size_bytes: int, current_total_bytes: int) -> List:
        array = []
        estimated_item_size = 0

        # Estimate bytes per item based on type
        if item_type == "string":
            test_item = self._generate_string()
            estimated_item_size = len(json.dumps(test_item)) + 1  # +1 for comma
        elif item_type in ["integer", "boolean"]:
            test_item = random.randint(0, 1000) if item_type == "integer" else random.choice([True, False])
            estimated_item_size = len(str(test_item)) + 1
        elif item_type == "number":
            test_item = round(random.uniform(0, 1000), 2)
            estimated_item_size = len(str(test_item)) + 1

        # Calculate how many items we need
        needed_bytes = target_size_bytes - current_total_bytes
        num_items = max(1, needed_bytes // max(1, estimated_item_size))

        # Generate array
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
            import math
            times = max(1, round(math.log2(target_bytes)))
            # times = max(1, round(math.log2(target_bytes) * 10))
            while current_bytes < target_bytes:
                payload["stringList"].extend([self._generate_string(20, 100) for _ in range(times)])

                # Recalculate current size
                current_bytes = len(json.dumps(payload))
                print(f"Progress: {current_bytes/target_bytes*100:.1f}")

            print(f"  Final size: {current_bytes} bytes (target: {target_bytes})")

        return payload


import requests
from typing import Dict, Optional


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

    def refresh_token(self, refresh_token: str) -> Dict[str, str]:
        data = {
            "client_id": self.client_id,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }

        if self.client_secret:
            data["client_secret"] = self.client_secret

        response = requests.post(self.token_url, data=data)
        response.raise_for_status()

        return response.json()


import requests
import json
from typing import List, Dict, Any
from datetime import datetime
import statistics


class DTOTester:
    def __init__(self, backend_url: str, generator: DTOPayloadGenerator):
        self.backend_url = backend_url
        self.generator = generator
        self.results: List[Dict] = []

    def commit_dto_version(self,
                           nid: str, aid: str, cid: str,
                           access_token: str,
                           version: str,
                           payload: dict) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        request = {'jsonValues': json.dumps(payload)}
        response = requests.post(f"{self.backend_url}/namespace/{nid}/application/{aid}/configuration/{cid}/commit",
                                 json=request, headers=headers)

        timestamp = datetime.utcnow().isoformat() + "Z"
        return {
            "version": version,
            "status_code": response.status_code,
            "timestamp": timestamp,
            "success": response.status_code == 201
        }


def main():
    KEYCLOAK_URL = "http://XXX:8080"
    REALM = "rtcms4j"
    CLIENT_ID = "rtcms4j-web"
    BACKEND_URL = "http://XXX:8000/core/api/v1"
    USERNAME = "admin"
    PASSWORD = "admin"

    SIZES_KB = [1, 500, 1 * 1024, 5 * 1024, 10 * 1024]
    # SIZES_KB = [10 * 1024]
    REPETITIONS_PER_SIZE = 30

    generator = DTOPayloadGenerator()
    authenticator = KeycloakAuthenticator(KEYCLOAK_URL, REALM, CLIENT_ID, None)
    tester = DTOTester(BACKEND_URL, generator)

    token_info = authenticator.authenticate(USERNAME, PASSWORD)
    access_token = token_info["access_token"]

    counter = 550
    for size_kb in SIZES_KB:
        print(f"\nPreparing {size_kb}KB template...")
        payload = generator.generate_payload('1.0.0', size_kb)
        actual_size_bytes = len(json.dumps(payload))
        print(f"\nReady to test {size_kb}KB payloads! ({REPETITIONS_PER_SIZE} repetitions)")

        for att in range(REPETITIONS_PER_SIZE):
            input('Press to proceed...')
            counter += 1
            version = f'1.0.{counter}'
            payload["version"] = version

            result = tester.commit_dto_version('1', '1', '1', access_token, version, payload)
            result["target_size_kb"] = size_kb
            result["actual_size_bytes"] = actual_size_bytes
            print(result)


if __name__ == "__main__":
    main()
