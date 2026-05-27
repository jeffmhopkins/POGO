#pragma once
#include <rack.hpp>

// Block 4: Distortion — three independent chains, one per APF group.
// Each chain implements the dual-zone drive mapping:
//   driveParam ∈ [0,1]
//   p ≤ 0.20: gain = p / 0.20  (mute → unity at 9am)
//   p > 0.20: d = (p − 0.20) / 0.80  (0–1 drive zone)
//
// MODE: 0 = soft clip (tanh), 1 = hard clip, 2 = wavefold
struct Distortion {
	static float softClip(float x, float d) {
		// drive=0 at d=0 (linear/clean) rising exponentially to ~54 at d=1.
		// Spec: "DRIVE at 9am = unity gain, all modes: signal passes clean at 1:1."
		float drive = std::exp(d * 4.f) - 1.f; // 0–54×
		if (drive < 1e-6f) return x;
		float denom = std::tanh(drive);
		return (denom > 1e-6f) ? std::tanh(drive * x) / denom : x;
	}

	static float hardClip(float x, float d) {
		float g = 1.f + d * 4.f; // 1–5× linear gain
		// ±1.16 matches hardware: BZX84C5V1 zener (5.1V) + 1N4148W Vf (0.7V) = ±5.8V → 5.8/5.0
		return clamp(g * x, -1.16f, 1.16f);
	}

	// Buchla-style wavefold: passive diode clamp at ±Vth, then V_out = 2×V_clamp − V_in
	// Vth = 0.28 (= 1.4V/5V; two 1N4148W per polarity in hardware passive clamp)
	static float wavefold(float x, float d) {
		constexpr float Vth = 0.28f;
		float y = (1.f + d * 4.f) * x;
		y = clamp(y, -20.f, 20.f); // ~35 folds headroom; hardware limited by op-amp rails
		return Vth * std::asin(std::sin(float(M_PI) * 0.5f / Vth * y)) * float(2.0 / M_PI);
	}

	// v should be normalised to ±1 before calling; returns ±1 normalised
	static float processNorm(float v, float driveParam, int mode) {
		if (driveParam <= 0.20f) {
			return v * (driveParam / 0.20f);
		}
		float d = (driveParam - 0.20f) / 0.80f;
		switch (mode) {
			case 0: default: return softClip(v, d);
			case 1:          return hardClip(v, d);
			case 2:          return wavefold(v, d);
		}
	}

	// Full-voltage process: input/output in Eurorack ±5 V scale
	// Returns scaled output; three chains are summed externally with 0.5× per chain.
	static float process(float v, float driveParam, int mode) {
		constexpr float SCALE = 5.f;
		float norm   = clamp(v / SCALE, -1.f, 1.f);
		float result = processNorm(norm, driveParam, mode);
		return result * SCALE;
	}
};
