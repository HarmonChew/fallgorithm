// reachplan.search in C++: the current piece, the preview, then the seven unknown
// pieces, with a beam of two.
//
// A translation of src/block_stack_ai/reachplan.search (which is tunedplan.search
// with reach.py's placements). Ties are kept exactly as there: options come in
// reach.py's order, the first of equal values wins, and the beam is ordered by
// value, then by the option's place in that order. The phase rule is built once
// from the real level and used at every ply; only gravity follows the ply's level.
//
// Experiment 015 (off by default): from Params::commit_ply_level on, the commit search
// (preview not known yet) adds 013's extra ply to its Params::commit_beam best options.
// Experiment 017 reads the commit search's ranking (commit_candidates).
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

// Experiment 014: the engine's NES randomizer (block-stack core/src/rng.cpp), as odds.
// A roll of 0-7 picks from the NES order (T J Z O S L I); a 7 or a repeat of the
// previous piece rerolls once, as (roll of 0-7 + the previous piece's spawn id) % 7,
// which picks the NES order's entry (spawn id % 7) twice in eight. In 64ths:
// 8 for a piece other than the previous, plus 2 (4 for that entry) from the reroll.
constexpr int nes_order[piece_types] = {T, J, Z, O, S, L, I};
constexpr int nes_spawn_id[piece_types] = {18, 7, 14, 10, 11, 2, 8};  // in I J L O S T Z

