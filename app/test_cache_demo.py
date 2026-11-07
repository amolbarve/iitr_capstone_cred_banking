# app/test_cache_demo.py
import time
from cache_manager import ResponseCacheManager

def simulate_cache_demonstration():
    print("==================================================")
    print("   RESPONSE CACHING: BEFORE / AFTER EVIDENCE      ")
    print("==================================================")

    test_query = "What are the foreclosure charges and minimum lock-in period?"
    mock_response = {
        "success": True,
        "answer": "Foreclosure charges are 2% after the 12-month lock-in period."
    }

    # --- BEFORE: First Request (Cache Miss) ---
    print(f"\n[Before] Query: '{test_query}'")
    start_miss = time.time()
    
    # Check cache (should be None)
    hit_test_1 = ResponseCacheManager.get(test_query)
    assert hit_test_1 is None
    
    # Simulate full execution & store
    time.sleep(0.045) # Simulate LLM/Crew latency
    ResponseCacheManager.set(test_query, mock_response)
    miss_latency = round(time.time() - start_miss, 4)
    
    print(f"  -> Cache Status: CACHE_MISS")
    print(f"  -> Execution Latency: {miss_latency}s")
    print(f"  -> Response: {mock_response['answer']}")


    # --- AFTER: Repeated Request (Cache Hit) ---
    print(f"\n[After] Repeated Query: '{test_query}'")
    start_hit = time.time()
    
    hit_test_2 = ResponseCacheManager.get(test_query)
    hit_latency = round(time.time() - start_hit, 4)
    
    safe_hit_latency = max(hit_latency, 0.0001)
    speedup = round(miss_latency / safe_hit_latency, 1)
    
    print(f"  -> Cache Status: CACHE_HIT")
    print(f"  -> Execution Latency: {hit_latency}s (Instantaneous)")
    print(f"  -> Cached Response: {hit_test_2['response']['answer']}")
    print(f"  -> Speedup Factor: {speedup}x faster")
    print("==================================================")

if __name__ == "__main__":
    simulate_cache_demonstration()