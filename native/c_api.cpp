// The C entry points src/block_stack_ai/native.py loads with ctypes.
//
// Bad arguments return -1 instead of reaching undefined behaviour, because the
// tests call these with generated input.
#include <cstdint>
#include <exception>
#include <string>
#include <vector>

#include "board.hpp"
#include "eval.hpp"
#include "reach.hpp"
#include "search.hpp"
#include "agent.hpp"
#include "rollout.hpp"
#include "value.hpp"
#include "net.hpp"
#include "netsearch.hpp"

#if defined(_WIN32)
#define FN_API extern "C" __declspec(dllexport)
#else
#define FN_API extern "C" __attribute__((visibility("default")))
#endif

using namespace fallgorithm;

namespace {

constexpr int abi_version = 16;

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
    return base_value(*params, phase, cleared, load_columns(columns));
}

// Experiment 014's value with the points term at ``level``, the level after the clear.
FN_API double fn_value_at(const Params* params, int phase, int cleared,
                          const std::uint32_t* columns, int level) {
    return value_of(*params, phase, cleared, load_columns(columns), level);
}

// Experiment 014: search.hpp's NES odds of ``piece`` after ``previous``.
FN_API double fn_nes_odds(int previous, int piece) {
    if (previous < 0 || previous >= piece_types || piece < 0 || piece >= piece_types) {
        return -1.0;
    }
    return nes_odds(previous, piece);
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

// Every placement reach.reachable finds, in its order, with each one's masks.
// ``flight`` is (orientation, x, y, gravity_counter, first_delay, shift_wait,
// rotate_wait). ``placements`` receives (orientation, x, y) per placement and
// ``masks`` all the masks back to back, ``mask_lengths`` saying how many each.
// Returns the count, -1 for bad arguments, -2 if a buffer is too small, -3 if the
// walk back lost its path.
FN_API int fn_reach(const std::uint32_t* columns, int piece, const int* flight, int period,
                    int rows, int interval, int* placements, int capacity, std::uint8_t* masks,
                    int mask_capacity, int* mask_lengths) {
    if (piece < 0 || piece >= piece_types || flight[0] < 0 ||
        flight[0] >= orientation_counts[piece] || flight[1] < -1 || flight[1] > width ||
        flight[2] < 0 || flight[2] >= grid_rows || flight[3] < 0 || flight[4] < 0 ||
        flight[5] < 0 || flight[6] < 0 || period < 1 || rows < 1 || rows > 2 || interval < 1) {
        return -1;
    }
    // Reused across calls, as the search reuses its own, so the tests also check
    // that every run starts from a clean state.
    thread_local ReachSearch search;
    search.run(load_columns(columns), piece,
               Flight{flight[0], flight[1], flight[2], flight[3], flight[4], flight[5], flight[6]},
               period, rows, interval);
    const int count = static_cast<int>(search.placements.size());
    if (count > capacity) {
        return -2;
    }
    std::vector<std::uint8_t> found;
    int used = 0;
    for (int index = 0; index < count; ++index) {
        const Reach& placement = search.placements[index];
        if (!search.masks(placement, found)) {
            return -3;
        }
        const int length = static_cast<int>(found.size());
        if (used + length > mask_capacity) {
            return -2;
        }
        placements[3 * index] = placement.orientation;
        placements[3 * index + 1] = placement.x;
        placements[3 * index + 2] = placement.y;
        mask_lengths[index] = length;
        for (int k = 0; k < length; ++k) {
            masks[used + k] = found[k];
        }
        used += length;
    }
    return count;
}

// One reachplan.search decision. ``position`` is (piece, next_piece or -1,
// orientation, x, y, gravity_counter, first_delay, shift_wait, rotate_wait, drought,
// level, lines, start_level, double_killscreen, tap_interval). Writes the chosen
// (orientation, x, y) and its masks. Returns 1, or 0 when no placement is reachable
// (the Python's None), -1 for bad arguments, -2 if ``masks`` is too small, -3 if the
// walk back lost its path.
FN_API int fn_decide(const Params* params, const std::uint32_t* columns, const int* position,
                     int* out, std::uint8_t* masks, int mask_capacity, int* mask_length) {
    const int* flight = position + 2;
    if (position[0] < 0 || position[0] >= piece_types || position[1] < -1 ||
        position[1] >= piece_types || flight[0] < 0 ||
        flight[0] >= orientation_counts[position[0]] || flight[1] < -1 || flight[1] > width ||
        flight[2] < 0 || flight[2] >= grid_rows || flight[3] < 0 || flight[4] < 0 ||
        flight[5] < 0 || flight[6] < 0 || position[9] < 0 || position[10] < 0 ||
        position[11] < 0 || position[12] < 0 || position[12] >= 20 || position[14] < 1) {
        return -1;
    }
    Position at{load_columns(columns), position[0], position[1],
                Flight{flight[0], flight[1], flight[2], flight[3], flight[4], flight[5], flight[6]},
                position[9], position[10], position[11], position[12], position[13] != 0,
                position[14]};
    thread_local Searcher searcher;
    searcher.set_params(*params);
    Choice choice;
    if (!searcher.search(at, choice)) {
        return -3;
    }
    if (!choice.found) {
        return 0;
    }
    const int length = static_cast<int>(choice.masks.size());
    if (length > mask_capacity) {
        return -2;
    }
    out[0] = choice.orientation;
    out[1] = choice.x;
    out[2] = choice.y;
    *mask_length = length;
    for (int k = 0; k < length; ++k) {
        masks[k] = choice.masks[k];
    }
    return 1;
}

// The search's unknown-piece average for one settled board, for the tests.
// ``position`` as fn_decide's (only level, double_killscreen and tap_interval are used).
FN_API double fn_unknown_average(const Params* params, const std::uint32_t* settled,
                                 const int* position, int base_drought, int unknown_level) {
    Position at{load_columns(settled), I, -1, Flight{}, 0, position[10], 0, 0,
                position[13] != 0, position[14]};
    thread_local Searcher searcher;
    searcher.set_params(*params);
    return searcher.expected_unknown(at, at.columns, base_drought, unknown_level);
}

namespace {

// The engine game the Python binding would create (ruleset and mode by name).
bool make_config(const char* ruleset, const char* mode, int start_level, int height, int seed,
                 blocks::Config& config) {
    config.ruleset = blocks::ruleset_from_name(ruleset);
    const std::string mode_name(mode);
    if (mode_name == "endless") {
        config.mode = blocks::Mode::Endless;
    } else if (mode_name == "challenge") {
        config.mode = blocks::Mode::Challenge;
    } else {
        return false;
    }
    config.start_level = start_level;
    config.height = height;
    config.seed = static_cast<std::uint16_t>(seed);
    return true;
}

// Plays one game and writes fn_play_game's ``inputs`` and ``out``. Returns 0, or -3.
template <class AnyAgent>
int run_game(const blocks::Config& config, AnyAgent& agent, int line_cap, int frame_cap,
             std::uint8_t* inputs, std::int64_t* out, std::vector<BoardSample>* samples,
             std::uint64_t& final_score) {
    blocks::Game game(config);
    const std::uint64_t initial_hash = game.state_hash();
    std::vector<std::uint8_t> played;
    played.reserve(static_cast<std::size_t>(frame_cap));
    GameResult result;
    if (!play_game(game, agent, line_cap, frame_cap, played, result, samples)) {
        return -3;
    }
    for (std::size_t index = 0; index < played.size(); ++index) {
        inputs[index] = played[index];
    }
    const std::int64_t values[] = {result.inputs, static_cast<std::int64_t>(result.frames),
                                   result.reason, result.pieces, result.adjusts,
                                   result.switches, static_cast<std::int64_t>(result.score),
                                   result.lines, result.level,
                                   static_cast<std::int64_t>(initial_hash),
                                   static_cast<std::int64_t>(game.state_hash())};
    for (int index = 0; index < 11; ++index) {
        out[index] = values[index];
    }
    final_score = result.score;
    return 0;
}

}  // namespace

// One whole reach_plan game on the engine (experiment010._play). The game is created
// as the Python binding creates it (ruleset and mode by name). ``inputs`` receives
// every frame's mask; ``out`` receives (inputs, engine frames, stop reason, pieces,
// adjusts, switches, score, lines, level, initial state hash, final state hash), the
// stop reason as agent.hpp's StopReason and the hashes as Game::state_hash's bits.
// Returns 0, -1 for bad arguments, -3 if the agent failed.
FN_API int fn_play_game(const Params* params, const char* ruleset, const char* mode,
                        int start_level, int height, int seed, int line_cap, int frame_cap,
                        int interval, int reaction, std::uint8_t* inputs, int capacity,
                        std::int64_t* out) {
    if (!ruleset || !mode || seed < 0 || seed > 0xffff || line_cap < 0 || frame_cap < 0 ||
        capacity < frame_cap || interval < 1 || reaction < 0) {
        return -1;
    }
    try {
        blocks::Config config;
        if (!make_config(ruleset, mode, start_level, height, seed, config)) {
            return -1;
        }
        Agent agent(Searcher(*params), interval, reaction);
        std::uint64_t final_score = 0;
        return run_game(config, agent, line_cap, frame_cap, inputs, out, nullptr, final_score);
    } catch (const std::exception&) {
        return -1;
    }
}

// Experiment 013's game: fn_play_game's arguments and outputs, with the agent chosen
// by ``agent``: 0 reach_plan with ``params``, 1 the same with the extra ply
// (search.hpp's depth check), 2 the learned value with ``weights`` (value.hpp's 114,
// and ``line_cap`` as the model's cap), 3 the extra ply with the NES odds (Experiment
// 014), 4 that agent with Experiment 016's rollout re-ranking (rollout.hpp, and 017's at
// the commit decision; no exploration, no ``gram``), 5 that agent with Experiment 018's
// re-ranker in place of the rollouts (``weights`` holds rollout.hpp's rerank_weights; the
// same rules as 4). When ``gram`` is given, the game's boards
// are added to value.hpp's least-squares sums (FitSums, add_game; only the line
// cap matters there): ``gram`` (114 x 114), ``target`` (114) and ``totals`` (count, sum,
// sum of squares of the targets). ``explore``, ``explore_start`` and ``explore_seed``
// are agent.hpp's exploration (0, 0 for every evaluated game).
FN_API int fn_play_game_ex(int agent_kind, const Params* params, const double* weights,
                           const char* ruleset, const char* mode, int start_level, int height,
                           int seed, int line_cap, int frame_cap, int interval, int reaction,
                           double explore, int explore_start, std::uint64_t explore_seed,
                           std::uint8_t* inputs,
                           int capacity, std::int64_t* out, double* gram, double* target,
                           double* totals) {
    if (!ruleset || !mode || seed < 0 || seed > 0xffff || line_cap < 0 || frame_cap < 0 ||
        capacity < frame_cap || interval < 1 || reaction < 0 || agent_kind < 0 ||
        agent_kind > 5 || (agent_kind != 2 && !params) ||
        ((agent_kind == 2 || agent_kind == 5) && !weights) || (gram && (!target || !totals)) ||
        (agent_kind >= 4 && (gram || explore != 0.0 || explore_start != 0)) || start_level < 0 ||
        start_level >= 20 ||
        !(explore >= 0.0 && explore <= 1.0) || explore_start < 0) {
        return -1;
    }
    try {
        blocks::Config config;
        if (!make_config(ruleset, mode, start_level, height, seed, config)) {
            return -1;
        }
        ValueModel model;
        model.line_cap = line_cap;
        if (weights && agent_kind == 2) {
            for (int index = 0; index < value_weights; ++index) {
                model.weights[index] = weights[index];
            }
        }
        std::vector<BoardSample> samples;
        std::vector<BoardSample>* keep = gram ? &samples : nullptr;
        std::uint64_t final_score = 0;
        int status = 0;
        if (agent_kind == 4 || agent_kind == 5) {
            Searcher searcher(*params);
            searcher.set_extra_ply(true);
            searcher.set_nes_odds(true);
            RerankModel rerank;
            RolloutSearcher rollouts(searcher, *params);
            if (agent_kind == 5) {
                for (int index = 0; index < rerank_weights; ++index) {
                    rerank.weights[index] = weights[index];
                }
                rollouts.set_rerank(&rerank);
            }
            BasicAgent<RolloutSearcher> agent(rollouts, interval, reaction);
            status = run_game(config, agent, line_cap, frame_cap, inputs, out, keep, final_score);
        } else if (agent_kind == 2) {
            BasicAgent<ValueSearcher> agent(ValueSearcher(model), interval, reaction);
            agent.set_explore(explore, explore_start, explore_seed);
            status = run_game(config, agent, line_cap, frame_cap, inputs, out, keep, final_score);
        } else {
            Searcher searcher(*params);
            searcher.set_extra_ply(agent_kind == 1 || agent_kind == 3);
            searcher.set_nes_odds(agent_kind == 3);
            Agent agent(searcher, interval, reaction);
            agent.set_explore(explore, explore_start, explore_seed);
            status = run_game(config, agent, line_cap, frame_cap, inputs, out, keep, final_score);
        }
        if (status || !gram) {
            return status;
        }
        FitSums sums;
        add_game(model, samples, final_score, start_level, sums);
        for (int index = 0; index < value_weights * value_weights; ++index) {
            gram[index] = sums.gram[index];
        }
        for (int index = 0; index < value_weights; ++index) {
            target[index] = sums.target[index];
        }
        totals[0] = sums.count;
        totals[1] = sums.total;
        totals[2] = sums.squares;
        return 0;
    } catch (const std::exception&) {
        return -1;
    }
}

// Experiment 018's data: agent 4's game (fn_play_game_ex's arguments and outputs, no
// exploration), and every rollout-ranked decision's candidates in ``rows``, each as
// (model, level, rank, rollouts' mean return, then rollout.hpp's rerank features), with
// their count in ``row_count``. Returns 0, -1 for bad arguments, -2 if ``rows`` is too
// small, -3 if the agent failed.
FN_API int fn_distil_game(const Params* params, const char* ruleset, const char* mode,
                          int start_level, int height, int seed, int line_cap, int frame_cap,
                          int interval, int reaction, std::uint8_t* inputs, int capacity,
                          std::int64_t* out, double* rows, int row_capacity, int* row_count) {
    if (!params || !rows || !row_count || !ruleset || !mode || seed < 0 || seed > 0xffff ||
        line_cap < 0 || frame_cap < 0 || capacity < frame_cap || interval < 1 ||
        reaction < 0 || start_level < 0 || start_level >= 20 || row_capacity < 0) {
        return -1;
    }
    try {
        blocks::Config config;
        if (!make_config(ruleset, mode, start_level, height, seed, config)) {
            return -1;
        }
        Searcher searcher(*params);
        searcher.set_extra_ply(true);
        searcher.set_nes_odds(true);
        std::vector<DistilRow> found;
        RolloutSearcher rollouts(searcher, *params);
        rollouts.set_dump(&found);
        BasicAgent<RolloutSearcher> agent(rollouts, interval, reaction);
        std::uint64_t final_score = 0;
        const int status =
            run_game(config, agent, line_cap, frame_cap, inputs, out, nullptr, final_score);
        if (status) {
            return status;
        }
        constexpr int stride = 4 + rerank_features_count;
        if (static_cast<long long>(found.size()) * stride > row_capacity) {
            return -2;
        }
        for (std::size_t index = 0; index < found.size(); ++index) {
            double* row = rows + index * stride;
            row[0] = found[index].model;
            row[1] = found[index].level;
            row[2] = found[index].rank;
            row[3] = found[index].mean;
            for (int k = 0; k < rerank_features_count; ++k) {
                row[4 + k] = found[index].x[k];
            }
        }
        *row_count = static_cast<int>(found.size());
        return 0;
    } catch (const std::exception&) {
        return -1;
    }
}

// Experiment 021's data: fn_distil_game's game, and every rollout-ranked decision's
// candidates in ``rows``, each as rank_distil_stride numbers: model, level, rank, the
// rollouts' mean, the even rollouts' mean, the odd ones', the current piece, the preview
// (-1: not known), the lines and the drought before the placement, the settled board's ten
// columns' visible rows (bit r is visible row r, row 0 at the top), then the rerank
// features. Returns as fn_distil_game.
constexpr int rank_distil_stride = 10 + width + rerank_features_count;

FN_API int fn_rank_distil_stride() { return rank_distil_stride; }

FN_API int fn_rank_distil_game(const Params* params, const char* ruleset, const char* mode,
                               int start_level, int height, int seed, int line_cap,
                               int frame_cap, int interval, int reaction, std::uint8_t* inputs,
                               int capacity, std::int64_t* out, double* rows, int row_capacity,
                               int* row_count) {
    if (!params || !rows || !row_count || !ruleset || !mode || seed < 0 || seed > 0xffff ||
        line_cap < 0 || frame_cap < 0 || capacity < frame_cap || interval < 1 ||
        reaction < 0 || start_level < 0 || start_level >= 20 || row_capacity < 0) {
        return -1;
    }
    try {
        blocks::Config config;
        if (!make_config(ruleset, mode, start_level, height, seed, config)) {
            return -1;
        }
        Searcher searcher(*params);
        searcher.set_extra_ply(true);
        searcher.set_nes_odds(true);
        std::vector<DistilRow> found;
        RolloutSearcher rollouts(searcher, *params);
        rollouts.set_dump(&found);
        BasicAgent<RolloutSearcher> agent(rollouts, interval, reaction);
        std::uint64_t final_score = 0;
        const int status =
            run_game(config, agent, line_cap, frame_cap, inputs, out, nullptr, final_score);
        if (status) {
            return status;
        }
        if (static_cast<long long>(found.size()) * rank_distil_stride > row_capacity) {
            return -2;
        }
        for (std::size_t index = 0; index < found.size(); ++index) {
            const DistilRow& f = found[index];
            double* row = rows + index * rank_distil_stride;
            const double head[10] = {static_cast<double>(f.model), static_cast<double>(f.level),
                                     static_cast<double>(f.rank), f.mean, f.mean_even,
                                     f.mean_odd, static_cast<double>(f.piece),
                                     static_cast<double>(f.next), static_cast<double>(f.lines),
                                     static_cast<double>(f.drought)};
            for (int k = 0; k < 10; ++k) {
                row[k] = head[k];
            }
            for (int column = 0; column < width; ++column) {
                row[10 + column] = static_cast<double>(f.settled[column] >> hidden_rows);
            }
            for (int k = 0; k < rerank_features_count; ++k) {
                row[10 + width + k] = f.x[k];
            }
        }
        *row_count = static_cast<int>(found.size());
        return 0;
    } catch (const std::exception&) {
        return -1;
    }
}

// Experiment 021: the rank network's outputs for ``count`` rows of fn_rank_distil_game's
// layout (for the tests); ``net`` is experiment021.export's bytes. Returns 0, or -1 for
// bad arguments.
FN_API int fn_rank_values(const unsigned char* net, int net_size, const double* rows, int count,
                          int line_cap, int start_level, double* out) {
    if (!net || net_size < 0 || !rows || count < 0 || !out || line_cap < 0 ||
        start_level < 0 || start_level >= 20) {
        return -1;
    }
    ValueNetwork network;
    if (!network.load(net, static_cast<std::size_t>(net_size), rank_magic, rank_inputs_count)) {
        return -1;
    }
    for (int index = 0; index < count; ++index) {
        const double* row = rows + static_cast<std::size_t>(index) * rank_distil_stride;
        const int model = static_cast<int>(row[0]), piece = static_cast<int>(row[6]);
        const int next = static_cast<int>(row[7]);
        if (model < 0 || model >= rerank_models || piece < 0 || piece >= piece_types ||
            next < -1 || next >= piece_types) {
            return -1;
        }
        Columns columns{};
        for (int column = 0; column < width; ++column) {
            columns[column] = static_cast<std::uint32_t>(row[10 + column]) << hidden_rows;
        }
        std::array<double, rerank_features_count> x{};
        int cleared = 0;
        for (int k = 0; k < rerank_features_count; ++k) {
            x[k] = row[10 + width + k];
        }
        for (int k = 1; k <= 4; ++k) {
            cleared += x[4 + k] != 0.0 ? k : 0;
        }
        const auto dense = rank_inputs(model, piece, next, static_cast<int>(row[8]) + cleared,
                                       line_cap, static_cast<int>(row[1]),
                                       static_cast<int>(row[9]), x);
        out[index] = rank_forward(network, columns, dense.data());
    }
    return 0;
}

// Experiment 021's agent: fn_distil_game's agent (017's) with the rank network ``net``
// in place of the rollouts, at the same decisions; fn_play_game_ex's outputs.
// Returns 0, -1 for bad arguments (or a ``net`` that is not a rank network), -3 if the
// agent failed.
FN_API int fn_rank_game(const unsigned char* net, int net_size, const Params* params,
                        const char* ruleset, const char* mode, int start_level, int height,
                        int seed, int line_cap, int frame_cap, int interval, int reaction,
                        std::uint8_t* inputs, int capacity, std::int64_t* out) {
    if (!net || net_size < 0 || !params || !ruleset || !mode || seed < 0 || seed > 0xffff ||
        line_cap < 0 || frame_cap < 0 || capacity < frame_cap || interval < 1 ||
        reaction < 0 || start_level < 0 || start_level >= 20) {
        return -1;
    }
    try {
        blocks::Config config;
        ValueNetwork network;
        if (!make_config(ruleset, mode, start_level, height, seed, config) ||
            !network.load(net, static_cast<std::size_t>(net_size), rank_magic,
                          rank_inputs_count)) {
            return -1;
        }
        Searcher searcher(*params);
        searcher.set_extra_ply(true);
        searcher.set_nes_odds(true);
        RolloutSearcher ranked(searcher, *params);
        ranked.set_rank_net(&network, line_cap);
        BasicAgent<RolloutSearcher> agent(ranked, interval, reaction);
        std::uint64_t final_score = 0;
        return run_game(config, agent, line_cap, frame_cap, inputs, out, nullptr, final_score);
    } catch (const std::exception&) {
        return -1;
    }
}

// Experiment 020's data: one game by agent 0, 1 or 3 of fn_play_game_ex (its arguments
// and outputs, exploration included, no ``weights`` or ``gram``), and every board a
// piece left (agent.hpp's samples, one per spawn) in ``rows``, each as dump_stride
// numbers: the ten columns' visible rows (bit r is visible row r, row 0 at the top), the
// lines, the score so far, the drought, the piece that left the board (-1 for the first
// board), then value.hpp's 18 board features. The game's final score is ``out``'s.
// Returns 0, -1 for bad arguments, -2 if ``rows`` is too small, -3 if the agent failed.
constexpr int dump_stride = width + 4 + board_features;

namespace {

// fn_dump_game's rows for ``samples``. Returns 0, or -2 if they do not fit.
int write_rows(const std::vector<BoardSample>& samples, std::int32_t* rows, int row_capacity,
               int* row_count) {
    if (static_cast<long long>(samples.size()) * dump_stride > row_capacity) {
        return -2;
    }
    for (std::size_t index = 0; index < samples.size(); ++index) {
        const BoardSample& sample = samples[index];
        std::int32_t* row = rows + index * dump_stride;
        for (int column = 0; column < width; ++column) {
            row[column] = static_cast<std::int32_t>(sample.columns[column] >> hidden_rows);
        }
        row[width] = sample.lines;
        row[width + 1] = static_cast<std::int32_t>(sample.score);  // ~6M at most by 430 lines
        row[width + 2] = sample.drought;
        row[width + 3] = sample.last;
        const auto f = board_feature_values(sample.columns);
        for (int k = 0; k < board_features; ++k) {
            row[width + 4 + k] = static_cast<std::int32_t>(f[k]);
        }
    }
    *row_count = static_cast<int>(samples.size());
    return 0;
}

}  // namespace

FN_API int fn_dump_stride() { return dump_stride; }

FN_API int fn_dump_game(int agent_kind, const Params* params, const char* ruleset,
                        const char* mode, int start_level, int height, int seed, int line_cap,
                        int frame_cap, int interval, int reaction, double explore,
                        int explore_start, std::uint64_t explore_seed, std::uint8_t* inputs,
                        int capacity, std::int64_t* out, std::int32_t* rows, int row_capacity,
                        int* row_count) {
    if (!params || !rows || !row_count || !ruleset || !mode || seed < 0 || seed > 0xffff ||
        line_cap < 0 || frame_cap < 0 || capacity < frame_cap || interval < 1 ||
        reaction < 0 || start_level < 0 || start_level >= 20 || row_capacity < 0 ||
        (agent_kind != 0 && agent_kind != 1 && agent_kind != 3) ||
        !(explore >= 0.0 && explore <= 1.0) || explore_start < 0) {
        return -1;
    }
    try {
        blocks::Config config;
        if (!make_config(ruleset, mode, start_level, height, seed, config)) {
            return -1;
        }
        Searcher searcher(*params);
        searcher.set_extra_ply(agent_kind != 0);
        searcher.set_nes_odds(agent_kind == 3);
        Agent agent(searcher, interval, reaction);
        agent.set_explore(explore, explore_start, explore_seed);
        std::vector<BoardSample> samples;
        std::uint64_t final_score = 0;
        const int status =
            run_game(config, agent, line_cap, frame_cap, inputs, out, &samples, final_score);
        if (status) {
            return status;
        }
        return write_rows(samples, rows, row_capacity, row_count);
    } catch (const std::exception&) {
        return -1;
    }
}

// Experiment 020: the value network's values, in points, of ``count`` boards (for the
// tests), each as fn_dump_game's row layout's first 14 numbers (columns' visible rows,
// lines, score, drought, last piece). ``net`` is experiment020.export's bytes. Returns 0,
// or -1 for bad arguments.
FN_API int fn_net_values(const unsigned char* net, int net_size, const std::int32_t* rows,
                         int count, int line_cap, int start_level, double* out) {
    if (!net || net_size < 0 || !rows || count < 0 || !out || start_level < 0 ||
        start_level >= 20 || line_cap < 0) {
        return -1;
    }
    ValueNetwork network;
    if (!network.load(net, static_cast<std::size_t>(net_size))) {
        return -1;
    }
    NetSearcher searcher(&network, line_cap);
    for (int index = 0; index < count; ++index) {
        const std::int32_t* row = rows + static_cast<std::size_t>(index) * dump_stride;
        Columns columns{};
        for (int column = 0; column < width; ++column) {
            columns[column] = static_cast<std::uint32_t>(row[column]) << hidden_rows;
        }
        if (row[width] < 0 || row[width + 3] < -1 || row[width + 3] >= piece_types) {
            return -1;
        }
        out[index] = searcher.value(columns, row[width], row[width + 2], row[width + 3],
                                    start_level);
    }
    return 0;
}

// Experiment 020's agent: one game by netsearch.hpp's search with the network ``net``
// (fn_dump_game's arguments and outputs otherwise, exploration included). With
// ``prefilter`` above 0, the hand search with ``params`` keeps that many placements
// first. ``rows`` may be null; given, it receives the game's boards as fn_dump_game's.
// Returns 0, -1 for bad arguments, -2 if ``rows`` is too small, -3 if the agent failed.
FN_API int fn_net_game(const unsigned char* net, int net_size, const Params* params,
                       int prefilter, const char* ruleset,
                       const char* mode, int start_level, int height, int seed, int line_cap,
                       int frame_cap, int interval, int reaction, double explore,
                       int explore_start, std::uint64_t explore_seed, std::uint8_t* inputs,
                       int capacity, std::int64_t* out, std::int32_t* rows, int row_capacity,
                       int* row_count) {
    if (!net || net_size < 0 || prefilter < 0 || (prefilter > 0 && !params) || !ruleset ||
        !mode || seed < 0 || seed > 0xffff ||
        line_cap < 0 || frame_cap < 0 || capacity < frame_cap || interval < 1 ||
        reaction < 0 || start_level < 0 || start_level >= 20 || (rows && !row_count) ||
        row_capacity < 0 || !(explore >= 0.0 && explore <= 1.0) || explore_start < 0) {
        return -1;
    }
    try {
        blocks::Config config;
        ValueNetwork network;
        if (!make_config(ruleset, mode, start_level, height, seed, config) ||
            !network.load(net, static_cast<std::size_t>(net_size))) {
            return -1;
        }
        BasicAgent<NetSearcher> agent(prefilter > 0
                                          ? NetSearcher(&network, line_cap, *params, prefilter)
                                          : NetSearcher(&network, line_cap),
                                      interval, reaction);
        agent.set_explore(explore, explore_start, explore_seed);
        std::vector<BoardSample> samples;
        std::uint64_t final_score = 0;
        const int status = run_game(config, agent, line_cap, frame_cap, inputs, out,
                                    rows ? &samples : nullptr, final_score);
        if (status || !rows) {
            return status;
        }
        return write_rows(samples, rows, row_capacity, row_count);
    } catch (const std::exception&) {
        return -1;
    }
}

// The 18 board features of value.hpp for one board (for the tests).
FN_API void fn_board_features(const std::uint32_t* columns, double* out) {
    const auto f = board_feature_values(load_columns(columns));
    for (int index = 0; index < board_features; ++index) {
        out[index] = f[index];
    }
}

// value.hpp's board_value and clear_reward (for the tests).
FN_API double fn_board_value(const double* weights, int line_cap, const std::uint32_t* columns,
                             int lines, int start_level) {
    ValueModel model;
    model.line_cap = line_cap;
    for (int index = 0; index < value_weights; ++index) {
        model.weights[index] = weights[index];
    }
    return board_value(model, load_columns(columns), lines, start_level);
}

FN_API double fn_clear_reward(int cleared, int lines_after, int start_level) {
    return clear_reward(cleared, lines_after, start_level);
}
