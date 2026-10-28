// The board model of the Python agent, in C++.
//
// A board is ten column bitmasks, exactly as pathaware.grid_columns builds them:
// bit r of a column is model row r, row 0 at the top. Rows 0-1 are the engine's
// two hidden rows and rows 2-21 the twenty visible ones. Every function here is a
// line-by-line translation of the Python one named beside it.
#pragma once

#include <algorithm>
#include <array>
#include <bit>
#include <cstdint>
#include <cstdlib>

namespace fallgorithm {

constexpr int width = 10;
constexpr int height = 20;
constexpr int hidden_rows = 2;
constexpr int grid_rows = hidden_rows + height;
constexpr std::uint32_t visible_mask = ((1u << grid_rows) - 1) ^ ((1u << hidden_rows) - 1);
constexpr std::uint32_t hidden_mask = (1u << hidden_rows) - 1;
constexpr int well_column = width - 1;  // wellplan.WELL_COLUMN
constexpr int reserve_cap = 4;          // wellplan.RESERVE_CAP

using Columns = std::array<std::uint32_t, width>;

// pieces.PIECES order, which is also the engine's Piece enum order.
enum Piece : int { I, J, L, O, S, T, Z };
constexpr int piece_types = 7;

struct Cell {
    int dx, dy;
};

// pieces._SHAPES: offsets from the piece origin; orientation 0 is the spawn
// orientation, each next one a clockwise turn.
constexpr int orientation_counts[piece_types] = {2, 4, 4, 1, 2, 4, 2};
constexpr Cell shapes[piece_types][4][4] = {
    {{{-2, 0}, {-1, 0}, {0, 0}, {1, 0}}, {{0, -2}, {0, -1}, {0, 0}, {0, 1}}},
    {{{-1, 0}, {0, 0}, {1, 0}, {1, 1}}, {{0, -1}, {0, 0}, {-1, 1}, {0, 1}},
     {{-1, -1}, {-1, 0}, {0, 0}, {1, 0}}, {{0, -1}, {1, -1}, {0, 0}, {0, 1}}},
    {{{-1, 0}, {0, 0}, {1, 0}, {-1, 1}}, {{-1, -1}, {0, -1}, {0, 0}, {0, 1}},
     {{1, -1}, {-1, 0}, {0, 0}, {1, 0}}, {{0, -1}, {0, 0}, {0, 1}, {1, 1}}},
    {{{-1, 0}, {0, 0}, {-1, 1}, {0, 1}}},
    {{{0, 0}, {1, 0}, {-1, 1}, {0, 1}}, {{0, -1}, {0, 0}, {1, 0}, {1, 1}}},
    {{{-1, 0}, {0, 0}, {1, 0}, {0, 1}}, {{0, -1}, {-1, 0}, {0, 0}, {0, 1}},
     {{-1, 0}, {0, 0}, {1, 0}, {0, -1}}, {{0, -1}, {0, 0}, {1, 0}, {0, 1}}},
    {{{-1, 0}, {0, 0}, {0, 1}, {1, 1}}, {{1, -1}, {0, 0}, {1, 0}, {0, 1}}},
};

// pathaware.GRAVITY_PERIOD and FIRST_TRANSITION_LINES (core/src/rules.cpp).
constexpr int gravity_periods[30] = {48, 43, 38, 33, 28, 23, 18, 13, 8, 6, 5, 5, 5, 4, 4,
                                     4,  3,  3,  3,  2,  2,  2,  2,  2, 2, 2, 2, 2, 2, 1};
constexpr int first_transition_lines[20] = {10,  20,  30,  40,  50,  60,  70,
                                            80,  90,  100, 100, 100, 100, 100,
                                            100, 100, 110, 120, 130, 140};
constexpr int double_gravity_level = 39;  // limits.DOUBLE_GRAVITY_LEVEL

// pathaware.gravity_period
inline int gravity_period(int level) { return gravity_periods[level < 29 ? level : 29]; }

// limits.gravity: rows tried per gravity tick.
inline int gravity_rows(int level, bool double_killscreen) {
    return double_killscreen && level >= double_gravity_level ? 2 : 1;
}

// pathaware.level_for_lines for an endless game without wrapping (the benchmark).
inline int level_for_lines(int lines, int start_level) {
    const int threshold = first_transition_lines[start_level];
    if (lines < threshold) {
        return start_level;
    }
    return start_level + 1 + (lines - threshold) / 10;
}

struct Settled {
    Columns columns;
    int cleared;
};

// pathaware.settle_columns: lock a piece, then clear full visible rows. Only the
// visible rows compact; the hidden rows are carried over untouched.
inline Settled settle(const Columns& columns, int piece, int orientation, int x, int y) {
    Settled out{columns, 0};
    for (const Cell& cell : shapes[piece][orientation]) {
        out.columns[x + cell.dx] |= 1u << (y + cell.dy + hidden_rows);
    }
    std::uint32_t common = out.columns[0];
    for (int index = 1; index < width; ++index) {
        common &= out.columns[index];
    }
    std::uint32_t full = common & visible_mask;
    if (!full) {
        return out;
    }
    out.cleared = std::popcount(full);
    while (full) {  // top row first, as the Python list is
        const int row = std::countr_zero(full);
        full &= full - 1;
        const std::uint32_t low = ((1u << row) - 1) & visible_mask;
        const std::uint32_t high = ~((1u << (row + 1)) - 1);
        for (std::uint32_t& column : out.columns) {
            column = (column & hidden_mask) | (column & high) | ((column & low) << 1);
        }
    }
    return out;
}

// wellplan.column_heights for one column: from its topmost visible cell.
inline int column_height(std::uint32_t column) {
    const std::uint32_t visible = column >> hidden_rows;
    return visible ? height - std::countr_zero(visible) : 0;
}

inline std::array<int, width> column_heights(const Columns& columns) {
    std::array<int, width> heights{};
    for (int index = 0; index < width; ++index) {
        heights[index] = column_height(columns[index]);
    }
    return heights;
}

// wellplan.stack_height
inline int stack_height(const Columns& columns) {
    int tallest = 0;
    for (std::uint32_t column : columns) {
        tallest = std::max(tallest, column_height(column));
    }
    return tallest;
}

// The covered empty visible cells of one column.
inline int column_holes(std::uint32_t column) {
    const std::uint32_t visible = column >> hidden_rows;
    if (!visible) {
        return 0;
    }
    const int top = std::countr_zero(visible);
    return (height - top) - std::popcount(visible >> top);
}

// heuristic.BoardFeatures
struct Features {
    int holes, aggregate_height, bumpiness, max_height;
};

// pathaware.column_features: all ten columns.
inline Features column_features(const Columns& columns) {
    const auto heights = column_heights(columns);
    Features f{0, 0, 0, 0};
    for (int index = 0; index < width; ++index) {
        f.holes += column_holes(columns[index]);
        f.aggregate_height += heights[index];
        f.max_height = std::max(f.max_height, heights[index]);
    }
    for (int index = 0; index + 1 < width; ++index) {
        f.bumpiness += std::abs(heights[index] - heights[index + 1]);
    }
    return f;
}

// wellplan.field_features: every column but the well; no bumpiness into the well.
inline Features field_features(const Columns& columns) {
    const auto heights = column_heights(columns);
    Features f{0, 0, 0, 0};
    for (int index = 0; index < width; ++index) {
        if (index == well_column) {
            continue;
        }
        f.holes += column_holes(columns[index]);
        f.aggregate_height += heights[index];
        f.max_height = std::max(f.max_height, heights[index]);
    }
    for (int index = 0; index + 1 < width; ++index) {
        if (index != well_column && index + 1 != well_column) {
            f.bumpiness += std::abs(heights[index] - heights[index + 1]);
        }
    }
    return f;
}

// wellplan.well_reserve: rows a vertical I dropped in the well would clear now.
inline int well_reserve(const Columns& columns) {
    const std::uint32_t visible = columns[well_column] >> hidden_rows;
    const int blocked = visible ? hidden_rows + std::countr_zero(visible) : grid_rows;
    const int landing = blocked - reserve_cap;
    if (landing < 0) {
        return 0;
    }
    return std::min(settle(columns, I, 1, well_column, landing).cleared, reserve_cap);
}

// tunedplan.row_transitions: filled/empty changes along each row from the top of
// the stack down, the walls counting as filled.
inline int row_transitions(const Columns& columns) {
    const int top = height - stack_height(columns);
    int total = 0;
    for (int row = top; row < height; ++row) {
        int previous = 1;
        for (std::uint32_t column : columns) {
            const int cell = (column >> (row + hidden_rows)) & 1;
            total += cell != previous;
            previous = cell;
        }
        total += previous != 1;
    }
    return total;
}

// tunedplan.column_transitions: changes down each visible column, floor included.
inline int column_transitions(const Columns& columns) {
    int total = 0;
    for (std::uint32_t column : columns) {
        const std::uint32_t visible = column >> hidden_rows;
        int previous = 0;
        for (int row = 0; row < height; ++row) {
            const int cell = (visible >> row) & 1;
            total += cell != previous;
            previous = cell;
        }
        total += previous != 1;
    }
    return total;
}

// tunedplan.edge_depth: how far each edge column sits below its inner neighbour.
inline int edge_depth(const Columns& columns) {
    const auto heights = column_heights(columns);
    return std::max(0, heights[1] - heights[0]) +
           std::max(0, heights[width - 2] - heights[width - 1]);
}

}  // namespace fallgorithm
