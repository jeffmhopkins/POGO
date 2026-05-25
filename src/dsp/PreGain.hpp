#pragma once
#include <rack.hpp>

// Block 1: Pre-gain boost switch.
// GAIN=0: unity pass-through.
// GAIN=1: 5× gain with op-amp output swing soft limit (~±10.5 V on ±12 V rails).
struct PreGain {
	static float process(float v, float gainParam) {
		if (gainParam < 0.5f)
			return v;
		// 5× boost; NE5532 output swing ≈ ±10.5 V — soft saturation via tanh
		constexpr float G   = 5.f;
		constexpr float LIM = 10.5f;
		float boosted = G * v;
		// tanh-based soft clip scaled so the -3 dB point is at LIM
		return LIM * std::tanh(boosted / LIM);
	}
};
