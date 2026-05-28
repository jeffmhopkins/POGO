#pragma once
#include <rack.hpp>

// Block 3: Triple 2-pole OTA-C SVF bandpass resonators (formant F1/F2/F3).
//
// freqV    [V/oct, bipolar]: 1V/oct CV. f_ref[3] = {200, 1500, 6000} Hz at 0 V.
// qParam   [0,1]: exponential Q taper — Q = 0.5 × 400^qParam → [0.5, 200].
//          Peak gain = 1 (constant unity, hardware OTA-C SVF behavior).
//          Does NOT self-oscillate by design.
struct SVFGroup {
	float ic1 = 0.f, ic2 = 0.f;

	float process(float x, float f0, float Q, float sampleRate) {
		float g  = std::tan(float(M_PI) * f0 / sampleRate);
		float k  = 1.f / Q;
		float a1 = 1.f / (1.f + g * (g + k));
		float a2 = g * a1;
		float a3 = g * a2;
		float v3 = x - ic2;
		float v1 = a1 * ic1 + a2 * v3;
		float v2 = ic2 + a2 * ic1 + a3 * v3;
		ic1 = 2.f * v1 - ic1;
		ic2 = 2.f * v2 - ic2;
		return v1;  // 2-pole BP tap; peak gain = 1 at resonance
	}

	void reset() { ic1 = ic2 = 0.f; }
};

struct TripleBandpass {
	SVFGroup groups[3];
	float prevOut[3] = {};

	// x:      main input for BP1 + BP2
	// bp3x:   input for BP3 (ALT path when patched; else same as x)
	// tiltV:  per-group stereo tilt [V/oct] — caller passes (globalTilt + groupTilt) for L,
	//         or -(globalTilt + groupTilt) for R so each group can have independent spread
	float process(float x, float bp3x, float freqV[3], float qParam[3],
	              float tiltV[3], float sampleRate) {
		constexpr float F_REF[3] = {400.f, 400.f, 400.f};
		float sum = 0.f;
		for (int i = 0; i < 3; i++) {
			float f0 = F_REF[i] * std::pow(2.f, freqV[i] + tiltV[i]);
			f0 = clamp(f0, 10.f, sampleRate * 0.48f);
			float Q  = 0.5f * std::pow(400.f, qParam[i]);
			float y  = groups[i].process((i == 2) ? bp3x : x, f0, Q, sampleRate);
			prevOut[i] = y;
			sum += y;
		}
		return sum;
	}

	void reset() {
		for (auto& g : groups) g.reset();
		for (int i = 0; i < 3; i++) prevOut[i] = 0.f;
	}
};
