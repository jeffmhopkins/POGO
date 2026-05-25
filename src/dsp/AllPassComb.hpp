#pragma once
#include <rack.hpp>

// Block 3: Triple 6-stage all-pass comb filter (APCF).
//
// Each group consists of 6 cascaded 1st-order APF stages and a feedback path.
// Three independent groups (L+R stereo, each processed separately):
//   Group 1: 20 Hz – 2 kHz    (f_ref = 200 Hz  at 0 V)
//   Group 2: 200 Hz – 8 kHz   (f_ref = 1500 Hz at 0 V)
//   Group 3: 1 kHz – 20 kHz   (f_ref = 6000 Hz at 0 V)

// ── First-order all-pass section ─────────────────────────────────────────────
// H(z) = (a + z^-1) / (1 + a*z^-1)
// a = (1 - tan(pi*f0/fs)) / (1 + tan(pi*f0/fs))
// Difference equation: y[n] = a*x[n] + x[n-1] - a*y[n-1]
struct APFStage {
	float xz = 0.f; // x[n-1]
	float yz = 0.f; // y[n-1]

	float process(float x, float a) {
		float y = a * x + xz - a * yz;
		xz = x;
		yz = y;
		return y;
	}

	static float coeff(float f0, float sampleRate) {
		float t = std::tan(M_PI * f0 / sampleRate);
		return (1.f - t) / (1.f + t);
	}

	void reset() { xz = yz = 0.f; }
};

// ── Six-stage APF chain with feedback ────────────────────────────────────────
// freqV    [V/oct, bipolar]: 1 V/oct CV controls f0. f_ref at 0 V.
// fbGain   [0, 0.95]: feedback depth
// polarity [+1, 0, -1]: feedback polarity (positive=notches, negative=peaks)
// prevDistV: post-distortion tap for FB DIST BLEND crossfade
// blendParam [0,1]: 0 = clean APF feedback, 1 = post-distortion feedback
struct APFGroup {
	APFStage stages[6];
	float prevOut = 0.f;

	static constexpr float FB_MAX = 0.94f; // hard limit to prevent runaway

	float process(float x, float a,
	              float fbGain, float polarity,
	              float prevDistV, float blendParam) {
		float fbSig = prevOut * polarity;
		float fbMixed = fbSig * (1.f - blendParam) + (prevDistV * polarity) * blendParam;
		float xIn = x + clamp(fbGain, 0.f, FB_MAX) * clamp(fbMixed, -20.f, 20.f);
		xIn = clamp(xIn, -20.f, 20.f); // prevent NaN on instability

		float y = xIn;
		for (auto& s : stages)
			y = s.process(y, a);
		prevOut = y;
		return y;
	}

	void reset() {
		for (auto& s : stages) s.reset();
		prevOut = 0.f;
	}
};

// ── Full triple APF chain (one channel) ──────────────────────────────────────
// combBypass [0,1]: wet level (0=dry, 1=full comb output)
// widthV     [V]: frequency offset applied to distinguish L vs R (stereo width)
struct TripleAPF {
	APFGroup groups[3];

	// Process one sample.
	// freqV[3], fbGain[3], polarity[3], distV[3], blend[3]: per-group params
	// combBypass: wet/dry crossfade
	// widthOffset: added to all freq CVs for stereo spread (0 for L, widthParam for R)
	float process(float x,
	              const float freqV[3], const float fbGain[3],
	              const float polarity[3], const float distV[3],
	              const float blend[3],
	              float combBypass, float widthOffset,
	              float sampleRate) {
		// f_ref per group at 0 V/oct (spec Phase 1 defaults: 200 Hz / 1.5 kHz / 6 kHz)
		// local static avoids C++11 ODR issue with constexpr array members
		static const float F_REF[3] = {200.f, 1500.f, 6000.f};
		float wetSum = 0.f;
		for (int i = 0; i < 3; i++) {
			float f0 = F_REF[i] * std::pow(2.f, freqV[i] + widthOffset);
			f0 = clamp(f0, 10.f, sampleRate * 0.48f);
			float a = APFStage::coeff(f0, sampleRate);
			wetSum += groups[i].process(x, a, fbGain[i], polarity[i], distV[i], blend[i]);
		}
		// Average three groups and crossfade with dry
		float wet = wetSum / 3.f;
		return x * (1.f - combBypass) + wet * combBypass;
	}

	void reset() {
		for (auto& g : groups) g.reset();
	}
};
