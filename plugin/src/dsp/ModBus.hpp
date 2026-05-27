#pragma once
#include <rack.hpp>

// Modulation bus processor and per-destination attenuverter helper.
//
// ModBusProcessor: scales and offsets a mod source to produce the shared bus signal.
//   amount [0,1]: maps to 0.2×–5× (exponential taper)
//   offset [-1,1]: maps to ±5 V DC offset
//
// applyDestination: applies override-jack + attenuverter to a destination CV.
//   busV        : mod bus voltage
//   overrideV   : override jack voltage
//   hasOverride : true when a cable is connected to the override jack
//   attenuverter: [-1, +1] pot value
struct ModBusProcessor {
	// Amount pot taper: 0 → 0.2×, 0.5 → 1×, 1 → 5×
	static float amountGain(float p) {
		// Exponential: gain = 0.2 × 25^p  (0.2 at p=0, 5 at p=1)
		return 0.2f * std::pow(25.f, p);
	}

	static float process(float sourceV, float amountParam, float offsetParam) {
		float gain   = amountGain(amountParam);
		float offset = offsetParam * 5.f; // [-1,+1] → ±5 V
		return clamp(sourceV * gain + offset, -10.f, 10.f);
	}
};

static inline float applyDestination(float busV, float overrideV,
                                     bool hasOverride, float att) {
	float source = hasOverride ? overrideV : busV;
	return source * att;
}
