// Experiment 020's value network: the points a settled board will still score, in
// Tetrises at level 18, read by a small multi-layer network (experiment020.ValueNet).
//
// No Python copy: experiment020.export writes the weights (normalisation folded into the
// first layer) and tests/test_experiment020.py checks the values against PyTorch. The
// arithmetic is in net.cpp, its own translation unit with its own flags (float32, fused
// multiply-adds allowed); a fixed summation order keeps it deterministic for one binary.
#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

#include "board.hpp"

namespace fallgorithm {

// experiment020.INPUTS: 200 cells (row by row from the top), 18 board features, the
// speed band (18, 19-28, 29-38, 39+), lines left / 100, drought, last piece one-hot.
constexpr int net_cells = width * height;
constexpr int net_inputs = net_cells + 18 + 4 + 1 + 1 + piece_types;
constexpr std::int32_t net_magic = 0x30323046;

// Experiment 021's rank network (experiment021.RankNet), the same shape: the 200 cells,
// then rank_dense numbers rollout.hpp's rank_inputs writes.
constexpr int rank_dense = 47;
constexpr int rank_inputs_count = net_cells + rank_dense;
constexpr std::int32_t rank_magic = 0x31323046;

struct ValueNetwork {
    int hidden = 0, hidden2 = 0;
    std::vector<float> w1, b1, w2, b2, w3;  // w1: one row of ``hidden`` per input
    std::vector<float> w2t;  // w2 transposed by load: one row of ``hidden2`` per hidden unit
    float b3 = 0.0f;

    // experiment020.export's bytes. Returns false if they are not a network for
    // net_inputs inputs.
    bool load(const unsigned char* data, std::size_t size) {
        return load(data, size, net_magic, net_inputs);
    }
    // An export with this ``magic`` and ``inputs`` (Experiment 021: rank_magic,
    // rank_inputs_count).
    bool load(const unsigned char* data, std::size_t size, std::int32_t magic, int inputs);
};

// The network's output for one settled board (``columns`` with the hidden rows, which
// it does not read): its 18 board features (value.hpp's, computed by the caller so this
// translation unit holds no code shared with the exact ones), the speed band (0-3), the
// lines left before the cap, the drought and the piece that left it (-1: none).
double net_forward(const ValueNetwork& net, const Columns& columns, const double* features,
                   int band, int lines_left, int drought, int last);

// Experiment 021: the rank network's output for one candidate's settled board and its
// rank_dense other inputs.
double rank_forward(const ValueNetwork& net, const Columns& columns, const float* dense);

// The network after the first layer: ReLU of the first layer's sums ``h``, the second
// layer, its ReLU and the output. In net_layer2.cpp: each second-layer sum adds its products
// in input order with the rounding net.cpp's original row-by-row loop had, but many sums at
// once from w2t (the vector width -march=native gives) and skipping inputs the ReLU made 0,
// which add only zeros. The values are bit for bit the same (checked on 400,000 values and
// 12 stored games, 2026-11-11), 3.6-4.5x faster for a whole game.
float net_finish(const ValueNetwork& net, const float* h);

}  // namespace fallgorithm
