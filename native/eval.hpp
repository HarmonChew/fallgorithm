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
    int height_budget, survival_budget, survival_level, drought_bound;
};

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
inline double value_of(const Params& p, int phase, int cleared, const Columns& columns) {
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

// make_rules' phase_rule(level)(drought, columns)
inline int phase_of(const Params& p, int level, int drought, const Columns& columns) {
    const int budget = level >= p.survival_level ? p.survival_budget : p.height_budget;
    return drought < p.drought_bound && stack_height(columns) < budget ? build : spend;
}

}  // namespace fallgorithm
