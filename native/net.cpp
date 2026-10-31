// native/net.hpp's network. Built with its own flags (CMakeLists.txt); see net.hpp.
#include "net.hpp"

#include <algorithm>
#include <bit>
#include <cstring>


namespace fallgorithm {

bool ValueNetwork::load(const unsigned char* data, std::size_t size, std::int32_t magic,
                        int inputs) {
    std::int32_t header[4];
    if (!data || size < sizeof(header)) {
        return false;
    }
    std::memcpy(header, data, sizeof(header));
    if (header[0] != magic || header[1] != inputs || header[2] < 1 || header[3] < 1) {
        return false;
    }
    hidden = header[2];
    hidden2 = header[3];
    const std::size_t sizes[] = {static_cast<std::size_t>(inputs) * hidden,
                                 static_cast<std::size_t>(hidden),
                                 static_cast<std::size_t>(hidden) * hidden2,
                                 static_cast<std::size_t>(hidden2),
                                 static_cast<std::size_t>(hidden2), 1};
    std::size_t total = 0;
    for (std::size_t part : sizes) {
        total += part;
    }
    if (size != sizeof(header) + total * sizeof(float)) {
        return false;
    }
    const unsigned char* at = data + sizeof(header);
    std::vector<float>* parts[] = {&w1, &b1, &w2, &b2, &w3};
    for (int index = 0; index < 5; ++index) {
        parts[index]->resize(sizes[index]);
        std::memcpy(parts[index]->data(), at, sizes[index] * sizeof(float));
        at += sizes[index] * sizeof(float);
    }
    std::memcpy(&b3, at, sizeof(float));
    return true;
}

namespace {

// h += x * row, for one first-layer input.
inline void add_row(float* h, const float* row, float x, int n) {
    for (int k = 0; k < n; ++k) {
        h[k] += x * row[k];
    }
}

// The first layer's biases plus the filled cells' rows (only those add theirs).
void start(const ValueNetwork& net, const Columns& columns, std::vector<float>& h) {
    const int n = net.hidden;
    h.assign(net.b1.begin(), net.b1.end());
    for (int column = 0; column < width; ++column) {
        std::uint32_t visible = columns[column] >> hidden_rows;
        while (visible) {
            const int row = std::countr_zero(visible);
            visible &= visible - 1;
            add_row(h.data(), &net.w1[static_cast<std::size_t>(row * width + column) * n], 1.0f, n);
        }
    }
}

// The rest of the network from the first layer's sums ``h`` (made ReLU here).
float finish(const ValueNetwork& net, float* h) {
    const int n = net.hidden;
    for (int k = 0; k < n; ++k) {
        h[k] = std::max(h[k], 0.0f);
    }
    float out = net.b3;
    for (int j = 0; j < net.hidden2; ++j) {
        const float* row = &net.w2[static_cast<std::size_t>(j) * n];
        float total = net.b2[j];
        for (int k = 0; k < n; ++k) {
            total += row[k] * h[k];
        }
        out += net.w3[j] * std::max(total, 0.0f);
    }
    return out;
}

}  // namespace

double net_forward(const ValueNetwork& net, const Columns& columns, const double* features,
                   int band, int lines_left, int drought, int last) {
    const int n = net.hidden;
    thread_local std::vector<float> h;
    start(net, columns, h);
    int at = net_cells;
    for (int k = 0; k < 18; ++k) {
        if (features[k] != 0.0) {
            add_row(h.data(), &net.w1[static_cast<std::size_t>(at + k) * n],
                    static_cast<float>(features[k]), n);
        }
    }
    at += 18;
    add_row(h.data(), &net.w1[static_cast<std::size_t>(at + band) * n], 1.0f, n);
    at += 4;
    add_row(h.data(), &net.w1[static_cast<std::size_t>(at) * n],
            static_cast<float>(lines_left) / 100.0f, n);
    add_row(h.data(), &net.w1[static_cast<std::size_t>(at + 1) * n], static_cast<float>(drought), n);
    if (last >= 0) {
        add_row(h.data(), &net.w1[static_cast<std::size_t>(at + 2 + last) * n], 1.0f, n);
    }
    return finish(net, h.data());
}

double rank_forward(const ValueNetwork& net, const Columns& columns, const float* dense) {
    thread_local std::vector<float> h;
    start(net, columns, h);
    for (int k = 0; k < rank_dense; ++k) {
        if (dense[k] != 0.0f) {
            add_row(h.data(), &net.w1[static_cast<std::size_t>(net_cells + k) * net.hidden],
                    dense[k], net.hidden);
        }
    }
    return finish(net, h.data());
}

}  // namespace fallgorithm
