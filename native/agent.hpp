// benchplan.BenchAgent.act with reachplan.ReachAgent._decide, and one whole game, in C++.
//
// The agent plays one frame at a time on the engine's own blocks::Game, exactly as
// the Python agent plays through the binding: commit at a spawn with the preview
// unknown, adjust at the reaction frame with it known (or one full search at the
// spawn when the reaction time is 0), and follow the chosen placement's masks.
#pragma once

#include <algorithm>
#include <cstdint>
#include <string>
#include <vector>

#include <blocks/game.hpp>

#include "board.hpp"
#include "search.hpp"
#include "value.hpp"

namespace fallgorithm {

// pathaware.grid_columns(wellplan.visible_grid(state.board)): the twenty visible
// rows only; board row r is model row r + 2.
inline Columns visible_columns(const blocks::State& state) {
    Columns columns{};
    for (int row = 0; row < height; ++row) {
        for (int column = 0; column < width; ++column) {
            if (state.board[row * width + column]) {
                columns[column] |= 1u << (row + hidden_rows);
            }
        }
    }
    return columns;
}

// ``Search`` is search.hpp's Searcher (reach_plan) or value.hpp's ValueSearcher.
template <class Search>
class BasicAgent {
public:
    // ``interval`` and ``reaction`` are limits.Limits' tap_interval and
    // reaction_frames (computed in Python, whose round() they need).
    BasicAgent(const Search& searcher, int interval, int reaction)
        : searcher_(searcher), interval_(interval), reaction_(reaction) {}

    // Experiment 013's self-play exploration (off unless set): the first
    // ``start_pieces`` pieces, and after them each piece with probability ``rate``, play
    // a uniformly random reachable placement instead, and skip that piece's adjust
    // search. A splitmix64 stream from ``seed`` decides.
    void set_explore(double rate, int start_pieces, std::uint64_t seed) {
        explore_rate_ = rate;
        explore_start_ = start_pieces;
        explore_state_ = seed;
    }

    // BenchAgent.act. Returns false only if a walk back lost its path.
    bool act(const blocks::Game& game, std::uint8_t& mask) {
        const blocks::State& state = game.state();
        mask = 0;
        if (state.phase != blocks::Phase::Active || game.terminal()) {
            return true;
        }
        const bool current_is_i = state.current == blocks::Piece::I;
        const bool preview_is_i = state.next == blocks::Piece::I;
        if (static_cast<long long>(state.piece_count) != piece_count_) {
            piece_count_ = state.piece_count;
            frame_ = 0;
            shift_wait_ = rotate_wait_ = 0;
            have_target_ = false;
            exploring_ = false;
            pieces += 1;
            drought_before_ = drought_;
            if (reaction_ == 0) {
                drought_ = current_is_i || preview_is_i ? 0 : drought_before_ + 1;
                if (!decide(game, true)) {
                    return false;
                }
            } else {
                drought_ = current_is_i ? 0 : drought_before_ + 1;
                if (!decide(game, false)) {
                    return false;
                }
            }
        } else if (reaction_ > 0 && frame_ == reaction_ && !exploring_) {
            adjusts += 1;
            drought_ = current_is_i || preview_is_i ? 0 : drought_before_ + 1;
            if (!decide(game, true)) {
                return false;
            }
        }
        const int index = frame_ - base_;
        mask = index < static_cast<int>(masks_.size()) ? masks_[index] : 0;
        shift_wait_ = mask & (press_left | press_right) ? interval_ - 1 : std::max(0, shift_wait_ - 1);
        rotate_wait_ = mask & (press_cw | press_ccw) ? interval_ - 1 : std::max(0, rotate_wait_ - 1);
        frame_ += 1;
        return true;
    }

