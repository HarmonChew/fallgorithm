// Experiment 013's learned value: a linear guess of the score still to come from a
// settled board, and the search that uses it in place of eval.hpp's 20 numbers.
//
// C++ only (no Python copy). The value of a board after a placement is
//
//     V(board, lines) = w[band] . x(board, lines)
//
// where the band is the board's level range (below 29, 29-38, 39 and up) and x is
// a constant, the lines left before the cap (L, in hundreds), the 18 board features
// below, and each feature times L. So each band has 38 weights, 114 in all, fitted by
// least squares to the score each self-play game actually went on to make.
#pragma once

#include <algorithm>
#include <array>
#include <cstdint>
#include <limits>
#include <vector>

#include "board.hpp"
#include "reach.hpp"
#include "search.hpp"

namespace fallgorithm {

constexpr int board_features = 18;
constexpr int band_weights = 2 + 2 * board_features;
constexpr int value_bands = 3;
constexpr int value_weights = value_bands * band_weights;
constexpr int clear_points[5] = {0, 40, 100, 300, 1200};  // the engine's (game.cpp)

struct ValueModel {
    int line_cap = 430;
    std::array<double, value_weights> weights{};
};

// The band of a level: 0 below 29, 1 for 29-38, 2 from the double killscreen on.
inline int value_band(int level) { return level < 29 ? 0 : level < double_gravity_level ? 1 : 2; }

// The 18 board features, in this order:
//  0 holes (all columns)            7 row transitions
//  1 rows holding a hole            8 column transitions
//  2 hole depth (filled cells       9 well depth (lowest of columns 0-8 minus
//    above each hole, summed)          the well's height, at least 0)
//  3 aggregate height (cols 0-8)   10 well reserve (0-4)
//  4 bumpiness (cols 0-8)          11 the well column's height
//  5 max height (all columns)      12 edge depth
//  6 max height above 10 (or 0)    13 pits: columns 0-8 at least 3 below both
//                                     neighbours (one at the edges, the well not
//                                     counted as a neighbour)
// 14-17 max height at least 10, 13, 15, 17 (1 or 0): steps, so the danger near the
// top need not grow in a straight line with the height.
inline std::array<double, board_features> board_feature_values(const Columns& columns) {
    const auto heights = column_heights(columns);
    std::array<double, board_features> f{};
    std::uint32_t hole_rows = 0;
    int holes = 0, depth = 0;
    for (std::uint32_t column : columns) {
        const std::uint32_t visible = column >> hidden_rows;
        if (!visible) {
            continue;
        }
        int above = 0;
        for (int row = std::countr_zero(visible); row < height; ++row) {
            if ((visible >> row) & 1) {
                above += 1;
            } else {
                holes += 1;
                depth += above;
                hole_rows |= 1u << row;
            }
        }
    }
    const Features field = field_features(columns);
    int lowest = height;
    for (int index = 0; index < well_column; ++index) {
        lowest = std::min(lowest, heights[index]);
    }
    int pits = 0;
    for (int index = 0; index < well_column; ++index) {
        const int left = index > 0 ? heights[index - 1] : height;
        const int right = index + 1 < well_column ? heights[index + 1] : height;
        pits += std::min(left, right) - heights[index] >= 3;
    }
    const int tallest = stack_height(columns);
    f[0] = holes;
    f[1] = std::popcount(hole_rows);
    f[2] = depth;
    f[3] = field.aggregate_height;
    f[4] = field.bumpiness;
    f[5] = tallest;
    f[6] = std::max(0, tallest - 10);
    f[7] = row_transitions(columns);
    f[8] = column_transitions(columns);
    f[9] = std::max(0, lowest - heights[well_column]);
    f[10] = well_reserve(columns);
    f[11] = heights[well_column];
    f[12] = edge_depth(columns);
    f[13] = pits;
    f[14] = tallest >= 10;
    f[15] = tallest >= 13;
    f[16] = tallest >= 15;
    f[17] = tallest >= 17;
    return f;
}

// The band and its 38 inputs for one board with ``lines`` cleared so far.
inline int value_inputs(const ValueModel& model, const Columns& columns, int lines,
                        int start_level, std::array<double, band_weights>& x) {
    const double left = std::max(0, model.line_cap - lines) / 100.0;
    const auto f = board_feature_values(columns);
    x[0] = 1.0;
    x[1] = left;
    for (int index = 0; index < board_features; ++index) {
        x[2 + index] = f[index];
        x[2 + board_features + index] = f[index] * left;
    }
    return value_band(level_for_lines(lines, start_level));
}

inline double board_value(const ValueModel& model, const Columns& columns, int lines,
                          int start_level) {
    std::array<double, band_weights> x{};
    const int band = value_inputs(model, columns, lines, start_level, x);
    double total = 0.0;
    for (int index = 0; index < band_weights; ++index) {
        total += model.weights[band * band_weights + index] * x[index];
    }
    return total;
}

// The points a clear of ``cleared`` rows earns when it brings the lines to
// ``lines_after`` (the engine updates the level first, then scores).
inline double clear_reward(int cleared, int lines_after, int start_level) {
    return static_cast<double>(clear_points[cleared]) *
           (level_for_lines(lines_after, start_level) + 1);
}

// reach_plan's search shape (search.hpp) with the learned value: the current piece,
// the preview, a beam of two, then the seven unknown pieces. A placement is worth
// its clear's points plus, at the last ply, the learned value of the board it leaves.
class ValueSearcher {
public:
    ValueSearcher() = default;
    explicit ValueSearcher(const ValueModel& model) : model_(model) {}

