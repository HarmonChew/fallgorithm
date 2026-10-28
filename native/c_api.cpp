// The C entry points src/block_stack_ai/native.py loads with ctypes.
//
// Bad arguments return -1 instead of reaching undefined behaviour, because the
// tests call these with generated input.
#include <cstdint>
#include <vector>

#include "board.hpp"
#include "eval.hpp"
#include "reach.hpp"

#if defined(_WIN32)
#define FN_API extern "C" __declspec(dllexport)
#else
#define FN_API extern "C" __attribute__((visibility("default")))
#endif

using namespace fallgorithm;

namespace {

constexpr int abi_version = 2;

Columns load_columns(const std::uint32_t* columns) {
    Columns out{};
    for (int index = 0; index < width; ++index) {
        out[index] = columns[index];
    }
    return out;
}

bool placement_in_bounds(int piece, int orientation, int x, int y) {
    if (piece < 0 || piece >= piece_types || orientation < 0 ||
        orientation >= orientation_counts[piece]) {
        return false;
    }
    for (const Cell& cell : shapes[piece][orientation]) {
        const int column = x + cell.dx;
        const int row = y + cell.dy + hidden_rows;
        if (column < 0 || column >= width || row < 0 || row >= grid_rows) {
            return false;
        }
    }
    return true;
}

}  // namespace

FN_API int fn_abi_version() { return abi_version; }

FN_API int fn_params_size() { return static_cast<int>(sizeof(Params)); }

// Writes the settled board to ``out`` and returns the cleared rows, or -1.
FN_API int fn_settle(const std::uint32_t* columns, int piece, int orientation, int x, int y,
                     std::uint32_t* out) {
    if (!placement_in_bounds(piece, orientation, x, y)) {
        return -1;
    }
    const Settled settled = settle(load_columns(columns), piece, orientation, x, y);
    for (int index = 0; index < width; ++index) {
        out[index] = settled.columns[index];
    }
    return settled.cleared;
}

FN_API double fn_value(const Params* params, int phase, int cleared,
                       const std::uint32_t* columns) {
    return value_of(*params, phase, cleared, load_columns(columns));
}

FN_API int fn_phase(const Params* params, int level, int drought, const std::uint32_t* columns) {
    return phase_of(*params, level, drought, load_columns(columns));
}

FN_API int fn_level_for_lines(int lines, int start_level) {
    if (start_level < 0 || start_level >= 20 || lines < 0) {
        return -1;
    }
    return level_for_lines(lines, start_level);
}

// Writes the gravity period and rows per tick; returns 0, or -1.
FN_API int fn_gravity(int level, int double_killscreen, int* period, int* rows) {
    if (level < 0) {
        return -1;
    }
    *period = gravity_period(level);
    *rows = gravity_rows(level, double_killscreen != 0);
    return 0;
}

// Every placement reach.reachable finds, in its order, with each one's masks.
// ``flight`` is (orientation, x, y, gravity_counter, first_delay, shift_wait,
// rotate_wait). ``placements`` receives (orientation, x, y) per placement and
// ``masks`` all the masks back to back, ``mask_lengths`` saying how many each.
// Returns the count, -1 for bad arguments, -2 if a buffer is too small, -3 if the
// walk back lost its path.
FN_API int fn_reach(const std::uint32_t* columns, int piece, const int* flight, int period,
                    int rows, int interval, int* placements, int capacity, std::uint8_t* masks,
                    int mask_capacity, int* mask_lengths) {
    if (piece < 0 || piece >= piece_types || flight[0] < 0 ||
        flight[0] >= orientation_counts[piece] || flight[1] < -1 || flight[1] > width ||
        flight[2] < 0 || flight[2] >= grid_rows || flight[3] < 0 || flight[4] < 0 ||
        flight[5] < 0 || flight[6] < 0 || period < 1 || rows < 1 || rows > 2 || interval < 1) {
        return -1;
    }
    // Reused across calls, as the search reuses its own, so the tests also check
    // that every run starts from a clean state.
    thread_local ReachSearch search;
    search.run(load_columns(columns), piece,
               Flight{flight[0], flight[1], flight[2], flight[3], flight[4], flight[5], flight[6]},
               period, rows, interval);
    const int count = static_cast<int>(search.placements.size());
    if (count > capacity) {
        return -2;
    }
    std::vector<std::uint8_t> found;
    int used = 0;
    for (int index = 0; index < count; ++index) {
        const Reach& placement = search.placements[index];
        if (!search.masks(placement, found)) {
            return -3;
        }
        const int length = static_cast<int>(found.size());
        if (used + length > mask_capacity) {
            return -2;
        }
        placements[3 * index] = placement.orientation;
        placements[3 * index + 1] = placement.x;
        placements[3 * index + 2] = placement.y;
        mask_lengths[index] = length;
        for (int k = 0; k < length; ++k) {
            masks[used + k] = found[k];
        }
        used += length;
    }
    return count;
}
