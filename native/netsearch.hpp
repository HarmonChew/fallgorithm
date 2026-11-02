// Experiment 020's search with the value network (net.hpp): no hand-built score.
//
// Adjust decision (preview known): every placement of the current piece, then every
// placement of the preview after it; a pair is worth both clears' points plus the
// network's value of the board both leave, and the current piece's placement of the best
// pair is chosen. Commit decision (preview not known): each placement's points plus the
// value of the board it leaves; the network was trained on boards read before the next
// piece was known, so it averages over that piece itself. A placement whose preview has
// nowhere to go is worth -inf; the first of equal totals wins.
//
// The prefilter (off unless set): the hand search (search.hpp's Searcher with 015's
// numbers, extra ply and NES odds) ranks the current piece's placements first, and only
// its best ``prefilter`` are valued by the network. This keeps the network to boards
// like those it was trained on: chosen from all of them, it finds the boards where its
// guess is most wrong (towers 015's agent never builds). Only the current piece is
// prefiltered; at the adjust the preview's placements are all valued. The adjust
// ranking is the hand search's one-ply path value, so a prefilter of 2 holds its
// choice (made within its beam of 2) but a prefilter of 1 is not 015's agent.
#pragma once

#include <algorithm>
#include <cstdint>
#include <utility>
#include <vector>

#include "board.hpp"
#include "net.hpp"
#include "reach.hpp"
#include "search.hpp"
#include "value.hpp"

namespace fallgorithm {

constexpr double net_tetris_points = 1200.0 * 19;  // experiment020.TETRIS_18

// The value network's value of a settled board, in points (0 once the lines reach the
// cap): ``drought`` counts ``last``, the piece that left the board.
inline double net_value(const ValueNetwork& net, int line_cap, const Columns& columns,
                        int lines, int drought, int last, int start_level) {
    if (lines >= line_cap) {
        return 0.0;
    }
    const auto f = board_feature_values(columns);
    const int level = level_for_lines(lines, start_level);
    const int band = level <= start_level ? 0 : level < 29 ? 1
                     : level < double_gravity_level ? 2 : 3;
    return net_tetris_points *
           net_forward(net, columns, f.data(), band, line_cap - lines, drought, last);
}

class NetSearcher {
public:
    NetSearcher(const ValueNetwork* net, int line_cap) : net_(net), line_cap_(line_cap) {}
    NetSearcher(const ValueNetwork* net, int line_cap, const Params& params, int prefilter)
        : net_(net), line_cap_(line_cap), hand_(params), prefilter_(prefilter) {
        hand_.set_extra_ply(true);
        hand_.set_nes_odds(true);
    }

    // The network's value, in points (0 once the lines reach the cap).
    double value(const Columns& columns, int lines, int drought, int last, int start_level) const {
        return net_value(*net_, line_cap_, columns, lines, drought, last, start_level);
    }

    bool search(const Position& position, Choice& choice) {
        if (prefilter_ > 0) {
            return search_prefiltered(position, choice);
        }
        choice = Choice{};
        const int level = position.level;
        root_.run(position.columns, position.piece, position.flight, gravity_period(level),
                  gravity_rows(level, position.double_killscreen), position.interval);
        if (root_.placements.empty()) {
            return true;
        }
        const int start = position.start_level;
        if (position.next_piece >= 0 && adjust_k_ > 0 && level <= adjust_max_level_) {
            int pick = 0;
            if (deep_adjust(position, pick)) {
                return finish(pick, choice);
            }
        }
        const bool deep_commit = position.next_piece < 0 && level >= commit_level_;
        int best = 0;
        double best_total = minus_infinity;
        for (int order = 0; order < static_cast<int>(root_.placements.size()); ++order) {
            const Reach& placement = root_.placements[order];
            const Settled settled = settle(position.columns, position.piece,
                                           placement.orientation, placement.x, placement.y);
            const int lines = position.lines + settled.cleared;
            double total = clear_reward(settled.cleared, lines, start);
            if (deep_commit) {
                // Experiment 026: the backup (expectimax over the next piece) instead of V.
                // Same drought and last as the value call below: backup's drought counts
                // ``last``, and the agent's drought already counts the current piece. backup
                // runs ply_, not root_, so root_.placements stays intact.
                total += backup(settled.columns, lines, position.drought, position.piece, start,
                                position.double_killscreen, position.interval);
            } else if (position.next_piece < 0) {
                // The agent's drought already counts the current piece.
                total += value(settled.columns, lines, position.drought, position.piece, start);
            } else {
                total += best_preview(settled.columns, lines, position);
            }
            if (total > best_total) {
                best = order;
                best_total = total;
            }
        }
        return finish(best, choice);
    }

