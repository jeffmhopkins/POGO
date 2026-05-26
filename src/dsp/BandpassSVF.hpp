#pragma once
#include <rack.hpp>

// Block 3: Triple 4-pole OTA-C SVF bandpass resonators (formant F1/F2/F3).
// Same Andrew Simper trapezoidal SVF as LPFilter/HPFilter; BP output = v1.
//
// freqV    [V/oct, bipolar]: 1V/oct CV. f_ref[3] = {200, 1500, 6000} Hz at 0 V.
// qParam   [0,1]: Q from 0.5 (flat) to 50 (near self-oscillation).
// polarity: +1 = normal, 0 = silence, -1 = phase-inverted output before summing.
//
// TESTING: 4-pole (two cascaded 2-pole SVF stages). Spec says 2-pole; see STATUS.md.
// TESTING: FB_DIST_BLEND path removed — SVF input is clean audio only; see STATUS.md.
struct SVFGroup {
	float ic1a = 0.f, ic2a = 0.f;  // stage 1
	float ic1b = 0.f, ic2b = 0.f;  // stage 2

	float process(float x, float f0, float Q, float sampleRate) {
		float g = std::tan(M_PI * f0 / sampleRate);
		float k = 1.f / Q;
		float a1 = 1.f / (1.f + g * (g + k));
		float a2 = g * a1;
		float a3 = g * a2;
		// Stage 1
		float v3 = x - ic2a;
		float v1 = a1 * ic1a + a2 * v3;
		float v2 = ic2a + a2 * ic1a + a3 * v3;
		ic1a = 2.f * v1 - ic1a;
		ic2a = 2.f * v2 - ic2a;
		// Stage 2 — same coefficients, independent state
		v3 = v1 - ic2b;
		v1 = a1 * ic1b + a2 * v3;
		v2 = ic2b + a2 * ic1b + a3 * v3;
		ic1b = 2.f * v1 - ic1b;
		ic2b = 2.f * v2 - ic2b;
		return v1;  // 4-pole BP output
	}

	void reset() { ic1a = ic2a = ic1b = ic2b = 0.f; }
};

struct TripleBandpass {
	SVFGroup groups[3];
	float prevOut[3] = {};

	// qParam [0,1]: maps to Q in [0.5, 50].
	// widthOffset: per-channel freq shift in V/oct (0 for L, WIDTH value for R).
	float process(float x, float freqV[3], float qParam[3], int polarity,
	              float widthOffset, float sampleRate) {
		constexpr float F_REF[3] = {200.f, 1500.f, 6000.f};
		float sum = 0.f;
		float pol = (polarity == 1) ? 1.f : (polarity == -1) ? -1.f : 0.f;
		for (int i = 0; i < 3; i++) {
			float f0 = F_REF[i] * std::pow(2.f, freqV[i] + widthOffset);
			f0 = clamp(f0, 10.f, sampleRate * 0.48f);
			float Q  = 0.5f + qParam[i] * 49.5f;
			float y  = groups[i].process(x, f0, Q, sampleRate);
			y *= 1.f / (Q * Q);  // normalize 4-pole BP peak to unity; Q shapes bandwidth only
			prevOut[i] = y;
			sum += pol * y;
		}
		return sum;
	}

	void reset() {
		for (auto& g : groups) g.reset();
		for (int i = 0; i < 3; i++) prevOut[i] = 0.f;
	}
};