    bool search(const Position& position, Choice& choice) {
        position_ = position;
        choice = Choice{};
        const int level = position.level;
        root_.run(position.columns, position.piece, position.flight, gravity_period(level),
                  gravity_rows(level, position.double_killscreen), position.interval);
        current_.clear();
        for (const Reach& placement : root_.placements) {
            const Settled settled = settle(position.columns, position.piece,
                                           placement.orientation, placement.x, placement.y);
            const int lines = position.lines + settled.cleared;
            current_.push_back({placement, lines, settled.columns,
                                clear_reward(settled.cleared, lines, position.start_level)});
        }
        if (current_.empty()) {
            return true;
        }
        const Option* best = &current_[0];
        if (position.next_piece < 0) {
            double best_total = minus_infinity;
            for (const Option& option : current_) {
                const double total =
                    option.reward + unknown_average(option.settled, option.lines);
                if (total > best_total) {
                    best = &option;
                    best_total = total;
                }
            }
        } else {
            paths_.clear();
            for (int order = 0; order < static_cast<int>(current_.size()); ++order) {
                const Option& option = current_[order];
                Path path{0.0, order, false, 0, 0.0, {}};
                path.value = option.reward +
                             best_q(option.settled, position.next_piece, option.lines, &path);
                paths_.push_back(path);
            }
            std::stable_sort(paths_.begin(), paths_.end(), [](const Path& a, const Path& b) {
                return a.value > b.value;
            });
            const int beam = std::min(beam_width, static_cast<int>(paths_.size()));
            best = &current_[paths_[0].order];
            bool have_total = false;
            double best_total = 0.0;
            for (int index = 0; index < beam; ++index) {
                const Path& path = paths_[index];
                if (!path.preview_found) {
                    continue;
                }
                const Option& option = current_[path.order];
                const double total = option.reward + path.preview_reward +
                                     unknown_average(path.preview_settled, path.preview_lines);
                if (!have_total || total > best_total) {
                    best = &option;
                    best_total = total;
                    have_total = true;
                }
            }
        }
        choice.found = true;
        choice.orientation = best->placement.orientation;
        choice.x = best->placement.x;
        choice.y = best->placement.y;
        return root_.masks(best->placement, choice.masks);
    }