    // Experiment 026's search changes (search only, not the prefiltered path). From
    // ``commit_level`` on the commit decision values a board by ``backup``; at levels up to
    // ``adjust_max_level`` the adjust decision rescores by
    // ``backup`` (the best ``adjust_k`` current placements, each through its best ``adjust_k``
    // preview placements). ``adjust_k`` 0 and a huge ``commit_level`` are off:
    // the search is then 020's.
    void set_deep(int commit_level, int adjust_k, int adjust_max_level) {
        commit_level_ = commit_level;
        adjust_k_ = adjust_k;
        adjust_max_level_ = adjust_max_level;
    }

    // Experiment 013's exploration (agent.hpp): a random root placement instead.
    bool random_choice(std::uint64_t pick, Choice& choice) {
        if (prefilter_ > 0) {
            return hand_.random_choice(pick, choice);
        }
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

    static constexpr double tetris_points = net_tetris_points;

    // Experiment 023's backup of a settled board (the next piece not yet known): the
    // average, over the next piece by the NES odds after ``last`` (1/7 each for the first
    // board, last -1), of its best placement from the spawn (the commit search's reach)
    // by clear points plus the network's value of what it leaves; a piece with nowhere
    // to go adds 0 (the game is over). 0 once the lines reach the cap. With ``children``
    // (7 entries), each piece's best board, its lines, drought and the piece that left it
    // (lines -1 if that piece has no placement).
    struct Child {
        Columns columns{};
        int lines = -1, drought = 0, last = -1;
    };
    double backup(const Columns& columns, int lines, int drought, int last, int start_level,
                  bool double_killscreen, int interval, Child* children = nullptr) {
        if (lines >= line_cap_) {
            if (children) {
                for (int piece = 0; piece < piece_types; ++piece) {
                    children[piece] = Child{};
                }
            }
            return 0.0;
        }
        const int level = level_for_lines(lines, start_level);
        double total = 0.0;
        for (int piece = 0; piece < piece_types; ++piece) {
            const double odds = last < 0 ? 1.0 / piece_types : nes_odds(last, piece);
            ply_.run(columns, piece, Flight{}, gravity_period(level),
                     gravity_rows(level, double_killscreen), interval, false);
            const int after_drought = next_drought(drought, piece);
            double best = minus_infinity;
            Child child;
            for (const Reach& placement : ply_.placements) {
                const Settled settled = settle(columns, piece, placement.orientation,
                                               placement.x, placement.y);
                const int after = lines + settled.cleared;
                const double value = clear_reward(settled.cleared, after, start_level) +
                                     this->value(settled.columns, after, after_drought, piece,
                                                 start_level);
                if (value > best) {
                    best = value;
                    child = Child{settled.columns, after, after_drought, piece};
                }
            }
            if (children) {
                children[piece] = child;
            }
            if (best > minus_infinity) {
                total += odds * best;
            }
        }
        return total;
    }

private:
    bool finish(int order, Choice& choice) {
        const Reach& chosen = root_.placements[order];
        choice.found = true;
        choice.orientation = chosen.orientation;
        choice.x = chosen.x;
        choice.y = chosen.y;
        return root_.masks(chosen, choice.masks);
    }

    // One (current, preview) pair left on the board ``columns``.
    struct Pair {
        int order = 0;
        double first = 0.0, second = 0.0;  // the clears' points
        double total = 0.0;                // first + (second + V), as best_preview
        Columns columns{};
        int lines = 0, drought = 0;
    };

    // The adjust with the best ``adjust_k_`` current placements (by their best pair's
    // points + V) each rescored through its best ``adjust_k_`` preview placements by
    // backup; the current placement of the highest rescored value is played. Every pair is
    // valued as best_preview does (its boards are copied out first: backup reuses ply_).
    // Returns false if no pair exists, leaving the ordinary search to decide.
    bool deep_adjust(const Position& position, int& pick) {
        const int start = position.start_level;
        pairs_.clear();
        for (int order = 0; order < static_cast<int>(root_.placements.size()); ++order) {
            const Reach& placement = root_.placements[order];
            const Settled settled = settle(position.columns, position.piece,
                                           placement.orientation, placement.x, placement.y);
            const int lines = position.lines + settled.cleared;
            const double first = clear_reward(settled.cleared, lines, start);
            const int level = level_for_lines(lines, start);
            ply_.run(settled.columns, position.next_piece, Flight{}, gravity_period(level),
                     gravity_rows(level, position.double_killscreen), position.interval, false);
            // The drought after both pieces, as in best_preview.
            const int drought = position.next_piece == I ? 0
                                : position.drought == 0 ? 1 : position.drought + 1;
            for (const Reach& second : ply_.placements) {
                const Settled both = settle(settled.columns, position.next_piece,
                                            second.orientation, second.x, second.y);
                const int after = lines + both.cleared;
                Pair pair;
                pair.order = order;
                pair.first = first;
                pair.second = clear_reward(both.cleared, after, start);
                pair.total = first + (pair.second +
                             value(both.columns, after, drought, position.next_piece, start));
                pair.columns = both.columns;
                pair.lines = after;
                pair.drought = drought;
                pairs_.push_back(pair);
            }
        }
        if (pairs_.empty()) {
            return false;
        }
        // Pairs of one current placement are contiguous. Sort them by total (ties in
        // enumeration order), then rank the placements by their best pair (ties: first).
        std::vector<std::pair<std::size_t, std::size_t>> ranges;  // [begin, end) per placement
        for (std::size_t i = 0; i < pairs_.size();) {
            std::size_t end = i;
            while (end < pairs_.size() && pairs_[end].order == pairs_[i].order) {
                ++end;
            }
            std::stable_sort(pairs_.begin() + i, pairs_.begin() + end,
                             [](const Pair& a, const Pair& b) { return a.total > b.total; });
            ranges.emplace_back(i, end);
            i = end;
        }
        std::stable_sort(ranges.begin(), ranges.end(), [this](const auto& a, const auto& b) {
            return pairs_[a.first].total > pairs_[b.first].total;
        });
        const std::size_t kept = std::min(ranges.size(), static_cast<std::size_t>(adjust_k_));
        double best_value = minus_infinity;
        pick = pairs_[ranges[0].first].order;
        for (std::size_t r = 0; r < kept; ++r) {
            const std::size_t end = std::min(ranges[r].second,
                                             ranges[r].first + static_cast<std::size_t>(adjust_k_));
            double value_of = minus_infinity;
            for (std::size_t i = ranges[r].first; i < end; ++i) {
                const Pair& pair = pairs_[i];
                value_of = std::max(value_of,
                                    pair.first + (pair.second +
                                    backup(pair.columns, pair.lines, pair.drought,
                                           position.next_piece, start, position.double_killscreen,
                                           position.interval)));
            }
            if (value_of > best_value) {
                best_value = value_of;
                pick = pairs_[ranges[r].first].order;
            }
        }
        return true;
    }

    // The search over the hand search's best ``prefilter_`` placements, in its order.
    bool search_prefiltered(const Position& position, Choice& choice) {
        if (!hand_.search(position, choice)) {
            return false;
        }
        if (!choice.found) {
            return true;
        }
        if (position.next_piece < 0) {
            hand_.commit_candidates(prefilter_, candidates_);
        } else {
            hand_.candidates(prefilter_, candidates_);
        }
        const int start = position.start_level;
        int best = -1;
        double best_total = minus_infinity;
        for (const Searcher::Candidate& candidate : candidates_) {
            const int lines = position.lines + candidate.cleared;
            double total = clear_reward(candidate.cleared, lines, start);
            if (position.next_piece < 0) {
                total += value(candidate.settled, lines, position.drought, position.piece, start);
            } else {
                total += best_preview(candidate.settled, lines, position);
            }
            if (best < 0 || total > best_total) {
                best = candidate.order;
                best_total = total;
            }
        }
        return best < 0 || hand_.choose(best, choice);
    }

    // The best preview placement on ``columns``: its points plus the value of what it
    // leaves (-inf if it has none).
    double best_preview(const Columns& columns, int lines, const Position& position) {
        const int start = position.start_level;
        const int level = level_for_lines(lines, start);
        ply_.run(columns, position.next_piece, Flight{}, gravity_period(level),
                 gravity_rows(level, position.double_killscreen), position.interval, false);
        // The drought after both pieces. With the preview known the agent's drought is 0
        // when either piece is an I, else it counts the current piece.
        const int drought = position.next_piece == I ? 0
                            : position.drought == 0 ? 1 : position.drought + 1;
        double best = minus_infinity;
        for (const Reach& placement : ply_.placements) {
            const Settled settled = settle(columns, position.next_piece, placement.orientation,
                                           placement.x, placement.y);
            const int after = lines + settled.cleared;
            const double total = clear_reward(settled.cleared, after, start) +
                                 value(settled.columns, after, drought, position.next_piece, start);
            best = std::max(best, total);
        }
        return best;
    }

    const ValueNetwork* net_;
    int line_cap_;
    Searcher hand_{};
    int prefilter_ = 0;
    std::vector<Searcher::Candidate> candidates_;
    ReachSearch root_, ply_;
    int commit_level_ = 1 << 30, adjust_k_ = 0, adjust_max_level_ = 28;
    std::vector<Pair> pairs_;
};

}  // namespace fallgorithm
