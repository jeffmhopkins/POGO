#pragma once
#include <rack.hpp>

// Block VCA: pre-LP1 voltage-controlled amplifier.
// THAT 2180 dB-law hardware: G = 10^(2*(control-1)), giving -40 dB at control=0, 0 dB at control=1.
//
// amtParam [-1, +1]: bipolar attenuverter; center detent (0) = unity gain always.
// cvV      [0,10]  : CV input (normally mod bus or envelope).
//                    5 V = unity at full CW; above 5 V saturates at G=1.
//
// Gain law (control in [0,1]):
//   AMT = 0        → control = 1.0 always (unity, CV has no effect)
//   AMT = +1, CV=0 → control = 0.0 (muted, -40 dB)
//   AMT = +1, CV=5 → control = 1.0 (unity, accent)
//   AMT = -1, CV=0 → control = 1.0 (unity, duck idle)
//   AMT = -1, CV=5 → control = 0.0 (muted, duck full)
struct VcaBlock {
	static float process(float v, float amtParam, float cvV) {
		float normCV = clamp(cvV / 5.f, 0.f, 1.f);
		float control;
		if (amtParam >= 0.f)
			control = 1.f - amtParam * (1.f - normCV);  // 1 − AMT×(1−CV)
		else
			control = 1.f + amtParam * normCV;           // 1 − |AMT|×CV
		control = clamp(control, 0.f, 1.f);
		// dB-law: G = 10^(2*(control-1)) → 0 dB at control=1, -40 dB at control=0
		float G = (control <= 0.001f) ? 0.f : std::pow(10.f, 2.f * (control - 1.f));
		return v * G;
	}
};
