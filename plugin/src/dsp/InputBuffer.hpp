#pragma once
#include <rack.hpp>

// Block A: unity-gain input buffers with ±12 V rail clamp.
// Hardware: LM4562 voltage follower + BAT54 clamp; DSP is a simple clamp.
// LM4562 output swing ≈ ±11 V typical on ±12 V rails (spec Phase 3).
struct InputBuffer {
	static float process(float v) {
		return clamp(v, -11.0f, 11.0f);
	}
};
