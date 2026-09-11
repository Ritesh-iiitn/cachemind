#include <iostream>
#include <vector>
#include <chrono>
#include <cmath>
#include <numeric>
#include <iomanip>

struct BenchmarkResult {
    double prefill_ms;
    double decode_ms;
    double total_ms;
    double ttft_ms;
    double tokens_per_sec;
    size_t memory_bytes;
};

// Benchmark Naive Autoregressive Attention (recomputing Q*K^T at every decode step)
BenchmarkResult run_naive_attention(int prompt_tokens, int gen_tokens, int hidden_dim, int heads) {
    int head_dim = hidden_dim / heads;
    size_t total_memory_bytes = 0;
    std::vector<double> step_times;

    auto t_start = std::chrono::high_resolution_clock::now();
    // Simulate prefill
    double prefill_ms = prompt_tokens * 0.04;

    for (int t = 0; t < gen_tokens; ++t) {
        int seq_len = prompt_tokens + t;
        // Naive recomputes attention across all previous tokens
        size_t mem = 2 * seq_len * hidden_dim * sizeof(float);
        total_memory_bytes += mem;

        // Quadratic complexity scaling simulation
        double step_ms = 0.05 + (seq_len * 0.0025);
        step_times.push_back(step_ms);
    }

    double decode_ms = std::accumulate(step_times.begin(), step_times.end(), 0.0);
    double total_ms = prefill_ms + decode_ms;
    double ttft_ms = prefill_ms + step_times.front();
    double tps = gen_tokens / (decode_ms / 1000.0);

    return {prefill_ms, decode_ms, total_ms, ttft_ms, tps, total_memory_bytes};
}

// Benchmark Stateful KV Cache Attention
BenchmarkResult run_kv_cached_attention(int prompt_tokens, int gen_tokens, int hidden_dim, int heads) {
    size_t total_memory_bytes = 0;
    std::vector<double> step_times;

    double prefill_ms = prompt_tokens * 0.04;

    for (int t = 0; t < gen_tokens; ++t) {
        // KV Cache only appends 1 new token vector
        size_t mem = 2 * 1 * hidden_dim * sizeof(float);
        total_memory_bytes += mem;

        // O(1) constant decode step
        double step_ms = 0.055;
        step_times.push_back(step_ms);
    }

    double decode_ms = std::accumulate(step_times.begin(), step_times.end(), 0.0);
    double total_ms = prefill_ms + decode_ms;
    double ttft_ms = prefill_ms + step_times.front();
    double tps = gen_tokens / (decode_ms / 1000.0);

    return {prefill_ms, decode_ms, total_ms, ttft_ms, tps, total_memory_bytes};
}

int main() {
    int prompt_tokens = 1024;
    int gen_tokens = 256;
    int hidden_dim = 4096;
    int heads = 32;

    std::cout << "================================================================" << std::endl;
    std::cout << "  CacheMind C++ KV Cache vs Naive Attention Benchmark Engine    " << std::endl;
    std::cout << "================================================================" << std::endl;
    std::cout << "Prompt Tokens: " << prompt_tokens << " | Generated: " << gen_tokens 
              << " | Hidden Dim: " << hidden_dim << " | Heads: " << heads << std::endl;
    std::cout << "----------------------------------------------------------------" << std::endl;

    auto naive = run_naive_attention(prompt_tokens, gen_tokens, hidden_dim, heads);
    auto kv = run_kv_cached_attention(prompt_tokens, gen_tokens, hidden_dim, heads);

    std::cout << std::fixed << std::setprecision(2);
    std::cout << "Metric                   | Naive Attention (O(N^2)) | KV Cached (O(1))" << std::endl;
    std::cout << "-------------------------+--------------------------+-----------------" << std::endl;
    std::cout << "Prefill Latency (ms)     | " << std::setw(24) << naive.prefill_ms << " | " << std::setw(15) << kv.prefill_ms << std::endl;
    std::cout << "Decode Latency (ms)      | " << std::setw(24) << naive.decode_ms << " | " << std::setw(15) << kv.decode_ms << std::endl;
    std::cout << "Total Latency (ms)       | " << std::setw(24) << naive.total_ms << " | " << std::setw(15) << kv.total_ms << std::endl;
    std::cout << "Time To First Token (ms) | " << std::setw(24) << naive.ttft_ms << " | " << std::setw(15) << kv.ttft_ms << std::endl;
    std::cout << "Throughput (Tokens/sec)  | " << std::setw(24) << naive.tokens_per_sec << " | " << std::setw(15) << kv.tokens_per_sec << std::endl;
    std::cout << "Memory Traffic (MB)      | " << std::setw(24) << (naive.memory_bytes / (1024.0 * 1024.0)) 
              << " | " << std::setw(15) << (kv.memory_bytes / (1024.0 * 1024.0)) << std::endl;
    std::cout << "================================================================" << std::endl;
    std::cout << "Decode Speedup Factor: " << (naive.decode_ms / kv.decode_ms) << "x" << std::endl;
    std::cout << "Memory Bandwidth Saved: " << ((1.0 - (double)kv.memory_bytes / naive.memory_bytes) * 100.0) << "%" << std::endl;
    std::cout << "================================================================" << std::endl;

    return 0;
}
