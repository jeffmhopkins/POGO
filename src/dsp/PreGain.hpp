#pragma once
#include <rack.hpp>

// Block 1: Pre-gain boost switch.
// GAIN=0: unity pass-through.
// GAIN=1: 5× gain, hard-clipped at NE5532 output swing (~±10.5 V on ±12 V rails).
// Spec Phase 2: V_out = clamp(5 × V_in, −10.5, +10.5) — intentionally aggressive.
struct PreGain {
	static float process(float v, float gainParam) {
		if (gainParam < 0.5f)
			return v;
		return clamp(5.f * v, -10.5f, 10.5f);
	}
};
