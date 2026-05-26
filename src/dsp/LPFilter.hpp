#pragma once
#include <rack.hpp>

// Blocks 5 & 6: 2-pole state-variable low-pass filter.
// Uses Andrew Simper's trapezoidal-integrated SVF for numerical stability.
//
// cutoffV  [V/oct, bipolar]: 1 V/oct CV. f_ref = 632 Hz at 0 V (LP1 and LP2).
//          Effective range: ±5 V → ~20 Hz (−5 V) to ~20 kHz (+5 V).
// resParam [0,1]: resonance → Q from 0.5 to ~50 (near self-oscillation).
// spreadV  [V]: per-channel frequency offset for stereo widening (R channel only).
struct LPFilter {
	float ic1 = 0.f, ic2 = 0.f;
	float fref = 632.f; // Reference freq at 0 V (both LP1 and LP2)

	// Compute filter g and k coefficients from CV and resonance.
	// g = tan(pi * f0 / fs),  k = 1/Q
	static void computeCoeffs(float cutoffV, float resParam, float sampleRate,
	                           float fref_, float& g, float& k) {
		float f0 = fref_ * std::pow(2.f, cutoffV);
		f0 = clamp(f0, 10.f, sampleRate * 0.48f);
		g  = std::tan(M_PI * f0 / sampleRate);
		// Resonance: Q ∈ [0.5, 50]; high resonance → low k = 1/Q
		float Q = 0.5f + resParam * 49.5f;
		k = 1.f / Q;
	}

	// Returns LP output. HP and BP also available but not exposed here.
	float process(float x, float cutoffV, float resParam, float sampleRate) {
		float g, k;
		computeCoeffs(cutoffV, resParam, sampleRate, fref, g, k);
		float a1 = 1.f / (1.f + g * (g + k));
		float a2 = g * a1;
		float a3 = g * a2;

		float v3 = x - ic2;
		float v1 = a1 * ic1 + a2 * v3;
		float v2 = ic2 + a2 * ic1 + a3 * v3;
		ic1 = 2.f * v1 - ic1;
		ic2 = 2.f * v2 - ic2;
		return v2; // LP output
	}

	void reset() { ic1 = ic2 = 0.f; }
};
