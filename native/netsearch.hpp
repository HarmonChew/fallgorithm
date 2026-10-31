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

#include <cstdint>
#include <vector>

#include "board.hpp"
#include "net.hpp"
#include "reach.hpp"
#include "search.hpp"
#include "value.hpp"

namespace fallgorithm {

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
        if (lines >= line_cap_) {
            return 0.0;
        }
        const auto f = board_feature_values(columns);
        const int level = level_for_lines(lines, start_level);
        const int band = level <= start_level ? 0 : level < 29 ? 1
                         : level < double_gravity_level ? 2 : 3;
        return tetris_points * net_forward(*net_, columns, f.data(), band, line_cap_ - lines,
                                           drought, last);
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
        int best = 0;
        double best_total = minus_infinity;
        for (int order = 0; order < static_cast<int>(root_.placements.size()); ++order) {
            const Reach& placement = root_.placements[order];
            const Settled settled = settle(position.columns, position.piece,
                                           placement.orientation, placement.x, placement.y);
            const int lines = position.lines + settled.cleared;
            double total = clear_reward(settled.cleared, lines, start);
            if (position.next_piece < 0) {
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
        const Reach& chosen = root_.placements[best];
        choice.found = true;
        choice.orientation = chosen.orientation;
        choice.x = chosen.x;
        choice.y = chosen.y;
        return root_.masks(chosen, choice.masks);
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

    static constexpr double tetris_points = 1200.0 * 19;  // experiment020.TETRIS_18

private:
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
};

}  // namespace fallgorithm
