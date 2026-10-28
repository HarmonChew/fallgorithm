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

#if defined(_WIN32)
#define FN_API extern "C" __declspec(dllexport)
#else
#define FN_API extern "C" __attribute__((visibility("default")))
#endif

using namespace fallgorithm;

namespace {

constexpr int abi_version = 6;

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
    return value_of(*params, phase, cleared, load_columns(columns));
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
        config.ruleset = blocks::ruleset_from_name(ruleset);
        const std::string mode_name(mode);
        if (mode_name == "endless") {
            config.mode = blocks::Mode::Endless;
        } else if (mode_name == "challenge") {
            config.mode = blocks::Mode::Challenge;
        } else {
            return -1;
        }
        config.start_level = start_level;
        config.height = height;
        config.seed = static_cast<std::uint16_t>(seed);
        blocks::Game game(config);
        const std::uint64_t initial_hash = game.state_hash();
        Agent agent(*params, interval, reaction);
        std::vector<std::uint8_t> played;
        played.reserve(static_cast<std::size_t>(frame_cap));
        GameResult result;
        if (!play_game(game, agent, line_cap, frame_cap, played, result)) {
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
        return 0;
    } catch (const std::exception&) {
        return -1;
    }
}
