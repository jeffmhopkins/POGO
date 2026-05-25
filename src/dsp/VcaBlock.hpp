#pragma once
#include <rack.hpp>

// Block VCA: pre-LP1 voltage-controlled amplifier.
// THAT 2180 in hardware; modeled as a linear VCA.
//
// amtParam [-1, +1]: bipolar attenuverter; center detent (0) = unity gain always.
// cvV      [0,10]  : CV input (normally mod bus or envelope).
//
// Gain law (spec Phase 1 edge cases):
//   AMT = 0        → G = 1.0  (unity, CV has no effect)
//   AMT = +1, CV=0 → G = 0.0  (muted)
//   AMT = +1, CV=10→ G = 1.0  (accent: signal follows envelope)
//   AMT = -1, CV=0 → G = 1.0  (full through when envelope low)
//   AMT = -1, CV=10→ G = 0.0  (duck: signal dips when envelope high)
struct VcaBlock {
	static float process(float v, float amtParam, float cvV) {
		float normCV = clamp(cvV, 0.f, 10.f) / 10.f;
		// Positive AMT: raise = (1 - normCV), so CV=0→G=0, CV=10→G=1 (accent)
		// Negative AMT: raise = normCV,        so CV=0→G=1, CV=10→G=0 (duck)
		float mod = (amtParam >= 0.f) ? (1.f - normCV) : normCV;
		float g   = clamp(1.f - std::abs(amtParam) * mod, 0.f, 1.f);
		return v * g;
	}
};
