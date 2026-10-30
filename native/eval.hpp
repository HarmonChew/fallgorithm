// tunedplan.make_rules in C++: the plan value of a settled board and the phase rule.
//
// The sums are written in the Python's order, left to right, one operation at a
// time, so they round exactly as Python's floats do (see -ffp-contract=off in
// CMakeLists.txt).
#pragma once

#include "board.hpp"

#ifdef __FAST_MATH__
#error "fast-math reorders floating-point sums; the values would differ from the Python"
#endif

namespace fallgorithm {

// tunedplan.DEFAULTS, in that order; the whole numbers already resolved
// (tunedplan.resolve). native.py declares the same layout.
struct Params {
    double build_tetrises, build_premature_clear, build_holes, build_aggregate_height,
        build_bumpiness, build_max_height, build_reserve, build_overflow;
    double spend_lines_cleared, spend_holes, spend_aggregate_height, spend_bumpiness,
        spend_max_height, spend_row_transitions, spend_column_transitions, spend_edge_depth;
    // Experiment 014 (C++ only; the defaults 0 and -1 leave everything above unchanged):
    // the weight on a clear's real points, and the build budget from the killscreen.
    double clear_points;
    int height_budget, survival_budget, survival_level, drought_bound;
    int killscreen_budget;
    // Experiment 015 (search settings, not tuned; the defaults -1 and 0 leave the search
    // unchanged): from level ``commit_ply_level`` on, the commit search looks one unknown
    // piece further for its ``commit_beam`` best placements (search.hpp).
    int commit_ply_level, commit_beam;
    // Experiment 016 (search settings, not tuned; the defaults -1 and 0 leave the agent
    // unchanged): from ``rollout_from_level`` to ``rollout_to_level``, the decision with
    // the preview known re-ranks its ``rollout_beam`` best placements by ``rollout_count``
    // rollouts of ``rollout_depth`` pieces each; a rollout that tops out loses
    // ``rollout_death`` (rollout.hpp).
    int rollout_from_level, rollout_to_level, rollout_beam, rollout_count, rollout_depth,
        rollout_death;
};

// Experiment 014: the level where the double killscreen starts, and the NES points of
// a clear (before the (level + 1) factor).
constexpr int killscreen_level = 39;
constexpr double nes_points[5] = {0.0, 40.0, 100.0, 300.0, 1200.0};
// A Tetris at level 18 is worth 1.0 of ``clear_points``.
constexpr double points_unit = 1200.0 * 19.0;

// Experiment 014: the clear's real points at ``level``, the level after the clear (the
// engine updates the level, then scores), in units of a Tetris at level 18.
inline double points_of(int cleared, int level) {
    return nes_points[cleared] * (level + 1) / points_unit;
}

// wellplan.BUILD and wellplan.SPEND.
enum Phase : int { build = 0, spend = 1 };

// make_rules' clear_term
inline double clear_term(const Params& p, int cleared) {
    if (cleared == 4) {
        return p.build_tetrises;
    }
    if (cleared == 0) {
        return 0.0;
    }
    return p.build_premature_clear * (4 - cleared);
}

// make_rules' value_of
inline double base_value(const Params& p, int phase, int cleared, const Columns& columns) {
    if (phase == spend) {
        const Features f = column_features(columns);
        double score = p.spend_lines_cleared * cleared + p.spend_holes * f.holes +
                       p.spend_aggregate_height * f.aggregate_height +
                       p.spend_bumpiness * f.bumpiness + p.spend_max_height * f.max_height;
        // The Python only adds the extra features whose weight is not zero.
        if (p.spend_row_transitions != 0.0) {
            score += p.spend_row_transitions * row_transitions(columns);
        }
        if (p.spend_column_transitions != 0.0) {
            score += p.spend_column_transitions * column_transitions(columns);
        }
        if (p.spend_edge_depth != 0.0) {
            score += p.spend_edge_depth * edge_depth(columns);
        }
        return score;
    }
    const Features f = field_features(columns);
    return clear_term(p, cleared) + p.build_holes * f.holes +
           p.build_aggregate_height * f.aggregate_height + p.build_bumpiness * f.bumpiness +
           p.build_max_height * f.max_height + p.build_reserve * well_reserve(columns) +
           p.build_overflow * std::max(0, stack_height(columns) - p.height_budget);
}

// make_rules' value_of, plus Experiment 014's points term (only when its weight is
// not zero, so the sum rounds as before) at ``level``, the level after the clear.
inline double value_of(const Params& p, int phase, int cleared, const Columns& columns,
                       int level) {
    double value = base_value(p, phase, cleared, columns);
    if (p.clear_points != 0.0) {
        value += p.clear_points * points_of(cleared, level);
    }
    return value;
}

// make_rules' phase_rule(level)(drought, columns); from the killscreen, Experiment
// 014's own budget when it is set (not negative).
inline int phase_of(const Params& p, int level, int drought, const Columns& columns) {
    const int budget = level >= killscreen_level && p.killscreen_budget >= 0
                           ? p.killscreen_budget
                       : level >= p.survival_level ? p.survival_budget
                                                   : p.height_budget;
    return drought < p.drought_bound && stack_height(columns) < budget ? build : spend;
}

}  // namespace fallgorithm
