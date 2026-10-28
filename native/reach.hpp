// reach.py in C++: every placement the tap-limited player can reach.
//
// A line-by-line translation of reach._search and reach._walk_back; see reach.py for
// the model. One frame's live states are kept in a small vector *in insertion
// order*, because the Python keeps them in a dict and walks it in that order: the
// order decides which state is stored for a lock and which predecessor the walk
// back picks, so it decides the masks.
#pragma once

#include <algorithm>
#include <array>
#include <cstdint>
#include <vector>

#include "board.hpp"

namespace fallgorithm {

// pathaware's input bits.
constexpr std::uint8_t press_left = 1;
constexpr std::uint8_t press_right = 2;
constexpr std::uint8_t press_cw = 8;
constexpr std::uint8_t press_ccw = 16;

constexpr int stride = 13;  // reach.STRIDE: bit o * 13 + x + 1 is pose (o, x)
constexpr std::int64_t pose_mask = (std::int64_t{1} << (width + 2)) - 1;
// reach._WALLS: columns -4..-1 and 10.. (bit = column + 4); negative, as in Python.
constexpr std::int64_t walls = 0b1111 | (std::int64_t{-1} << 14);
constexpr int max_frames = 600;  // reach._MAX_FRAMES
constexpr int slice_rows = 32;   // the Python's 28 rows (22 + 6 of floor), padded with floor

// limits.Flight, without the fields reach.reachable ignores.
struct Flight {
    int orientation = 0;
    int x = 5;  // pathaware.SPAWN_X
    int y = 0;  // heuristic.SPAWN_ORIGIN_Y
    int gravity_counter = 0;
    int first_delay = 0;
    int shift_wait = 0;
    int rotate_wait = 0;
};

// One reachable lock placement and what the walk back needs to rebuild its inputs.
struct Reach {
    int orientation, x, y;
    int frame, bit, shift, rotate;
};

class ReachSearch {
public:
    // reach._search. Afterwards ``placements`` holds every distinct lock placement
    // in the Python's order (orientation, then x, then y).
    // ``record`` keeps the frames the walk back needs; a search whose masks are never
    // asked for (the later plies) can skip them.
    void run(const Columns& columns, int piece, const Flight& flight, int period, int rows,
             int interval, bool record = true) {
        piece_ = piece;
        count_ = orientation_counts[piece];
        interval_ = interval;
        placements.clear();
        layers_.clear();
        stored_.clear();
        fit_known_.fill(false);
        build_slices(columns);
        locked_.fill(0);

        int y = flight.y;
        int counter = flight.gravity_counter;
        int delay = flight.first_delay;
        current_.clear();
        current_.push_back({flight.shift_wait, flight.rotate_wait,
                            std::uint64_t{1} << (stride * flight.orientation + flight.x + 1)});
        for (int frame = 0; frame < max_frames; ++frame) {
            if (current_.empty()) {
                break;
            }
            if (record) {
                layers_.push_back({y, static_cast<int>(stored_.size()),
                                   static_cast<int>(current_.size())});
                stored_.insert(stored_.end(), current_.begin(), current_.end());
            }
            std::uint64_t here = fit(y);
            after_.clear();
            for (const State& state : current_) {
                const int idle_shift = state.shift ? state.shift - 1 : 0;
                const int idle_rotate = state.rotate ? state.rotate - 1 : 0;
                std::uint64_t moved[3] = {state.poses, 0, 0};
                int shifts[3] = {idle_shift, interval - 1, interval - 1};
                int moves = 1;
                if (state.shift == 0) {
                    moved[1] = (state.poses >> 1) & here;
                    moved[2] = (state.poses << 1) & here;
                    moves = 3;
                }
                for (int index = 0; index < moves; ++index) {
                    const std::uint64_t shifted = moved[index];
                    if (!shifted) {
                        continue;
                    }
                    add(shifts[index], idle_rotate, shifted);
                    if (state.rotate == 0 && count_ > 1) {
                        add(shifts[index], interval - 1, turn(shifted, 1) & here);
                        if (count_ == 4) {
                            add(shifts[index], interval - 1, turn(shifted, -1) & here);
                        }
                    }
                }
            }
            // Game::process_drop: the first-piece delay swallows frames, then gravity
            // tries ``rows`` downward moves every ``period`` frames.
            counter += 1;
            if (delay > 0) {
                delay -= 1;
            } else if (counter >= period) {
                counter = 0;
                for (int step = 0; step < rows; ++step) {
                    const std::uint64_t below = fit(y + 1);
                    here = fit(y);
                    std::size_t kept = 0;
                    for (std::size_t index = 0; index < after_.size(); ++index) {
                        State state = after_[index];
                        std::uint64_t stopped = state.poses & ~below;
                        if (stopped) {
                            stopped &= here;  // stuck in an overlapped spawn: a top-out
                            while (stopped) {
                                const int bit = std::countr_zero(stopped);
                                stopped &= stopped - 1;
                                lock(bit, y, frame, state);
                            }
                            state.poses &= below;
                        }
                        if (state.poses) {
                            after_[kept++] = state;
                        }
                    }
                    after_.resize(kept);
                    y += 1;
                }
            }
            current_.swap(after_);
        }
        std::sort(placements.begin(), placements.end(), [](const Reach& a, const Reach& b) {
            return a.bit != b.bit ? a.bit < b.bit : a.y < b.y;  // = (orientation, x, y)
        });
    }

