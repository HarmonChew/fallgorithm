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

struct ValueNetwork {
    int hidden = 0, hidden2 = 0;
    std::vector<float> w1, b1, w2, b2, w3;  // w1: one row of ``hidden`` per input
    float b3 = 0.0f;

    // experiment020.export's bytes. Returns false if they are not a network for
    // net_inputs inputs.
    bool load(const unsigned char* data, std::size_t size);
};

// The network's output for one settled board (``columns`` with the hidden rows, which
// it does not read): its 18 board features (value.hpp's, computed by the caller so this
// translation unit holds no code shared with the exact ones), the speed band (0-3), the
// lines left before the cap, the drought and the piece that left it (-1: none).
double net_forward(const ValueNetwork& net, const Columns& columns, const double* features,
                   int band, int lines_left, int drought, int last);

}  // namespace fallgorithm
