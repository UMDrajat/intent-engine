import requests


def verify_expansion():
    url = "http://localhost:8082/api/v1/search"
    payload = {"query": "learning golang generics", "limit": 3}
    r = requests.post(url, json=payload, timeout=30)
    data = r.json()

    print("=== Search Response Verification ===")
    print(f"Query: {data.get('query')}")
    print(f"Topics Expanded: {data.get('topics_expanded')}")
    print(f"URLs Added to Queue: {data.get('urls_added_to_queue')}")
    print(f"Total Results: {data.get('total_results')}")

    print("\n--- Ranking Verification ---")
    results = data.get("results", [])
    for i, res in enumerate(results, 1):
        source = res.get("source")
        title = res.get("title")
        score = res.get("score", 0)
        alignment = res.get("alignment_score", {}).get("total_score", 0)
        print(f" {i}. [{source}] {title}")
        print(f"    Score: {score:.4f}, Alignment: {alignment:.4f}")


if __name__ == "__main__":
    verify_expansion()
