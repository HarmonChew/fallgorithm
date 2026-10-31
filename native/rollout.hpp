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
//
// Experiment 019: from the double killscreen (level 39) on, the commit decision's count and
// depth can be set apart (Params::killscreen_rollout_count and _depth; 0 keeps the
// commit_rollout_ ones). The 29-38 adjust decision (preview known) is 016's band, so
// rollout_to_level 38 re-ranks it with 016's settings; no code is needed for that.
//
// Experiment 018: the same decisions can instead be re-ranked by a fitted linear score
// (RerankModel, set_rerank): no rollouts are played, and each candidate scores
// w[model] . rerank_features(...), the first of equal scores winning. And with
// set_dump, every re-ranked decision's candidates are written out as DistilRows (their
// features and the rollouts' mean return), the data the score is fitted to.
//
// Experiment 021: or by a rank network (net.hpp, set_rank_net) reading each candidate's
// settled board and rank_inputs: the same decisions and candidates, the highest output
// winning (the search's own choice on ties). The DistilRows also keep each candidate's
// board, the decision's pieces, lines and drought, and the means of the even and of the
// odd rollouts (two independent halves, to measure how noisy the mean is).
#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <vector>

#include "board.hpp"
#include "eval.hpp"
#include "net.hpp"
#include "search.hpp"
#include "value.hpp"

namespace fallgorithm {

// Experiment 018's re-rank features of one candidate, in this order: 1 if it is the
// search's own choice (else 0), the search's total (Searcher::Candidate::total; its own
// value instead when the total is not finite, which happens when the search finds some
// piece with no placement), 1 if that total includes the extra ply, 1 if it was not
// finite, the candidate's own value (value_of, as the rollouts' return starts), four
// flags for 1, 2, 3 and 4 cleared rows, and value.hpp's 18 board features of the
// settled board.
constexpr int rerank_features_count = 9 + board_features;
// One weight vector for the decisions with the preview known (Experiment 016's band),
// one for the commit decision below the double killscreen and one from it on.
constexpr int rerank_models = 3;
constexpr int rerank_weights = rerank_models * rerank_features_count;

struct RerankModel {
    std::array<double, rerank_weights> weights{};
};

inline int rerank_model(bool preview, int level) {
    return preview ? 0 : level < killscreen_level ? 1 : 2;
}

inline std::array<double, rerank_features_count> rerank_features(
    bool searched, const Searcher::Candidate& candidate, double own) {
    std::array<double, rerank_features_count> x{};
    const bool finite = std::isfinite(candidate.total);
    x[0] = searched ? 1.0 : 0.0;
    x[1] = finite ? candidate.total : own;
    x[2] = candidate.deep ? 1.0 : 0.0;
    x[3] = finite ? 0.0 : 1.0;
    x[4] = own;
    if (candidate.cleared > 0) {
        x[4 + candidate.cleared] = 1.0;
    }
    const auto board = board_feature_values(candidate.settled);
    for (int index = 0; index < board_features; ++index) {
        x[9 + index] = board[index];
    }
    return x;
}

// One candidate of a re-ranked decision: the model it belongs to, the level, its place
// in the search's order, the rollouts' mean return, and its features; and (Experiment
// 021) its settled board, the means of the even and the odd rollouts, the current and the
// preview piece (-1: not known), and the lines and drought before the placement.
struct DistilRow {
    int model, level, rank;
    double mean;
    std::array<double, rerank_features_count> x;
    Columns settled;
    double mean_even, mean_odd;
    int piece, next, lines, drought;
};

// Experiment 021's rank network inputs after the 200 cells, in this order: the rerank
// features, the model (one-hot), the current piece (one-hot), the preview (one-hot; all
// 0 when not known), the lines left before ``line_cap`` after the candidate's clear (in
// hundreds, 0 at least), the level / 10 and the drought (before the placement).
static_assert(rank_dense == rerank_features_count + rerank_models + 2 * piece_types + 3);

inline std::array<float, rank_dense> rank_inputs(
    int model, int piece, int next, int lines_after, int line_cap, int level, int drought,
    const std::array<double, rerank_features_count>& x) {
    std::array<float, rank_dense> out{};
    for (int k = 0; k < rerank_features_count; ++k) {
        out[k] = static_cast<float>(x[k]);
    }
    int at = rerank_features_count;
    out[at + model] = 1.0f;
    at += rerank_models;
    out[at + piece] = 1.0f;
    at += piece_types;
    if (next >= 0) {
        out[at + next] = 1.0f;
    }
    at += piece_types;
    out[at] = static_cast<float>(std::max(0, line_cap - lines_after)) / 100.0f;
    out[at + 1] = static_cast<float>(level) / 10.0f;
    out[at + 2] = static_cast<float>(drought);
    return out;
}

class RolloutSearcher {
public:
    RolloutSearcher() = default;
    RolloutSearcher(const Searcher& searcher, const Params& params)
        : searcher_(searcher), policy_(searcher), params_(params) {}

