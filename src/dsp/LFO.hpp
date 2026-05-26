#pragma once
#include <rack.hpp>

// Dual-use triangle-wave LFO replacing Block 2 (envelope follower).
// LFO1 normalizes into the mod bus when MOD_IN is unpatched.
// LFO2 is standalone (output jack only).
//
// speedParam [0,1]: exponential 0.05 Hz to 20 Hz.
//   0.05 * pow(400, param) → 0.05 Hz at 0, ~1 Hz at 50%, ~20 Hz at 100%.
// Returns [-1, +1]; caller maps to ±5 V output.
struct LFO {
	float phase = 0.f;  // [0, 1)

	float process(float speedParam, float sampleTime) {
		float speedHz = 0.05f * std::pow(400.f, speedParam);
		phase += speedHz * sampleTime;
		if (phase >= 1.f) phase -= 1.f;
		// Triangle: -1 at phase=0, +1 at phase=0.5, -1 at phase=1
		return (phase < 0.5f) ? (4.f * phase - 1.f) : (3.f - 4.f * phase);
	}

	void reset() { phase = 0.f; }
};
