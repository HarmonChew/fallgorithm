// reachplan.search in C++: the current piece, the preview, then the seven unknown
// pieces, with a beam of two.
//
// A translation of src/block_stack_ai/reachplan.search (which is tunedplan.search
// with reach.py's placements). Ties are kept exactly as there: options come in
// reach.py's order, the first of equal values wins, and the beam is ordered by
// value, then by the option's place in that order. The phase rule is built once
// from the real level and used at every ply; only gravity follows the ply's level.
#pragma once

#include <algorithm>
#include <cstdint>
#include <limits>
#include <vector>

#include "board.hpp"
#include "eval.hpp"
#include "reach.hpp"

namespace fallgorithm {

constexpr int beam_width = 2;                   // searchplan.BEAM_WIDTH
constexpr double unknown_weight = 1.0 / piece_types;  // searchplan.UNKNOWN_WEIGHT
constexpr double minus_infinity = -std::numeric_limits<double>::infinity();

// wellplan.next_drought
inline int next_drought(int drought, int piece) { return piece == I ? 0 : drought + 1; }

struct Position {
    Columns columns;
    int piece;
    int next_piece;  // -1: not known yet (the commit search)
    Flight flight;
    int drought, level, lines, start_level;
    bool double_killscreen;
    int interval;  // limits.Limits.tap_interval
};

struct Choice {
    bool found = false;
    int orientation = 0, x = 0, y = 0;
    std::vector<std::uint8_t> masks;
};

class Searcher {
public:
    Searcher() = default;
    explicit Searcher(const Params& params) : params_(params) {}
    void set_params(const Params& params) { params_ = params; }

    // reachplan.search; ``choice.found`` is false where the Python returns None.
    // Returns false only if the walk back for the chosen placement failed.
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
            current_.push_back({placement, settled.cleared, settled.columns});
        }
        if (current_.empty()) {
            return true;
        }
        const int phase = phase_of(params_, level, position.drought, position.columns);
        const Option* best = &current_[0];
        if (position.next_piece < 0) {
            double best_total = minus_infinity;
            for (const Option& option : current_) {
                const double total =
                    value_of(params_, phase, option.cleared, option.settled) +
                    unknown_average(option.settled, position.drought,
                                    level_for_lines(position.lines + option.cleared,
                                                    position.start_level));
                if (total > best_total) {
                    best = &option;
                    best_total = total;
                }
            }
        } else {
            const int preview_drought = next_drought(position.drought, position.next_piece);
            paths_.clear();
            for (int order = 0; order < static_cast<int>(current_.size()); ++order) {
                const Option& option = current_[order];
                const double own = value_of(params_, phase, option.cleared, option.settled);
                const int next_level =
                    level_for_lines(position.lines + option.cleared, position.start_level);
                Path path{0.0, order, false, 0, {}};
                const double preview_value =
                    best_value(option.settled, position.next_piece, next_level,
                               phase_of(params_, level, preview_drought, option.settled), &path);
                path.value = own + preview_value;
                paths_.push_back(path);
            }
            std::stable_sort(paths_.begin(), paths_.end(), [](const Path& a, const Path& b) {
                return a.value > b.value;  // ties keep the option order
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
                const int unknown_level = level_for_lines(
                    position.lines + option.cleared + path.preview_cleared, position.start_level);
                const double total =
                    path.value +
                    unknown_average(path.preview_settled, preview_drought, unknown_level);
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

    // The commit search's term for one settled board (for the tests): the mean best
    // value of the seven unknown pieces, the phase from the position's real level.
    double expected_unknown(const Position& position, const Columns& settled, int base_drought,
                            int unknown_level) {
        position_ = position;
        return unknown_average(settled, base_drought, unknown_level);
    }

private:
    struct Option {
        Reach placement;
        int cleared;
        Columns settled;
    };
    struct Path {
        double value;
        int order;
        bool preview_found;
        int preview_cleared;
        Columns preview_settled;
    };

    // tunedplan._best over a fresh piece's placements: the best value (-inf if
    // none). With ``path``, also keeps the best placement's settled board.
    double best_value(const Columns& columns, int piece, int ply_level, int phase, Path* path) {
        ply_.run(columns, piece, Flight{}, gravity_period(ply_level),
                 gravity_rows(ply_level, position_.double_killscreen), position_.interval,
                 false);
        bool found = false;
        double best = minus_infinity;
        for (const Reach& placement : ply_.placements) {
            const Settled settled =
                settle(columns, piece, placement.orientation, placement.x, placement.y);
            const double value = value_of(params_, phase, settled.cleared, settled.columns);
            if (!found || value > best) {
                found = true;
                best = value;
                if (path) {
                    path->preview_found = true;
                    path->preview_cleared = settled.cleared;
                    path->preview_settled = settled.columns;
                }
            }
        }
        return best;
    }

    // reachplan.search's unknown_average with searchplan.unknown_value: the mean,
    // over the seven pieces in PIECES order, of each one's best value.
    double unknown_average(const Columns& settled, int base_drought, int unknown_level) {
        double total = 0.0;
        for (int unknown = 0; unknown < piece_types; ++unknown) {
            const int phase =
                phase_of(params_, position_.level, next_drought(base_drought, unknown), settled);
            total += best_value(settled, unknown, unknown_level, phase, nullptr) * unknown_weight;
        }
        return total;
    }

    Params params_{};
    Position position_{};
    ReachSearch root_, ply_;
    std::vector<Option> current_;
    std::vector<Path> paths_;
};

}  // namespace fallgorithm
