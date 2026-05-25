#pragma once
#include <rack.hpp>

// Block A: unity-gain input buffers with ±12 V rail clamp.
// Hardware: LM4562 voltage follower + BAT54 clamp; DSP is a simple clamp.
struct InputBuffer {
	static float process(float v) {
		return clamp(v, -11.5f, 11.5f);
	}
};
