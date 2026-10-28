// The C entry points src/block_stack_ai/native.py loads with ctypes.
//
// Bad arguments return -1 instead of reaching undefined behaviour, because the
// tests call these with generated input.
#include <cstdint>

#include "board.hpp"
#include "eval.hpp"

#if defined(_WIN32)
#define FN_API extern "C" __declspec(dllexport)
#else
#define FN_API extern "C" __attribute__((visibility("default")))
#endif

using namespace fallgorithm;

namespace {

constexpr int abi_version = 1;

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
