#pragma once
#include <rack.hpp>

// Block 7: 2-pole state-variable high-pass filter.
// Same Simper SVF topology as LPFilter; HP output tapped instead.
//
// cutoffV  [V/oct, bipolar]: 1 V/oct CV. f_ref = 632 Hz at 0 V.
//          Effective range: ±5 V → ~20 Hz (−5 V) to ~20 kHz (+5 V).
// resParam [0,1]: Q exponential 0.5–2000. Top ~5% is self-oscillation territory.
struct HPFilter {
	float ic1 = 0.f, ic2 = 0.f;
	float prevBP = 0.f;  // BP tap (v1) from last process() — used for BAND OUT

	static constexpr float F_REF = 632.f;

	static void computeCoeffs(float cutoffV, float resParam, float sampleRate,
	                           float& g, float& k) {
		float f0 = F_REF * std::pow(2.f, cutoffV);
		f0 = clamp(f0, 10.f, sampleRate * 0.48f);
		g  = std::tan(M_PI * f0 / sampleRate);
		float Q = 0.5f * std::pow(4000.f, resParam);
		k = 1.f / Q;
	}

	float process(float x, float cutoffV, float resParam, float sampleRate) {
		float g, k;
		computeCoeffs(cutoffV, resParam, sampleRate, g, k);
		float a1 = 1.f / (1.f + g * (g + k));
		float a2 = g * a1;
		float a3 = g * a2;

		float v3 = x - ic2;
		float v1 = a1 * ic1 + a2 * v3;
		float v2 = ic2 + a2 * ic1 + a3 * v3;
		ic1 = 2.f * v1 - ic1;
		ic2 = 2.f * v2 - ic2;
		prevBP = v1;
		// HP output: x - k*v1 - v2 (standard Simper SVF); negate compensates for
		// SVF summing amp inversion in hardware.
		return -(x - k * v1 - v2);
	}

	void reset() { ic1 = ic2 = prevBP = 0.f; }
};
