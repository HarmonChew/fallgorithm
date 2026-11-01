// Experiment 025, roadmap step 1: one agent that plays one policy below a switch level
// and the other from it on. Policy V is Experiment 023's value agent (netsearch.hpp's
// NetSearcher, no prefilter); policy H is 017's agent (rollout.hpp's RolloutSearcher over
// a Searcher with the extra ply and NES odds). ``v_first`` says which comes first: V
// before ``switch_level`` and H from it on, or the reverse. The level is read from the
// position at every decision.
//
// Both searchers are stateless across decisions apart from their own scratch (the
// rollouts' draws come from a stream seeded by the position, rollout.hpp), so a game stays
// a pure function of its seed and each policy plays exactly as it does alone.
//
// The commit (at the spawn) and the adjust (at the reaction frame) are separate calls.
// The level cannot change within a piece, so both decisions of a piece go to the same
// policy; the rule is applied per call anyway and does not rely on that.
//
// BasicAgent copies the searcher. A copy is safe: both members are copyable values and the
// NetSearcher's pointer to the network stays valid as long as the caller's network
// outlives the game.
#pragma once

#include <cstdint>

#include "netsearch.hpp"
#include "rollout.hpp"

namespace fallgorithm {

class HybridSearcher {
public:
    HybridSearcher(const RolloutSearcher& rollouts, const NetSearcher& net, bool v_first,
                   int switch_level)
        : rollouts_(rollouts), net_(net), v_first_(v_first), switch_level_(switch_level) {}

    bool search(const Position& position, Choice& choice) {
        last_level_ = position.level;
        return use_net(position.level) ? net_.search(position, choice)
                                       : rollouts_.search(position, choice);
    }

    // Exploration is not used by Experiment 025. For completeness: the policy that played
    // the last decision seen (the first policy before any).
    bool random_choice(std::uint64_t pick, Choice& choice) {
        return use_net(last_level_) ? net_.random_choice(pick, choice)
                                    : rollouts_.random_choice(pick, choice);
    }

private:
    // V plays below the switch level when it is first, from it on when it is second.
    bool use_net(int level) const { return v_first_ == (level < switch_level_); }

    RolloutSearcher rollouts_;
    NetSearcher net_;
    bool v_first_;
    int switch_level_;
    int last_level_ = -1;
};

}  // namespace fallgorithm
