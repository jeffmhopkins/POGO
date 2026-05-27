#pragma once
#include <rack.hpp>

// Block 2: Envelope follower — precision full-wave rectifier → asymmetric peak
// detector → ×2 output scaling to produce 0–10 V from ±5 V audio.
//
// attack  [0,1]: maps logarithmically to 0.1 ms – 200 ms
// release [0,1]: maps logarithmically to 5 ms – 2 s
struct EnvelopeFollower {
	float env = 0.f;

	// Logarithmic parameter mapping: p∈[0,1] → τ∈[min, max] ms
	static float tauFromParam(float p, float minMs, float maxMs) {
		return 0.001f * std::exp(p * std::log(maxMs / minMs) + std::log(minMs));
	}

	float process(float v, float attackParam, float releaseParam, float sampleTime) {
		float rect      = std::abs(v);
		float tauAttack = tauFromParam(attackParam,  0.1f,    200.f);
		float tauRel    = tauFromParam(releaseParam, 5.f,   2000.f);
		float tau       = (rect > env) ? tauAttack : tauRel;
		// Exponential smoothing toward rectified input
		float coeff = 1.f - std::exp(-sampleTime / tau);
		env += (rect - env) * coeff;
		// Scale: ±5 V audio → 0–10 V CV
		return clamp(2.f * env, 0.f, 10.f);
	}

	void reset() { env = 0.f; }
};