    int pieces = 0, adjusts = 0, switches = 0, explored = 0;

private:
    // ReachAgent._decide. A switch is a change of (orientation, x); y is not compared.
    bool decide(const blocks::Game& game, bool preview_known) {
        const blocks::State& state = game.state();
        const Position position{
            visible_columns(state),
            static_cast<int>(state.current),
            preview_known ? static_cast<int>(state.next) : -1,
            Flight{state.orientation, state.x, state.y, state.gravity_counter,
                   state.first_delay_remaining, shift_wait_, rotate_wait_},
            drought_,
            state.level,
            state.lines,
            game.config().start_level,
            game.config().ruleset == blocks::RulesetId::ClassicNtscDoubleKillscreen,
            interval_};
        if (!searcher_.search(position, choice_)) {
            return false;
        }
        if (!have_target_ && (pieces <= explore_start_ ||
                              (explore_rate_ > 0.0 &&
                               static_cast<double>(next_random() >> 11) * 0x1.0p-53 <
                                   explore_rate_))) {
            exploring_ = true;
            explored += 1;
            if (!searcher_.random_choice(next_random(), choice_)) {
                return false;
            }
        }
        if (have_target_ && (!choice_.found || choice_.orientation != target_orientation_ ||
                             choice_.x != target_x_)) {
            switches += 1;
        }
        have_target_ = choice_.found;
        target_orientation_ = choice_.orientation;
        target_x_ = choice_.x;
        masks_ = choice_.found ? choice_.masks : std::vector<std::uint8_t>{};
        base_ = frame_;
        return true;
    }

    std::uint64_t next_random() {  // splitmix64
        std::uint64_t z = (explore_state_ += 0x9e3779b97f4a7c15ull);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ull;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebull;
        return z ^ (z >> 31);
    }

    Search searcher_;
    Choice choice_;
    double explore_rate_ = 0.0;
    int explore_start_ = 0;
    std::uint64_t explore_state_ = 0;
    bool exploring_ = false;
    int interval_, reaction_;
    long long piece_count_ = -1;
    int frame_ = 0, base_ = 0, shift_wait_ = 0, rotate_wait_ = 0;
    int drought_ = 0, drought_before_ = 0;
    bool have_target_ = false;
    int target_orientation_ = 0, target_x_ = 0;
    std::vector<std::uint8_t> masks_;
};

using Agent = BasicAgent<Searcher>;

// experiment008._stop_reason's answers.
enum StopReason : int { game_over = 0, challenge_complete = 1, line_cap_reached = 2, frame_limit = 3 };

struct GameResult {
    int inputs = 0;
    std::uint64_t frames = 0;  // the engine's frame count, as experiment008._result reports it
    int reason = game_over;
    int pieces = 0, adjusts = 0, switches = 0, explored = 0;
    std::uint64_t score = 0;
    int lines = 0, level = 0;
};

// experiment010._play's loop: the stop rules are checked before each frame's input.
// Returns false only if the agent failed. With ``samples`` (Experiment 013), also
// keeps the board, lines and score at every spawn, so each board a piece left (and,
// for Experiment 020, the drought and the piece that left it).
template <class AnyAgent>
bool play_game(blocks::Game& game, AnyAgent& agent, int line_cap, int frame_cap,
               std::vector<std::uint8_t>& inputs, GameResult& result,
               std::vector<BoardSample>* samples = nullptr) {
    inputs.clear();
    long long sampled = -1;
    int last = -1, drought = 0;
    while (true) {
        const blocks::State& state = game.state();
        if (samples && state.phase == blocks::Phase::Active &&
            static_cast<long long>(state.piece_count) != sampled) {
            sampled = state.piece_count;
            samples->push_back({visible_columns(state), state.lines, state.score, drought, last});
            last = static_cast<int>(state.current);
            drought = next_drought(drought, last);
        }
        if (game.terminal()) {
            result.reason = state.phase == blocks::Phase::ChallengeComplete ? challenge_complete
                                                                             : game_over;
            break;
        }
        if (state.lines >= line_cap) {
            result.reason = line_cap_reached;
            break;
        }
        if (static_cast<int>(inputs.size()) >= frame_cap) {
            result.reason = frame_limit;
            break;
        }
        std::uint8_t mask = 0;
        if (!agent.act(game, mask)) {
            return false;
        }
        game.tick(mask);
        inputs.push_back(mask);
    }
    const blocks::State& state = game.state();
    result.inputs = static_cast<int>(inputs.size());
    result.frames = state.frame;
    result.pieces = agent.pieces;
    result.adjusts = agent.adjusts;
    result.switches = agent.switches;
    result.score = state.score;
    result.lines = state.lines;
    result.level = state.level;
    return true;
}

}  // namespace fallgorithm
