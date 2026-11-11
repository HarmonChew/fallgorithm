// net.hpp's net_finish: the value network after its first layer. Its own translation unit
// built with -ffp-contract=off (CMakeLists.txt), so it does the arithmetic the earlier
// row-by-row loop in net.cpp compiled to (GCC, -O3 -march=native -ffp-contract=fast): each
// second-layer sum adds its rounded products in input order, except the last ``hidden % 4``
// inputs, which that loop's scalar remainder fused (std::fma here). Every network so far has
// hidden 256, so no input is fused.
#include "net.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>

namespace fallgorithm {

float net_finish(const ValueNetwork& net, const float* h) {
    const int n = net.hidden, m = net.hidden2;
    thread_local std::vector<float> sums;
    sums.assign(net.b2.begin(), net.b2.end());
    float* total = sums.data();
    const int fused_from = n - n % 4;
    for (int k = 0; k < n; ++k) {
        const float x = std::max(h[k], 0.0f);
        if (x == 0.0f) {
            // x * w is a zero; adding it leaves a sum as it is (all weights are finite, and
            // no sum is -0: no network has a zero bias in b2)
            continue;
        }
        const float* row = &net.w2t[static_cast<std::size_t>(k) * m];
        if (k < fused_from) {
            for (int j = 0; j < m; ++j) {
                total[j] += row[j] * x;
            }
        } else {
            for (int j = 0; j < m; ++j) {
                total[j] = std::fma(row[j], x, total[j]);
            }
        }
    }
    float out = net.b3;
    for (int j = 0; j < m; ++j) {
        out += net.w3[j] * std::max(total[j], 0.0f);
    }
    return out;
}

}  // namespace fallgorithm