    // Experiment 013's exploration: after a search, the root placement ``pick`` picks
    // (modulo their count) in place of the searched one.
    bool random_choice(std::uint64_t pick, Choice& choice) {
        choice = Choice{};
        if (root_.placements.empty()) {
            return true;
        }
        const Reach& placement = root_.placements[pick % root_.placements.size()];
        choice.found = true;
        choice.orientation = placement.orientation;
        choice.x = placement.x;
        choice.y = placement.y;
        return root_.masks(placement, choice.masks);
    }

private:
    struct Option {
        Reach placement;
        int lines;
        Columns settled;
        double reward;
    };
    struct Path {
        double value;
        int order;
        bool preview_found;
        int preview_lines;
        double preview_reward;
        Columns preview_settled;
    };

    // The best placement of a fresh piece: max of its clear's points plus the learned
    // value of what it leaves (-inf if it has none). With ``path``, keeps that
    // placement's board, lines and points.
    double best_q(const Columns& columns, int piece, int lines, Path* path) {
        const int ply_level = level_for_lines(lines, position_.start_level);
        ply_.run(columns, piece, Flight{}, gravity_period(ply_level),
                 gravity_rows(ply_level, position_.double_killscreen), position_.interval,
                 false);
        bool found = false;
        double best = minus_infinity;
        for (const Reach& placement : ply_.placements) {
            const Settled settled =
                settle(columns, piece, placement.orientation, placement.x, placement.y);
            const int after = lines + settled.cleared;
            const double reward = clear_reward(settled.cleared, after, position_.start_level);
            const double value =
                reward + board_value(model_, settled.columns, after, position_.start_level);
            if (!found || value > best) {
                found = true;
                best = value;
                if (path) {
                    path->preview_found = true;
                    path->preview_lines = after;
                    path->preview_reward = reward;
                    path->preview_settled = settled.columns;
                }
            }
        }
        return best;
    }

    double unknown_average(const Columns& settled, int lines) {
        double total = 0.0;
        for (int unknown = 0; unknown < piece_types; ++unknown) {
            total += best_q(settled, unknown, lines, nullptr) * unknown_weight;
        }
        return total;
    }

    ValueModel model_{};
    Position position_{};
    ReachSearch root_, ply_;
    std::vector<Option> current_;
    std::vector<Path> paths_;
};

// Least-squares sums for fitting the weights: for every board a game left (one per
// piece, read at the next spawn), its band's inputs and the score the game made
// after it. Only that band's block of the 114 x 114 matrix is touched.
struct FitSums {
    std::vector<double> gram = std::vector<double>(value_weights * value_weights, 0.0);
    std::vector<double> target = std::vector<double>(value_weights, 0.0);
    double count = 0.0, total = 0.0, squares = 0.0;
};

struct BoardSample {
    Columns columns;
    int lines;
    std::uint64_t score;
    // Experiment 020: pieces since the last I (the piece that left the board counted),
    // and that piece (-1 before the first).
    int drought = 0;
    int last = -1;
};

inline void add_game(const ValueModel& model, const std::vector<BoardSample>& samples,
                     std::uint64_t final_score, int start_level, FitSums& sums) {
    std::array<double, band_weights> x{};
    for (const BoardSample& sample : samples) {
        const int band = value_inputs(model, sample.columns, sample.lines, start_level, x);
        const double y = static_cast<double>(final_score - sample.score);
        const int base = band * band_weights;
        for (int i = 0; i < band_weights; ++i) {
            sums.target[base + i] += x[i] * y;
            for (int j = 0; j < band_weights; ++j) {
                sums.gram[(base + i) * value_weights + base + j] += x[i] * x[j];
            }
        }
        sums.count += 1.0;
        sums.total += y;
        sums.squares += y * y;
    }
}

}  // namespace fallgorithm
