// Experiment 016: rollout re-ranking on top of search.hpp's Searcher.
//
// From Params::rollout_from_level to rollout_to_level, a decision with the preview
// known runs the Searcher as usual, then takes its rollout_beam best options and plays
// each one forward rollout_count times, rollout_depth pieces each: the preview first,
// then pieces drawn with the NES odds, each placed by the same Searcher (preview known,
// from the spawn). The same piece sequences are used for every option. A rollout's
// return is summed as the search sums a path: each placement's value (value_of), the
// option's own included. A rollout that tops out stops there and loses rollout_death
// for each placement it did not make, so dying early never beats a run of penalties.
// The option with the best mean return wins (the first of equal means: the option with
// the best preview path, which is not always the one the search picked).
//
// The draws come from a splitmix64 stream seeded by the position, so a game stays a
// pure function of its seed. Off (rollout_beam below 2, rollout_count or rollout_depth
// below 1, or the level outside the band),
// the agent plays exactly as the Searcher alone.
//
// Experiment 017: from Params::commit_rollout_from_level to commit_rollout_to_level, the
// commit decision (preview not known yet) is re-ranked the same way, with its own beam,
// count and depth: the commit search's best options (Searcher::commit_candidates), and
// rollouts whose first piece, the unknown preview, is drawn with the NES odds after the
// current piece. Off by the same rule, the commit decision is the Searcher's alone.
#pragma once

#include <cstdint>
#include <vector>

#include "board.hpp"
#include "eval.hpp"
#include "search.hpp"

namespace fallgorithm {

class RolloutSearcher {
public:
    RolloutSearcher() = default;
    RolloutSearcher(const Searcher& searcher, const Params& params)
        : searcher_(searcher), policy_(searcher), params_(params) {}

    bool search(const Position& position, Choice& choice) {
        if (!searcher_.search(position, choice)) {
            return false;
        }
        const bool preview = position.next_piece >= 0;
        const int from = preview ? params_.rollout_from_level : params_.commit_rollout_from_level;
        const int to = preview ? params_.rollout_to_level : params_.commit_rollout_to_level;
        const int beam = preview ? params_.rollout_beam : params_.commit_rollout_beam;
        const int count = preview ? params_.rollout_count : params_.commit_rollout_count;
        const int depth = preview ? params_.rollout_depth : params_.commit_rollout_depth;
        if (!choice.found || beam < 2 || count < 1 || depth < 1 || position.level < from ||
            position.level > to) {
            return true;
        }
        if (preview) {
            searcher_.candidates(beam, candidates_);
        } else {
            searcher_.commit_candidates(beam, candidates_);
        }
        if (candidates_.size() < 2) {
            return true;
        }
        draw_sequences(position, count, depth);
        const int phase =
            phase_of(params_, position.level, position.drought, position.columns);
        int best = 0;
        double best_mean = 0.0;
        for (int index = 0; index < static_cast<int>(candidates_.size()); ++index) {
            const Searcher::Candidate& candidate = candidates_[index];
            const int lines = position.lines + candidate.cleared;
            const double first = value_of(params_, phase, candidate.cleared, candidate.settled,
                                          level_for_lines(lines, position.start_level));
            double total = 0.0;
            for (const std::vector<int>& sequence : sequences_) {
                double value = 0.0;
                if (!rollout(position, candidate.settled, lines, sequence, depth, value)) {
                    return false;
                }
                total += first + value;
            }
            const double mean = total / static_cast<double>(sequences_.size());
            if (index == 0 || mean > best_mean) {
                best = index;
                best_mean = mean;
            }
        }
        return searcher_.choose(candidates_[best].order, choice);
    }

    bool random_choice(std::uint64_t pick, Choice& choice) {
        return searcher_.random_choice(pick, choice);
    }

private:
    // One rollout from ``columns`` with ``lines`` cleared, its return in ``total``:
    // ``sequence`` holds the preview and then ``depth`` drawn pieces; piece t is
    // placed knowing piece t + 1. Returns false only if a search's walk back failed.
    bool rollout(const Position& start, Columns columns, int lines,
                 const std::vector<int>& sequence, int depth, double& total) {
        total = 0.0;
        int drought = start.drought;
        for (int step = 0; step < depth; ++step) {
            const int piece = sequence[step], next = sequence[step + 1];
            drought = piece == I || next == I ? 0 : drought + 1;
            const int level = level_for_lines(lines, start.start_level);
            const Position position{columns, piece, next, Flight{}, drought, level, lines,
                                    start.start_level, start.double_killscreen,
                                    start.interval};
            if (!policy_.search(position, choice_)) {
                return false;
            }
            if (!choice_.found) {
                total -= static_cast<double>(params_.rollout_death) * (depth - step);
                return true;
            }
            const Settled settled =
                settle(columns, piece, choice_.orientation, choice_.x, choice_.y);
            const int phase = phase_of(params_, level, drought, columns);
            total += value_of(params_, phase, settled.cleared, settled.columns,
                              level_for_lines(lines + settled.cleared, start.start_level));
            lines += settled.cleared;
            columns = settled.columns;
        }
        return true;
    }

    // ``count`` sequences of the preview and ``depth`` pieces drawn with the NES odds
    // after the piece before, from a stream seeded by the position. An unknown preview
    // (the commit decision) is drawn first, after the current piece.
    void draw_sequences(const Position& position, int count, int depth) {
        std::uint64_t state = 0x6a09e667f3bcc909ull;
        for (int column = 0; column < width; ++column) {
            state = mix(state ^ position.columns[column]);
        }
        const bool preview = position.next_piece >= 0;
        const std::uint64_t next = preview ? static_cast<std::uint64_t>(position.next_piece) : 0xff;
        state = mix(state ^ (static_cast<std::uint64_t>(position.piece) << 8 | next));
        state = mix(state ^ static_cast<std::uint64_t>(position.lines));
        sequences_.assign(count, {});
        for (std::vector<int>& sequence : sequences_) {
            if (preview) {
                sequence.assign(1, position.next_piece);
            } else {
                sequence.assign(1, draw(state, position.piece));
            }
            for (int step = 0; step < depth; ++step) {
                sequence.push_back(draw(state, sequence.back()));
            }
        }
    }

    // One piece after ``previous`` with the NES odds, the stream advanced once.
    static int draw(std::uint64_t& state, int previous) {
        state = mix(state);
        const double roll = static_cast<double>(state >> 11) * 0x1.0p-53;
        int piece = 0;
        double cumulative = 0.0;
        for (; piece < piece_types - 1; ++piece) {
            cumulative += nes_odds(previous, piece);
            if (roll < cumulative) {
                break;
            }
        }
        return piece;
    }

    static std::uint64_t mix(std::uint64_t z) {  // splitmix64's step and finalizer
        z += 0x9e3779b97f4a7c15ull;
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ull;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebull;
        return z ^ (z >> 31);
    }

    Searcher searcher_, policy_;
    Params params_{};
    Choice choice_;
    std::vector<Searcher::Candidate> candidates_;
    std::vector<std::vector<int>> sequences_;
};

}  // namespace fallgorithm
