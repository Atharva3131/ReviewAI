import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from app.main import app

def test_runtime():
    client = TestClient(app)
    
    # 1. Test /health
    res_health = client.get("/health")
    print("/health status:", res_health.status_code, res_health.json())
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"

    # 2. Test /ready
    res_ready = client.get("/ready")
    print("/ready status:", res_ready.status_code, res_ready.json())
    assert res_ready.status_code == 200

    # 3. Test demo review ingestion
    res_demo = client.post(
        "/api/v1/demo/ingest-demo-review",
        json={
            "customer_name": "Jane Doe",
            "rating": 1,
            "review_text": "The service was terrible and product broke on arrival!"
        }
    )
    print("/ingest-demo-review status:", res_demo.status_code)
    if res_demo.status_code == 200:
        print("Demo response:", res_demo.json())
    else:
        print("Demo error:", res_demo.text)
    assert res_demo.status_code == 200

    print("\n[OK] ALL RUNTIME ENDPOINT TESTS PASSED!")

if __name__ == "__main__":
    test_runtime()
