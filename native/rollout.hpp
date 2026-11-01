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
//
// Experiment 021 step 4: the rollouts' own placements can be re-ranked by a rank network
// too (set_rollout_net): after the policy's search, its rollout_beam best options are
// scored as the rank agent scores a decision's, up to ``to_level``. Every rollout
// placement knows its preview; above rollout_to_level (where the network only learnt the
// commit decision) it is scored by the commit model with the preview hidden. Off (no
// network), the rollouts are 017's.
//
// Experiment 021 step 4b: or the rollout-ranked decision's own pick blends the two
// (set_blend): each candidate scores its rollouts' mean plus weight[model] times the rank
// network's output (both in the rollouts' units), the first of equal scores winning.
// With all weights 0 the pick is 017's.
//
// Experiment 022: from ``from_level`` on (set_playout), the commit decision's candidates
// (the same commit_rollout_beam best) are scored by playouts to the end of the game
// instead: ``count`` games from each candidate's board, every piece drawn with the NES odds
// and placed as the fast agent places it at a commit decision (the commit search, preview
// hidden, from the spawn; re-ranked by the rank network when one is given, as the rank
// agent does), until a piece has no placement or the lines reach ``line_cap``. A playout's
// return is the real points its clears earn, the candidate's own included, in units of a
// Tetris at level 18 (points_unit); the best mean wins (the first of equal means). The same
// piece sequences are used for every candidate, each drawn from its own splitmix64 stream
// seeded by the position, so a game stays a pure function of its seed.
//
// Experiment 022 step 3: or (count 0) the same decision is re-ranked by a killscreen
// network (set_killscreen_net) fitted to those playouts' means: the highest output among
// the same candidates, the search's own choice winning ties. The playouts' own placements
// use the playout network (set_playout's ``net``), so a network fitted on one round's
// playouts can place the next round's.
//
// Experiment 023 milestone 2: from ``from_level`` on (set_leaf_net), the rollout-ranked
// decisions keep their candidates, sequences and placements, but a rollout's return is
// the real points of its clears (the candidate's own included) plus the value network's
// value (netsearch.hpp's net_value) of the board it ends on, after ``depth`` pieces or at
// the line cap; a rollout that tops out ends with its points alone (the game is over).
#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <vector>