    // Experiment 018: re-rank by ``model`` instead of rollouts (nullptr: rollouts).
    void set_rerank(const RerankModel* model) { rerank_ = model; }
    // Experiment 018: append every rollout-ranked decision's candidates to ``rows``.
    void set_dump(std::vector<DistilRow>* rows) { dump_ = rows; }
    // Experiment 021: re-rank by the rank network ``net`` (nullptr: rollouts), its lines
    // left counted to ``line_cap``.
    void set_rank_net(const ValueNetwork* net, int line_cap) {
        rank_net_ = net;
        line_cap_ = line_cap;
    }

    bool search(const Position& position, Choice& choice) {
        if (!searcher_.search(position, choice)) {
            return false;
        }
        const bool preview = position.next_piece >= 0;
        const int from = preview ? params_.rollout_from_level : params_.commit_rollout_from_level;
        const int to = preview ? params_.rollout_to_level : params_.commit_rollout_to_level;
        const int beam = preview ? params_.rollout_beam : params_.commit_rollout_beam;
        int count = preview ? params_.rollout_count : params_.commit_rollout_count;
        int depth = preview ? params_.rollout_depth : params_.commit_rollout_depth;
        if (!preview && position.level >= killscreen_level) {  // Experiment 019
            count = params_.killscreen_rollout_count > 0 ? params_.killscreen_rollout_count : count;
            depth = params_.killscreen_rollout_depth > 0 ? params_.killscreen_rollout_depth : depth;
        }
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
        const int phase =
            phase_of(params_, position.level, position.drought, position.columns);
        const int model = rerank_model(preview, position.level);
        if (rank_net_) {
            // As the linear re-ranker below: the search's own choice wins ties.
            int best = searcher_.chosen();
            bool have_best = false;
            double best_score = 0.0;
            for (const Searcher::Candidate& candidate : candidates_) {
                const double own = value_of(
                    params_, phase, candidate.cleared, candidate.settled,
                    level_for_lines(position.lines + candidate.cleared, position.start_level));
                const bool searched = candidate.order == searcher_.chosen();
                const auto dense = rank_inputs(
                    model, position.piece, position.next_piece,
                    position.lines + candidate.cleared, line_cap_, position.level,
                    position.drought, rerank_features(searched, candidate, own));
                const double score = rank_forward(*rank_net_, candidate.settled, dense.data());
                if (!have_best || score > best_score || (score == best_score && searched)) {
                    best = candidate.order;
                    best_score = score;
                    have_best = true;
                }
            }
            if (best == searcher_.chosen()) {
                return true;
            }
            return searcher_.choose(best, choice);
        }
        if (rerank_) {
            // The search's own choice wins unless another candidate scores higher (so
            // all-zero weights play the Searcher's game); among others, the first.
            int best = searcher_.chosen();
            bool have_best = false;
            double best_score = 0.0;
            for (const Searcher::Candidate& candidate : candidates_) {
                const double own = value_of(
                    params_, phase, candidate.cleared, candidate.settled,
                    level_for_lines(position.lines + candidate.cleared, position.start_level));
                const bool searched = candidate.order == searcher_.chosen();
                const auto x = rerank_features(searched, candidate, own);
                double score = 0.0;
                for (int k = 0; k < rerank_features_count; ++k) {
                    score += rerank_->weights[model * rerank_features_count + k] * x[k];
                }
                if (!have_best || score > best_score || (score == best_score && searched)) {
                    best = candidate.order;
                    best_score = score;
                    have_best = true;
                }
            }
            if (best == searcher_.chosen()) {
                return true;  // ``choice`` is already the search's
            }
            return searcher_.choose(best, choice);
        }
        draw_sequences(position, count, depth);
        int best = 0;
        double best_mean = 0.0;
        for (int index = 0; index < static_cast<int>(candidates_.size()); ++index) {
            const Searcher::Candidate& candidate = candidates_[index];
            const int lines = position.lines + candidate.cleared;
            const double first = value_of(params_, phase, candidate.cleared, candidate.settled,
                                          level_for_lines(lines, position.start_level));
            double total = 0.0, halves[2] = {0.0, 0.0};
            for (std::size_t at = 0; at < sequences_.size(); ++at) {
                double value = 0.0;
                if (!rollout(position, candidate.settled, lines, sequences_[at], depth, value)) {
                    return false;
                }
                total += first + value;
                halves[at % 2] += first + value;
            }
            const double mean = total / static_cast<double>(sequences_.size());
            if (dump_) {
                const double even = static_cast<double>((sequences_.size() + 1) / 2);
                const double odd = static_cast<double>(sequences_.size() / 2);
                dump_->push_back({model, position.level, index, mean,
                                  rerank_features(candidate.order == searcher_.chosen(),
                                                  candidate, first),
                                  candidate.settled, halves[0] / even,
                                  odd > 0 ? halves[1] / odd : halves[0] / even, position.piece,
                                  position.next_piece, position.lines, position.drought});
            }
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
    const RerankModel* rerank_ = nullptr;
    const ValueNetwork* rank_net_ = nullptr;
    int line_cap_ = 0;
    std::vector<DistilRow>* dump_ = nullptr;
    Choice choice_;
    std::vector<Searcher::Candidate> candidates_;
    std::vector<std::vector<int>> sequences_;
};

}  // namespace fallgorithm
