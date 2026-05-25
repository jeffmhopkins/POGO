#pragma once
#include <rack.hpp>

// Block VCA: pre-LP1 voltage-controlled amplifier.
// THAT 2180 in hardware; modeled as a linear VCA.
//
// amtParam [-1, +1]: bipolar attenuverter (center detent = 0, i.e. no CV).
// cvV      [0,10]  : CV input (normally the mod bus or envelope).
//
// G = clamp(amtParam × cvV / 10, 0, 1)  — unipolar VCA
// Negative AMT inverts CV polarity (ducking).
struct VcaBlock {
	static float process(float v, float amtParam, float cvV) {
		float g = amtParam * (cvV / 10.f);
		// Bipolar amt: positive = accent, negative = duck.
		// For audio path, allow full inversion at negative g.
		return v * clamp(g, -1.f, 1.f);
	}
};