    // reach._walk_back: the inputs, from the flight's next frame to the last press,
    // that lead to ``placement``. Returns false if the search lost its own path (or
    // was run without ``record``).
    bool masks(const Reach& placement, std::vector<std::uint8_t>& out) const {
        out.clear();
        int bit = placement.bit;
        int next_shift = placement.shift;
        int next_rotate = placement.rotate;
        if (placement.frame >= static_cast<int>(layers_.size())) {
            return false;
        }
        for (int index = placement.frame; index >= 0; --index) {
            const Layer& layer = layers_[index];
            const std::uint64_t here = fits_[layer.y];
            bool found = false;
            for (int k = 0; k < layer.count && !found; ++k) {
                const State& state = stored_[layer.first + k];
                const int shift_moves = state.shift == 0 ? 3 : 1;
                const int rotate_moves = state.rotate == 0 ? rotation_moves() : 1;
                for (int s = 0; s < shift_moves && !found; ++s) {
                    const int dx = s == 0 ? 0 : s == 1 ? -1 : 1;
                    const std::uint8_t shift_mask = s == 0 ? 0 : s == 1 ? press_left : press_right;
                    if (next_shift != (dx ? interval_ - 1 : std::max(0, state.shift - 1))) {
                        continue;
                    }
                    for (int r = 0; r < rotate_moves; ++r) {
                        const int step = r == 0 ? 0 : r == 1 ? 1 : -1;
                        const std::uint8_t rotate_mask = r == 0 ? 0 : r == 1 ? press_cw : press_ccw;
                        if (next_rotate != (step ? interval_ - 1 : std::max(0, state.rotate - 1))) {
                            continue;
                        }
                        int middle = bit;
                        if (step) {
                            if (!((here >> bit) & 1)) {
                                continue;
                            }
                            middle = std::countr_zero(turn(std::uint64_t{1} << bit, -step));
                        }
                        int before = middle;
                        if (dx) {
                            if (!((here >> middle) & 1)) {
                                continue;
                            }
                            before = middle - dx;
                        }
                        if ((state.poses >> before) & 1) {
                            out.push_back(shift_mask | rotate_mask);
                            bit = before;
                            next_shift = state.shift;
                            next_rotate = state.rotate;
                            found = true;
                            break;
                        }
                    }
                }
            }
            if (!found) {
                out.clear();
                return false;
            }
        }
        // The masks were collected last frame first: drop the idle frames after the
        // last press, then put them in order.
        std::size_t start = 0;
        while (start < out.size() && out[start] == 0) {
            ++start;
        }
        out.erase(out.begin(), out.begin() + static_cast<std::ptrdiff_t>(start));
        std::reverse(out.begin(), out.end());
        return true;
    }

    std::vector<Reach> placements;

private:
    struct State {
        int shift, rotate;
        std::uint64_t poses;
    };
    struct Layer {
        int y, first, count;
    };

    // reach._rotations: none for the O, clockwise only for I/S/Z, both for the rest.
    int rotation_moves() const { return count_ == 1 ? 1 : count_ == 2 ? 2 : 3; }

    // reach._turn
    std::uint64_t turn(std::uint64_t poses, int step) const {
        const int span = stride * count_;
        const std::uint64_t full = (std::uint64_t{1} << span) - 1;
        if (step == 1) {
            return ((poses << stride) | (poses >> (span - stride))) & full;
        }
        return ((poses >> stride) | (poses << (span - stride))) & full;
    }

    // after[key] = after.get(key, 0) | poses, keeping first-insertion order.
    void add(int shift, int rotate, std::uint64_t poses) {
        if (!poses) {
            return;
        }
        for (State& state : after_) {
            if (state.shift == shift && state.rotate == rotate) {
                state.poses |= poses;
                return;
            }
        }
        after_.push_back({shift, rotate, poses});
    }

    // locks.setdefault((bit, y), (frame, bit, key))
    void lock(int bit, int y, int frame, const State& state) {
        const std::uint64_t mark = std::uint64_t{1} << bit;
        if (locked_[y] & mark) {
            return;
        }
        locked_[y] |= mark;
        placements.push_back({bit / stride, bit % stride - 1, y, frame, bit, state.shift,
                              state.rotate});
    }

    // reach._row_slices
    void build_slices(const Columns& columns) {
        slices_.fill(-1);  // the floor
        for (int row = 0; row < grid_rows; ++row) {
            slices_[row] = walls;
        }
        for (int column = 0; column < width; ++column) {
            std::uint32_t bits = columns[column];
            while (bits) {
                const int row = std::countr_zero(bits);
                bits &= bits - 1;
                slices_[row] |= std::int64_t{1} << (column + 4);
            }
        }
    }

    // reach._fit_mask, remembered per row as the Python's ``fits`` dict is.
    std::uint64_t fit(int y) {
        if (!fit_known_[y]) {
            std::uint64_t mask = 0;
            for (int orientation = 0; orientation < count_; ++orientation) {
                std::int64_t blocked = 0;
                for (const Cell& cell : shapes[piece_][orientation]) {
                    const int row = y + cell.dy + hidden_rows;
                    // Arithmetic shift of a negative slice, as Python's >> is.
                    blocked |= (row < slice_rows ? slices_[row] : -1) >> (cell.dx + 3);
                }
                mask |= static_cast<std::uint64_t>(~blocked & pose_mask) << (stride * orientation);
            }
            fits_[y] = mask;
            fit_known_[y] = true;
        }
        return fits_[y];
    }

    int piece_ = 0;
    int count_ = 1;
    int interval_ = 2;
    std::array<std::int64_t, slice_rows> slices_{};
    std::array<std::uint64_t, slice_rows> fits_{};
    std::array<bool, slice_rows> fit_known_{};
    std::array<std::uint64_t, slice_rows> locked_{};
    std::vector<State> current_, after_, stored_;
    std::vector<Layer> layers_;
};

}  // namespace fallgorithm
