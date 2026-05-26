#pragma once
#include <rack.hpp>

// Block VCA: pre-LP1 voltage-controlled amplifier.
// THAT 2180 in hardware; modeled as a linear VCA.
//
// amtParam [-1, +1]: bipolar attenuverter; center detent (0) = unity gain always.
// cvV      [0,10]  : CV input (normally mod bus or envelope).
//                    5 V = unity at full CW; above 5 V saturates at G=1.
//
// Gain law:
//   AMT = 0        → G = 1.0  (unity, CV has no effect)
//   AMT = +1, CV=0 → G = 0.0  (muted)
//   AMT = +1, CV=5 → G = 1.0  (accent: unity at 5 V)
//   AMT = -1, CV=0 → G = 1.0  (full through when envelope low)
//   AMT = -1, CV=5 → G = 0.0  (duck: fully attenuated at 5 V)
struct VcaBlock {
	static float process(float v, float amtParam, float cvV) {
		float normCV = clamp(cvV / 5.f, 0.f, 1.f);  // 5 V = full scale
		// Positive AMT: mod = (1 - normCV), so CV=0→G=0, CV≥5→G=1 (accent)
		// Negative AMT: mod = normCV,        so CV=0→G=1, CV≥5→G=0 (duck)
		float mod = (amtParam >= 0.f) ? (1.f - normCV) : normCV;
		float g   = clamp(1.f - std::abs(amtParam) * mod, 0.f, 1.f);
		return v * g;
	}
};