constexpr double nes_odds(int previous, int piece) {
    const int doubled = nes_order[nes_spawn_id[previous] % piece_types];
    return ((piece != previous ? 8 : 0) + (piece == doubled ? 4 : 2)) / 64.0;
}

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
    // Experiment 013's depth check (C++ only; off by default, which is reach_plan):
    // at the adjust search, look one unknown piece further.
    void set_extra_ply(bool extra_ply) { extra_ply_ = extra_ply; }
    // Experiment 014 (off by default): weigh the unknown pieces by the NES randomizer's
    // odds after the piece before them, not 1/7 each.
    void set_nes_odds(bool nes_odds) { nes_odds_ = nes_odds; }

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
            const bool commit_ply = params_.commit_ply_level >= 0 &&
                                    level >= params_.commit_ply_level && params_.commit_beam > 0;
            double best_total = minus_infinity;
            ranked_.clear();
            for (int order = 0; order < static_cast<int>(current_.size()); ++order) {
                const Option& option = current_[order];
                const int after = position.lines + option.cleared;
                const int after_level = level_for_lines(after, position.start_level);
                const double own =
                    value_of(params_, phase, option.cleared, option.settled, after_level);
                const double total =
                    own + unknown_average(option.settled, position.drought, position.piece,
                                          after_level, after);
                if (total > best_total) {
                    best = &option;
                    best_total = total;
                }
                ranked_.push_back({total, own, order});
            }
            if (commit_ply) {
                // Experiment 015: rank by the one-ply total (ties keep the option order),
                // then for the best ``commit_beam`` replace the seven-piece average with
                // the extra ply; the first of equal totals wins, as at the adjust search.
                std::stable_sort(ranked_.begin(), ranked_.end(),
                                 [](const Ranked& a, const Ranked& b) { return a.total > b.total; });
                const int beam = std::min(params_.commit_beam, static_cast<int>(ranked_.size()));
                best = &current_[ranked_[0].order];
                bool have_total = false;
                double deep_best = 0.0;
                for (int index = 0; index < beam; ++index) {
                    const Option& option = current_[ranked_[index].order];
                    const double total =
                        ranked_[index].own + deeper_average(option.settled, position.drought,
                                                            position.piece,
                                                            position.lines + option.cleared);
                    ranked_[index].total = total;
                    if (!have_total || total > deep_best) {
                        best = &option;
                        deep_best = total;
                        have_total = true;
                    }
                }
                // Experiment 017: the beam in the extra ply's order (ties keep the
                // one-ply order, so the first is the option chosen above).
                std::stable_sort(ranked_.begin(), ranked_.begin() + beam,
                                 [](const Ranked& a, const Ranked& b) { return a.total > b.total; });
            }
            ranked_sorted_ = commit_ply;
            deep_count_ = commit_ply ? std::min(params_.commit_beam,
                                                static_cast<int>(ranked_.size()))
                                     : 0;
        } else {
            const int preview_drought = next_drought(position.drought, position.next_piece);
            paths_.clear();
            for (int order = 0; order < static_cast<int>(current_.size()); ++order) {
                const Option& option = current_[order];
                const int next_level =
                    level_for_lines(position.lines + option.cleared, position.start_level);
                const double own =
                    value_of(params_, phase, option.cleared, option.settled, next_level);
                Path path{0.0, order, false, 0, {}};
                const double preview_value =
                    best_value(option.settled, position.next_piece, next_level,
                               position.lines + option.cleared,
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
                    (extra_ply_ ? deeper_average(path.preview_settled, preview_drought,
                                                 position.next_piece,
                                                 position.lines + option.cleared +
                                                     path.preview_cleared)
                                : unknown_average(path.preview_settled, preview_drought,
                                                  position.next_piece, unknown_level,
                                                  position.lines + option.cleared +
                                                      path.preview_cleared));
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
        chosen_ = static_cast<int>(best - current_.data());
        return root_.masks(best->placement, choice.masks);
    }

    // Experiment 018: the option index the last search chose (when it found one).
    int chosen() const { return chosen_; }

    // Experiment 016: after a search with the preview known that found a placement (only
    // then are ``paths_`` this search's), the ``count`` best options
    // in the order that search ranked them (the preview path's value, ties in the option
    // order), each as (option index, cleared rows, settled board, and Experiment 018's
    // search total: the preview path's value here, the commit search's ranking total
    // after a commit search, and whether that total includes 015's extra ply).
    struct Candidate {
        int order, cleared;
        Columns settled;
        double total;
        bool deep;
    };
    void candidates(int count, std::vector<Candidate>& out) const {
        out.clear();
        const int size = std::min(count, static_cast<int>(paths_.size()));
        for (int index = 0; index < size; ++index) {
            const Option& option = current_[paths_[index].order];
            out.push_back(
                {paths_[index].order, option.cleared, option.settled, paths_[index].value, false});
        }
    }

    // Experiment 017: the same after a commit search (preview not known) that found a
    // placement: the ``count`` best options in the order that search ranked them, by the
    // one-ply total, with Experiment 015's commit beam (when it ran) first, in the extra
    // ply's order. The first is the option the commit search chose.
    void commit_candidates(int count, std::vector<Candidate>& out) {
        if (!ranked_sorted_) {  // without the commit ply, sorted only when asked for
            std::stable_sort(ranked_.begin(), ranked_.end(),
                             [](const Ranked& a, const Ranked& b) { return a.total > b.total; });
            ranked_sorted_ = true;
        }
        out.clear();
        const int size = std::min(count, static_cast<int>(ranked_.size()));
        for (int index = 0; index < size; ++index) {
            const Option& option = current_[ranked_[index].order];
            out.push_back({ranked_[index].order, option.cleared, option.settled,
                           ranked_[index].total, index < deep_count_});
        }
    }

    // Experiment 016: the last search's option ``order`` as its choice, with its masks.
    bool choose(int order, Choice& choice) {
        const Reach& placement = current_[order].placement;
        choice = Choice{};
        choice.found = true;
        choice.orientation = placement.orientation;
        choice.x = placement.x;
        choice.y = placement.y;
        return root_.masks(placement, choice.masks);
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

    // The commit search's term for one settled board (for the tests): the mean best
    // value of the seven unknown pieces, the phase from the position's real level.
    double expected_unknown(const Position& position, const Columns& settled, int base_drought,
                            int unknown_level) {
        position_ = position;
        return unknown_average(settled, base_drought, -1, unknown_level, -1);
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
    // Experiment 015: a commit-search option's one-ply total and own value.
    struct Ranked {
        double total, own;
        int order;
    };

    // tunedplan._best over a fresh piece's placements: the best value (-inf if
    // none). With ``path``, also keeps the best placement's settled board. ``lines``
    // are the lines before the piece: Experiment 014's points term scores a clear at
    // the level after it, as the engine does (-1, for the tests: at ``ply_level``).
    double best_value(const Columns& columns, int piece, int ply_level, int lines, int phase,
                      Path* path) {
        ply_.run(columns, piece, Flight{}, gravity_period(ply_level),
                 gravity_rows(ply_level, position_.double_killscreen), position_.interval,
                 false);
        bool found = false;
        double best = minus_infinity;
        for (const Reach& placement : ply_.placements) {
            const Settled settled =
                settle(columns, piece, placement.orientation, placement.x, placement.y);
            const int points_level =
                lines < 0 ? ply_level
                          : level_for_lines(lines + settled.cleared, position_.start_level);
            const double value =
                value_of(params_, phase, settled.cleared, settled.columns, points_level);
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

    // The weight of ``unknown`` after ``previous`` (-1: not known; 1/7 each).
    double odds(int previous, int unknown) const {
        return nes_odds_ && previous >= 0 ? nes_odds(previous, unknown) : unknown_weight;
    }

    // reachplan.search's unknown_average with searchplan.unknown_value: the mean,
    // over the seven pieces in PIECES order, of each one's best value (Experiment 014:
    // weighted by odds() after ``previous``).
    double unknown_average(const Columns& settled, int base_drought, int previous,
                           int unknown_level, int lines) {
        double total = 0.0;
        for (int unknown = 0; unknown < piece_types; ++unknown) {
            const int phase =
                phase_of(params_, position_.level, next_drought(base_drought, unknown), settled);
            total += best_value(settled, unknown, unknown_level, lines, phase, nullptr) *
                     odds(previous, unknown);
        }
        return total;
    }

    // The extra ply: the mean, over the seven unknown pieces, of each one's best
    // placement's value plus the seven-piece average on the board that placement leaves.
    double deeper_average(const Columns& settled, int base_drought, int previous, int lines) {
        double total = 0.0;
        for (int unknown = 0; unknown < piece_types; ++unknown) {
            const int drought = next_drought(base_drought, unknown);
            const int phase = phase_of(params_, position_.level, drought, settled);
            Path best{0.0, 0, false, 0, {}};
            const double own = best_value(settled, unknown,
                                          level_for_lines(lines, position_.start_level), lines,
                                          phase, &best);
            if (!best.preview_found) {
                return minus_infinity;
            }
            total += (own + unknown_average(best.preview_settled, drought, unknown,
                                            level_for_lines(lines + best.preview_cleared,
                                                            position_.start_level),
                                            lines + best.preview_cleared)) *
                     odds(previous, unknown);
        }
        return total;
    }

    Params params_{};
    bool extra_ply_ = false, nes_odds_ = false;
    Position position_{};
    ReachSearch root_, ply_;
    std::vector<Option> current_;
    std::vector<Path> paths_;
    std::vector<Ranked> ranked_;
    int chosen_ = 0, deep_count_ = 0;
    bool ranked_sorted_ = false;
};

}  // namespace fallgorithm
