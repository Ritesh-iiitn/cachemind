import pytest
from backend.app.inference.kv_experiments import KVAttentionBenchmark

def test_kv_attention_speedup():
    res = KVAttentionBenchmark.run_kv_comparison(
        prompt_tokens=512,
        generated_tokens=64,
        hidden_dim=2048,
        num_heads=16
    )
    assert res["parameters"]["prompt_tokens"] == 512
    assert res["comparison"]["decode_speedup_factor"] > 1.0
    assert res["comparison"]["memory_bandwidth_saved_pct"] > 50.0
    assert res["kv_cached_attention"]["tokens_per_second"] > res["naive_attention"]["tokens_per_second"]