#include "board.hpp"
#include "eval.hpp"
#include "net.hpp"
#include "netsearch.hpp"
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
    // Experiment 021 step 4: the rollouts' placements re-ranked by ``net`` up to level
    // ``to_level`` (nullptr: the policy's search alone), its lines left counted to
    // ``line_cap``.
    void set_rollout_net(const ValueNetwork* net, int line_cap, int to_level) {
        rollout_net_ = net;
        rollout_line_cap_ = line_cap;
        rollout_net_to_level_ = to_level;
    }
    // Experiment 021 step 4b: the rollout-ranked pick by the mean plus ``weights[model]``
    // times ``net``'s output (nullptr: the mean alone), its lines left counted to
    // ``line_cap``.
    void set_blend(const ValueNetwork* net, int line_cap,
                   const std::array<double, rerank_models>& weights) {
        blend_net_ = net;
        blend_line_cap_ = line_cap;
        blend_weights_ = weights;
    }

    // Experiment 022: from level ``from_level`` on, the commit decision by ``count``
    // playouts to ``line_cap`` (``count`` 0: off, or the killscreen network), placed by
    // the rank network ``net``'s picks (nullptr: the commit search alone).
    void set_playout(const ValueNetwork* net, int line_cap, int from_level, int count) {
        playout_net_ = net;
        playout_line_cap_ = line_cap;
        playout_from_level_ = from_level;
        playout_count_ = count;
    }

    // Experiment 023 milestone 2: from level ``from_level`` on, the rollout-ranked
    // decisions score each rollout by real points (the option's clear and the rollout's)
    // plus the value network ``net``'s value of the board it ends on, a rollout that tops
    // out by its points alone; a rollout stops at ``line_cap``. The rollouts' placements
    // are still the Searcher's. (nullptr: 017's return, the summed hand values.)
    void set_leaf_net(const ValueNetwork* net, int line_cap, int from_level) {
        leaf_net_ = net;
        leaf_line_cap_ = line_cap;
        leaf_from_level_ = from_level;
    }

    // Experiment 022 step 3: from set_playout's ``from_level`` on, with ``count`` 0, the
    // commit decision re-ranked by ``net`` (nullptr: as without it).
    void set_killscreen_net(const ValueNetwork* net) { killscreen_net_ = net; }

    // Experiment 022's counts: playouts played, their placements, and playouts stopped
    // by playout_max_pieces before the game ended (expected 0).
    long long playouts = 0, playout_pieces = 0, playouts_cut = 0;

    bool search(const Position& position, Choice& choice) {
        if (!searcher_.search(position, choice)) {
            return false;
        }
        const bool preview = position.next_piece >= 0;
        if (!preview && position.level >= playout_from_level_ &&
            (playout_count_ > 0 || killscreen_net_)) {
            return playout_search(position, choice);
        }
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
            const int best = rank_pick(searcher_, *rank_net_, line_cap_, position, model,
                                       position.next_piece, phase, candidates_, params_);
            if (best == searcher_.chosen()) {
                return true;  // ``choice`` is already the search's
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
        const bool leaf = leaf_net_ && position.level >= leaf_from_level_;
        int best = 0;
        double best_mean = 0.0;
        for (int index = 0; index < static_cast<int>(candidates_.size()); ++index) {
            const Searcher::Candidate& candidate = candidates_[index];
            const int lines = position.lines + candidate.cleared;
            const double first =
                leaf ? clear_reward(candidate.cleared, lines, position.start_level)
                     : value_of(params_, phase, candidate.cleared, candidate.settled,
                                level_for_lines(lines, position.start_level));
            double total = 0.0, halves[2] = {0.0, 0.0};
            for (std::size_t at = 0; at < sequences_.size(); ++at) {
                double value = 0.0;
                const bool ok =
                    leaf ? leaf_rollout(position, candidate.settled, lines, sequences_[at],
                                        depth, value)
                         : rollout(position, candidate.settled, lines, sequences_[at], depth,
                                   value);
                if (!ok) {
                    return false;
                }
                total += first + value;
                halves[at % 2] += first + value;
            }
            const double mean = total / static_cast<double>(sequences_.size());
            double score = mean;
            if (blend_net_ && blend_weights_[model] != 0.0) {
                score += blend_weights_[model] *
                         rank_score(*blend_net_, blend_line_cap_, position, model,
                                    position.next_piece, candidate,
                                    candidate.order == searcher_.chosen(), first);
            }
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
            if (index == 0 || score > best_mean) {
                best = index;
                best_mean = score;
            }
        }
        return searcher_.choose(candidates_[best].order, choice);
    }

    bool random_choice(std::uint64_t pick, Choice& choice) {
        return searcher_.random_choice(pick, choice);
    }

private:
    // A playout can never need more pieces than this (430 lines are 1,075 pieces).
    static constexpr int playout_max_pieces = 4000;

    // Experiment 022's commit decision: the commit search's commit_rollout_beam best
    // candidates, each scored by its mean playout return.
    bool playout_search(const Position& position, Choice& choice) {
        if (!choice.found || params_.commit_rollout_beam < 2) {
            return true;
        }
        searcher_.commit_candidates(params_.commit_rollout_beam, candidates_);
        if (candidates_.size() < 2) {
            return true;
        }
        const int phase = phase_of(params_, position.level, position.drought, position.columns);
        if (playout_count_ == 0) {  // step 3: the killscreen network
            const int best = rank_pick(searcher_, *killscreen_net_, playout_line_cap_, position,
                                       rerank_model(false, position.level), -1, phase,
                                       candidates_, params_);
            return best == searcher_.chosen() || searcher_.choose(best, choice);
        }
        seed_playouts(position);
        int best = 0;
        double best_mean = 0.0;
        for (int index = 0; index < static_cast<int>(candidates_.size()); ++index) {
            const Searcher::Candidate& candidate = candidates_[index];
            const int lines = position.lines + candidate.cleared;
            const double first =
                clear_reward(candidate.cleared, lines, position.start_level) / points_unit;
            double total = 0.0, halves[2] = {0.0, 0.0};
            for (int at = 0; at < playout_count_; ++at) {
                double value = 0.0;
                if (!playout(position, candidate.settled, lines, at, value)) {
                    return false;
                }
                total += first + value;
                halves[at % 2] += first + value;
            }
            const double mean = total / static_cast<double>(playout_count_);
            if (dump_) {
                const double own = value_of(params_, phase, candidate.cleared, candidate.settled,
                                            level_for_lines(lines, position.start_level));
                const double even = static_cast<double>((playout_count_ + 1) / 2);
                const double odd = static_cast<double>(playout_count_ / 2);
                dump_->push_back({rerank_model(false, position.level), position.level, index,
                                  mean,
                                  rerank_features(candidate.order == searcher_.chosen(),
                                                  candidate, own),
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

    // One playout (sequence ``at``) from ``columns`` with ``lines`` cleared, its points
    // after the candidate's own in ``total``. Returns false only if a search's walk back
    // failed.
    bool playout(const Position& start, Columns columns, int lines, int at, double& total) {
        total = 0.0;
        playouts += 1;
        int drought = start.drought, previous = start.piece;
        for (int step = 0; lines < playout_line_cap_; ++step) {
            if (step == playout_max_pieces) {
                playouts_cut += 1;
                return true;
            }
            const int piece = playout_piece(at, step, previous);
            previous = piece;
            drought = next_drought(drought, piece);
            const int level = level_for_lines(lines, start.start_level);
            const Position position{columns, piece, -1, Flight{}, drought, level, lines,
                                    start.start_level, start.double_killscreen,
                                    start.interval};
            if (!fast_commit(position, choice_)) {
                return false;
            }
            if (!choice_.found) {
                return true;  // topped out
            }
            playout_pieces += 1;
            const Settled settled =
                settle(columns, piece, choice_.orientation, choice_.x, choice_.y);
            lines += settled.cleared;
            total += clear_reward(settled.cleared, lines, start.start_level) / points_unit;
            columns = settled.columns;
        }
        return true;
    }

    // The fast agent's commit decision: the commit search, re-ranked by the playout
    // network over the same candidates as the rank agent's (its commit band).
    bool fast_commit(const Position& position, Choice& choice) {
        if (!policy_.search(position, choice)) {
            return false;
        }
        if (!playout_net_ || !choice.found || params_.commit_rollout_beam < 2 ||
            params_.commit_rollout_count < 1 || params_.commit_rollout_depth < 1 ||
            position.level < params_.commit_rollout_from_level ||
            position.level > params_.commit_rollout_to_level) {
            return true;
        }
        policy_.commit_candidates(params_.commit_rollout_beam, policy_candidates_);
        if (policy_candidates_.size() < 2) {
            return true;
        }
        const int phase = phase_of(params_, position.level, position.drought, position.columns);
        const int best = rank_pick(policy_, *playout_net_, playout_line_cap_, position,
                                   rerank_model(false, position.level), -1, phase,
                                   policy_candidates_, params_);
        return best == policy_.chosen() || policy_.choose(best, choice);
    }

    // One stream per playout, seeded by the position (as draw_sequences) and its index.
    void seed_playouts(const Position& position) {
        std::uint64_t state = 0x3c6ef372fe94f82bull;
        for (int column = 0; column < width; ++column) {
            state = mix(state ^ position.columns[column]);
        }
        state = mix(state ^ static_cast<std::uint64_t>(position.piece));
        state = mix(state ^ static_cast<std::uint64_t>(position.lines));
        streams_.resize(playout_count_);
        playout_sequences_.resize(playout_count_);
        for (int at = 0; at < playout_count_; ++at) {
            streams_[at] = mix(state ^ static_cast<std::uint64_t>(at));
            playout_sequences_[at].clear();
        }
    }

    // Playout ``at``'s piece ``step`` (drawn when first asked for, after ``previous``).
    int playout_piece(int at, int step, int previous) {
        std::vector<int>& sequence = playout_sequences_[at];
        if (static_cast<int>(sequence.size()) <= step) {
            sequence.push_back(draw(streams_[at], previous));
        }
        return sequence[step];
    }

    // The rank network's pick among ``candidates`` of ``searcher``'s last search (its
    // option index): the highest output, the search's own choice winning ties. ``next``
    // is the preview the network is shown (-1: none).
    static int rank_pick(const Searcher& searcher, const ValueNetwork& net, int line_cap,
                         const Position& position, int model, int next, int phase,
                         const std::vector<Searcher::Candidate>& candidates,
                         const Params& params) {
        int best = searcher.chosen();
        bool have_best = false;
        double best_score = 0.0;
        for (const Searcher::Candidate& candidate : candidates) {
            const double own = value_of(
                params, phase, candidate.cleared, candidate.settled,
                level_for_lines(position.lines + candidate.cleared, position.start_level));
            const bool searched = candidate.order == searcher.chosen();
            const double score =
                rank_score(net, line_cap, position, model, next, candidate, searched, own);
            if (!have_best || score > best_score || (score == best_score && searched)) {
                best = candidate.order;
                best_score = score;
                have_best = true;
            }
        }
        return best;
    }

    // The rank network's output for one candidate (``own``: its placement's value).
    static double rank_score(const ValueNetwork& net, int line_cap, const Position& position,
                             int model, int next, const Searcher::Candidate& candidate,
                             bool searched, double own) {
        const auto dense = rank_inputs(model, position.piece, next,
                                       position.lines + candidate.cleared, line_cap,
                                       position.level, position.drought,
                                       rerank_features(searched, candidate, own));
        return rank_forward(net, candidate.settled, dense.data());
    }

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
            const int phase = phase_of(params_, level, drought, columns);
            if (rollout_net_ && level <= rollout_net_to_level_ && params_.rollout_beam >= 2) {
                policy_.candidates(params_.rollout_beam, policy_candidates_);
                if (policy_candidates_.size() >= 2) {
                    const int model = rerank_model(level <= params_.rollout_to_level, level);
                    const int best = rank_pick(policy_, *rollout_net_, rollout_line_cap_,
                                               position, model, model == 0 ? next : -1,
                                               phase, policy_candidates_, params_);
                    if (best != policy_.chosen() && !policy_.choose(best, choice_)) {
                        return false;
                    }
                }
            }
            const Settled settled =
                settle(columns, piece, choice_.orientation, choice_.x, choice_.y);
            total += value_of(params_, phase, settled.cleared, settled.columns,
                              level_for_lines(lines + settled.cleared, start.start_level));
            lines += settled.cleared;
            columns = settled.columns;
        }
        return true;
    }

    // Experiment 023's rollout (set_leaf_net): the same placements as rollout() without
    // the rollout network, its return the points it clears plus the network's value of
    // the board it ends on (none after a top-out), stopping at the line cap.
    bool leaf_rollout(const Position& start, Columns columns, int lines,
                      const std::vector<int>& sequence, int depth, double& total) {
        total = 0.0;
        int drought = start.drought;
        // The network's drought counts the piece that left the board (the agent's
        // current piece at a commit decision; at an adjust with an I preview it differs
        // until that I is placed, the first rollout piece).
        int value_drought = start.drought, last = start.piece;
        for (int step = 0; step < depth && lines < leaf_line_cap_; ++step) {
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
                return true;  // topped out: no more points
            }
            const Settled settled =
                settle(columns, piece, choice_.orientation, choice_.x, choice_.y);
            lines += settled.cleared;
            total += clear_reward(settled.cleared, lines, start.start_level);
            columns = settled.columns;
            value_drought = next_drought(value_drought, piece);
            last = piece;
        }
        total += net_value(*leaf_net_, leaf_line_cap_, columns, lines, value_drought, last,
                           start.start_level);
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
    const ValueNetwork* rollout_net_ = nullptr;
    const ValueNetwork* blend_net_ = nullptr;
    int blend_line_cap_ = 0;
    std::array<double, rerank_models> blend_weights_{};
    int rollout_line_cap_ = 0, rollout_net_to_level_ = 0;
    std::vector<Searcher::Candidate> policy_candidates_;
    std::vector<DistilRow>* dump_ = nullptr;
    Choice choice_;
    std::vector<Searcher::Candidate> candidates_;
    std::vector<std::vector<int>> sequences_;
    const ValueNetwork* playout_net_ = nullptr;
    const ValueNetwork* killscreen_net_ = nullptr;
    const ValueNetwork* leaf_net_ = nullptr;
    int leaf_line_cap_ = 0, leaf_from_level_ = 0;
    int playout_line_cap_ = 0, playout_from_level_ = 0, playout_count_ = 0;
    std::vector<std::uint64_t> streams_;
    std::vector<std::vector<int>> playout_sequences_;
};

}  // namespace fallgorithm
