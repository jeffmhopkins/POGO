#include "plugin.hpp"
#include "dsp/InputBuffer.hpp"
#include "dsp/PreGain.hpp"
#include "dsp/EnvelopeFollower.hpp"
#include "dsp/ModBus.hpp"
#include "dsp/AllPassComb.hpp"
#include "dsp/Distortion.hpp"
#include "dsp/VcaBlock.hpp"
#include "dsp/LPFilter.hpp"
#include "dsp/HPFilter.hpp"

// ── Horizontal 2-position slide switch ────────────────────────────────────
struct PogoSwitchH2 : app::Switch {
	PogoSwitchH2() { box.size = mm2px(Vec(9.f, 5.f)); }

	void draw(const DrawArgs& args) override {
		float w = box.size.x, h = box.size.y;
		float cy = h * 0.5f;
		float bodyH = mm2px(2.4f), slugW = mm2px(3.5f), slugH = mm2px(2.8f);

		nvgBeginPath(args.vg);
		nvgRoundedRect(args.vg, 0, cy - bodyH * 0.5f, w, bodyH, mm2px(1.2f));
		nvgFillColor(args.vg, nvgRGB(0x22, 0x22, 0x22));
		nvgFill(args.vg);
		nvgStrokeColor(args.vg, nvgRGB(0x55, 0x55, 0x55));
		nvgStrokeWidth(args.vg, 0.5f);
		nvgStroke(args.vg);

		auto* pq = getParamQuantity();
		float t = pq ? (pq->getValue() - pq->getMinValue()) / (pq->getMaxValue() - pq->getMinValue()) : 0.f;
		float slugX = t * (w - slugW);
		nvgBeginPath(args.vg);
		nvgRoundedRect(args.vg, slugX, cy - slugH * 0.5f, slugW, slugH, mm2px(0.8f));
		nvgFillColor(args.vg, nvgRGB(0x66, 0x66, 0x66));
		nvgFill(args.vg);
		nvgStrokeColor(args.vg, nvgRGB(0x88, 0x88, 0x88));
		nvgStrokeWidth(args.vg, 0.3f);
		nvgStroke(args.vg);
	}
};

// ── Horizontal 3-position slide switch ────────────────────────────────────
struct PogoSwitchH3 : app::Switch {
	PogoSwitchH3() { box.size = mm2px(Vec(12.f, 5.f)); }

	void draw(const DrawArgs& args) override {
		float w = box.size.x, h = box.size.y;
		float cy = h * 0.5f;
		float bodyH = mm2px(2.4f), slugW = mm2px(3.5f), slugH = mm2px(2.8f);

		nvgBeginPath(args.vg);
		nvgRoundedRect(args.vg, 0, cy - bodyH * 0.5f, w, bodyH, mm2px(1.2f));
		nvgFillColor(args.vg, nvgRGB(0x22, 0x22, 0x22));
		nvgFill(args.vg);
		nvgStrokeColor(args.vg, nvgRGB(0x55, 0x55, 0x55));
		nvgStrokeWidth(args.vg, 0.5f);
		nvgStroke(args.vg);

		auto* pq = getParamQuantity();
		float t = pq ? (pq->getValue() - pq->getMinValue()) / (pq->getMaxValue() - pq->getMinValue()) : 0.5f;
		float slugX = t * (w - slugW);
		nvgBeginPath(args.vg);
		nvgRoundedRect(args.vg, slugX, cy - slugH * 0.5f, slugW, slugH, mm2px(0.8f));
		nvgFillColor(args.vg, nvgRGB(0x66, 0x66, 0x66));
		nvgFill(args.vg);
		nvgStrokeColor(args.vg, nvgRGB(0x88, 0x88, 0x88));
		nvgStrokeWidth(args.vg, 0.3f);
		nvgStroke(args.vg);
	}
};

// ── Vertical slider (45 mm travel, matching LP2 / HP SVG tracks) ──────────
struct PogoSlider : app::SliderKnob {
	PogoSlider() { box.size = mm2px(Vec(13.f, 45.f)); }

	void draw(const DrawArgs& args) override {
		float w = box.size.x, h = box.size.y;
		float trackW = mm2px(4.f);
		float trackX  = (w - trackW) * 0.5f;
		float handleW = w, handleH = mm2px(7.f);
		float travelH = h - handleH;

		auto* pq = getParamQuantity();
		float t = pq ? (pq->getValue() - pq->getMinValue()) / (pq->getMaxValue() - pq->getMinValue()) : 0.5f;
		float handleY = (1.f - t) * travelH; // top = max value

		// Track
		nvgBeginPath(args.vg);
		nvgRoundedRect(args.vg, trackX, 0, trackW, h, mm2px(1.5f));
		nvgFillColor(args.vg, nvgRGB(0x11, 0x11, 0x11));
		nvgFill(args.vg);
		nvgStrokeColor(args.vg, nvgRGB(0x44, 0x44, 0x44));
		nvgStrokeWidth(args.vg, 0.5f);
		nvgStroke(args.vg);

		// Handle
		nvgBeginPath(args.vg);
		nvgRoundedRect(args.vg, 0, handleY, handleW, handleH, mm2px(1.8f));
		nvgFillColor(args.vg, nvgRGB(0x55, 0x55, 0x55));
		nvgFill(args.vg);
		nvgStrokeColor(args.vg, nvgRGB(0x77, 0x77, 0x77));
		nvgStrokeWidth(args.vg, 0.4f);
		nvgStroke(args.vg);
	}
};

// ─────────────────────────────────────────────────────────────────────────
struct Pogo : Module {
	enum ParamId {
		// Zone 0a — INPUT / GAIN
		GAIN_PARAM,
		// Zone 0b — ENVELOPE
		MOD_SRC_PARAM,
		ATTACK_PARAM,
		RELEASE_PARAM,
		// Zone 0c — MOD BUS
		MOD_AMOUNT_PARAM,
		MOD_OFFSET_PARAM,
		// Zone 1 — CONTROL / COMB
		COMB_BYPASS_PARAM,
		WIDTH_PARAM,
		POLARITY_PARAM,
		MASTER_OFFSET_PARAM,
		// Zone 1 — CONTROL / DIST
		DIST_MODE_PARAM,
		FB_DIST_BLEND_PARAM,
		// Zone 1 — unified bottom row attenuverters (19 mod destinations start here)
		BYPASS_ATT_PARAM,           // APF Comb Bypass
		MASTER_OFFSET_ATT_PARAM,    // APF Master Offset
		BLEND_ATT_PARAM,            // APF FB Dist Blend
		// Zone 2a — Comb 1
		FREQ_1_PARAM,
		FB_1_PARAM,
		DRIVE_1_PARAM,
		FREQ_ATT_1_PARAM,
		FB_ATT_1_PARAM,
		DRIVE_ATT_1_PARAM,
		// Zone 2b — Comb 2
		FREQ_2_PARAM,
		FB_2_PARAM,
		DRIVE_2_PARAM,
		FREQ_ATT_2_PARAM,
		FB_ATT_2_PARAM,
		DRIVE_ATT_2_PARAM,
		// Zone 2c — Comb 3
		FREQ_3_PARAM,
		FB_3_PARAM,
		DRIVE_3_PARAM,
		FREQ_ATT_3_PARAM,
		FB_ATT_3_PARAM,
		DRIVE_ATT_3_PARAM,
		// Zone 3 — VCA
		VCA_AMT_PARAM,
		// Zone 3 — LP1
		LP1_CUTOFF_PARAM,
		LP1_SPREAD_PARAM,
		LP1_RESONANCE_PARAM,
		LP1_CUT_ATT_PARAM,
		LP1_RES_ATT_PARAM,
		// Zone 4 — LP2
		LP2_CUTOFF_PARAM,
		LP2_RESONANCE_PARAM,
		LP2_CUT_ATT_PARAM,
		LP2_RES_ATT_PARAM,
		// Zone 5 — HP
		HP_CUTOFF_PARAM,
		HP_RESONANCE_PARAM,
		HP_CUT_ATT_PARAM,
		HP_RES_ATT_PARAM,
		NUM_PARAMS
	};

	enum InputId {
		// Audio
		L_IN_INPUT,
		R_IN_INPUT,
		// Mod source
		MOD_IN_INPUT,
		// Zone 1 CV override jacks
		BYPASS_CV_INPUT,
		MASTER_OFFSET_CV_INPUT,
		BLEND_CV_INPUT,
		// Comb 1 CV override jacks
		FREQ_CV_1_INPUT,
		FB_CV_1_INPUT,
		DRIVE_CV_1_INPUT,
		// Comb 2 CV override jacks
		FREQ_CV_2_INPUT,
		FB_CV_2_INPUT,
		DRIVE_CV_2_INPUT,
		// Comb 3 CV override jacks
		FREQ_CV_3_INPUT,
		FB_CV_3_INPUT,
		DRIVE_CV_3_INPUT,
		// VCA CV
		VCA_CV_INPUT,
		// LP1 CV override jacks
		LP1_CUT_CV_INPUT,
		LP1_RES_CV_INPUT,
		// LP2 CV override jacks
		LP2_CUT_CV_INPUT,
		LP2_RES_CV_INPUT,
		// HP CV override jacks
		HP_CUT_CV_INPUT,
		HP_RES_CV_INPUT,
		NUM_INPUTS
	};

	enum OutputId {
		ENV_L_OUTPUT,
		ENV_R_OUTPUT,
		BAND_L_OUTPUT,   // LP1 aux L (BAND OUT)
		BAND_R_OUTPUT,   // LP1 aux R (BAND OUT)
		L_OUTPUT,
		R_OUTPUT,
		NUM_OUTPUTS
	};

	enum LightId {
		NUM_LIGHTS
	};

	Pogo() {
		config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS, NUM_LIGHTS);

		// Zone 0a
		configSwitch(GAIN_PARAM, 0.f, 1.f, 0.f, "Gain", {"1\xc3\x97", "5\xc3\x97"});

		// Zone 0b
		configSwitch(MOD_SRC_PARAM, 0.f, 2.f, 1.f, "Mod Source Select", {"L", "Max(L,R)", "Avg(L,R)"});
		configParam(ATTACK_PARAM, 0.f, 1.f, 0.3f, "Attack");
		configParam(RELEASE_PARAM, 0.f, 1.f, 0.5f, "Release");

		// Zone 0c
		configParam(MOD_AMOUNT_PARAM, 0.f, 1.f, 0.5f, "Mod Amount");
		configParam(MOD_OFFSET_PARAM, -1.f, 1.f, 0.f, "Mod Offset");

		// Zone 1 COMB
		configParam(COMB_BYPASS_PARAM, 0.f, 1.f, 1.f, "Comb Bypass");
		configParam(WIDTH_PARAM, 0.f, 1.f, 0.f, "Stereo Width");
		configSwitch(POLARITY_PARAM, 0.f, 2.f, 1.f, "APF Feedback Polarity", {"Positive", "Off", "Negative"});
		configParam(MASTER_OFFSET_PARAM, -5.f, 5.f, 0.f, "Master Offset", " V");

		// Zone 1 DIST
		configSwitch(DIST_MODE_PARAM, 0.f, 2.f, 0.f, "Distortion Mode", {"Soft Clip", "Hard Clip", "Wavefold"});
		configParam(FB_DIST_BLEND_PARAM, 0.f, 1.f, 0.f, "FB Dist Blend");

		// Zone 1 bottom row attenuverters
		configParam(BYPASS_ATT_PARAM, -1.f, 1.f, 0.f, "Comb Bypass CV Depth");
		configParam(MASTER_OFFSET_ATT_PARAM, -1.f, 1.f, 0.f, "Master Offset CV Depth");
		configParam(BLEND_ATT_PARAM, -1.f, 1.f, 0.f, "FB Dist Blend CV Depth");

		// Comb 1
		configParam(FREQ_1_PARAM, -5.f, 5.f, 0.f, "Comb 1 Freq", " V/oct");
		configParam(FB_1_PARAM, 0.f, 1.f, 0.f, "Comb 1 Feedback");
		configParam(DRIVE_1_PARAM, 0.f, 1.f, 0.20f, "Comb 1 Drive");
		configParam(FREQ_ATT_1_PARAM, -1.f, 1.f, 0.f, "Comb 1 Freq CV Depth");
		configParam(FB_ATT_1_PARAM, -1.f, 1.f, 0.f, "Comb 1 FB CV Depth");
		configParam(DRIVE_ATT_1_PARAM, -1.f, 1.f, 0.f, "Comb 1 Drive CV Depth");

		// Comb 2
		configParam(FREQ_2_PARAM, -5.f, 5.f, 0.f, "Comb 2 Freq", " V/oct");
		configParam(FB_2_PARAM, 0.f, 1.f, 0.f, "Comb 2 Feedback");
		configParam(DRIVE_2_PARAM, 0.f, 1.f, 0.20f, "Comb 2 Drive");
		configParam(FREQ_ATT_2_PARAM, -1.f, 1.f, 0.f, "Comb 2 Freq CV Depth");
		configParam(FB_ATT_2_PARAM, -1.f, 1.f, 0.f, "Comb 2 FB CV Depth");
		configParam(DRIVE_ATT_2_PARAM, -1.f, 1.f, 0.f, "Comb 2 Drive CV Depth");

		// Comb 3
		configParam(FREQ_3_PARAM, -5.f, 5.f, 0.f, "Comb 3 Freq", " V/oct");
		configParam(FB_3_PARAM, 0.f, 1.f, 0.f, "Comb 3 Feedback");
		configParam(DRIVE_3_PARAM, 0.f, 1.f, 0.20f, "Comb 3 Drive");
		configParam(FREQ_ATT_3_PARAM, -1.f, 1.f, 0.f, "Comb 3 Freq CV Depth");
		configParam(FB_ATT_3_PARAM, -1.f, 1.f, 0.f, "Comb 3 FB CV Depth");
		configParam(DRIVE_ATT_3_PARAM, -1.f, 1.f, 0.f, "Comb 3 Drive CV Depth");

		// VCA
		configParam(VCA_AMT_PARAM, -1.f, 1.f, 0.f, "VCA CV Depth");

		// LP1
		configParam(LP1_CUTOFF_PARAM, -4.f, 4.f, 0.f, "LP1 Cutoff", " V/oct");
		configParam(LP1_SPREAD_PARAM, -1.f, 1.f, 0.f, "LP1 Stereo Spread Offset", " V/oct");
		configParam(LP1_RESONANCE_PARAM, 0.f, 1.f, 0.f, "LP1 Resonance");
		configParam(LP1_CUT_ATT_PARAM, -1.f, 1.f, 0.f, "LP1 Cutoff CV Depth");
		configParam(LP1_RES_ATT_PARAM, -1.f, 1.f, 0.f, "LP1 Resonance CV Depth");

		// LP2
		configParam(LP2_CUTOFF_PARAM, -4.f, 4.f, 0.f, "LP2 Cutoff", " V/oct");
		configParam(LP2_RESONANCE_PARAM, 0.f, 1.f, 0.f, "LP2 Resonance");
		configParam(LP2_CUT_ATT_PARAM, -1.f, 1.f, 0.f, "LP2 Cutoff CV Depth");
		configParam(LP2_RES_ATT_PARAM, -1.f, 1.f, 0.f, "LP2 Resonance CV Depth");

		// HP
		configParam(HP_CUTOFF_PARAM, -4.f, 4.f, 0.f, "HP Cutoff", " V/oct");
		configParam(HP_RESONANCE_PARAM, 0.f, 1.f, 0.f, "HP Resonance");
		configParam(HP_CUT_ATT_PARAM, -1.f, 1.f, 0.f, "HP Cutoff CV Depth");
		configParam(HP_RES_ATT_PARAM, -1.f, 1.f, 0.f, "HP Resonance CV Depth");

		// Inputs
		configInput(L_IN_INPUT, "Audio L");
		configInput(R_IN_INPUT, "Audio R");
		configInput(MOD_IN_INPUT, "Mod Source");
		configInput(BYPASS_CV_INPUT, "Comb Bypass CV");
		configInput(MASTER_OFFSET_CV_INPUT, "Master Offset CV");
		configInput(BLEND_CV_INPUT, "FB Dist Blend CV");
		configInput(FREQ_CV_1_INPUT, "Comb 1 Freq CV");
		configInput(FB_CV_1_INPUT, "Comb 1 Feedback CV");
		configInput(DRIVE_CV_1_INPUT, "Comb 1 Drive CV");
		configInput(FREQ_CV_2_INPUT, "Comb 2 Freq CV");
		configInput(FB_CV_2_INPUT, "Comb 2 Feedback CV");
		configInput(DRIVE_CV_2_INPUT, "Comb 2 Drive CV");
		configInput(FREQ_CV_3_INPUT, "Comb 3 Freq CV");
		configInput(FB_CV_3_INPUT, "Comb 3 Feedback CV");
		configInput(DRIVE_CV_3_INPUT, "Comb 3 Drive CV");
		configInput(VCA_CV_INPUT, "VCA CV");
		configInput(LP1_CUT_CV_INPUT, "LP1 Cutoff CV");
		configInput(LP1_RES_CV_INPUT, "LP1 Resonance CV");
		configInput(LP2_CUT_CV_INPUT, "LP2 Cutoff CV");
		configInput(LP2_RES_CV_INPUT, "LP2 Resonance CV");
		configInput(HP_CUT_CV_INPUT, "HP Cutoff CV");
		configInput(HP_RES_CV_INPUT, "HP Resonance CV");

		// Outputs
		configOutput(ENV_L_OUTPUT, "Envelope CV L");
		configOutput(ENV_R_OUTPUT, "Envelope CV R");
		configOutput(BAND_L_OUTPUT, "LP1 Aux L");
		configOutput(BAND_R_OUTPUT, "LP1 Aux R");
		configOutput(L_OUTPUT, "Audio L");
		configOutput(R_OUTPUT, "Audio R");
	}

	// ── DSP state ────────────────────────────────────────────────────────────
	EnvelopeFollower envL, envR;
	TripleAPF        combL, combR;
	// Distortion taps from previous sample (needed for APF feedback blend)
	float distTapL[3] = {}, distTapR[3] = {};
	LPFilter lp1L, lp1R;
	LPFilter lp2L, lp2R;
	HPFilter hpL, hpR;

	void onReset() override {
		envL.reset(); envR.reset();
		combL.reset(); combR.reset();
		for (int i = 0; i < 3; i++) distTapL[i] = distTapR[i] = 0.f;
		lp1L.reset(); lp1R.reset();
		lp2L.reset(); lp2R.reset();
		hpL.reset();  hpR.reset();
	}

	void process(const ProcessArgs& args) override {
		const float fs = args.sampleRate;
		const float dt = args.sampleTime;

		// ── Block A: input buffers ────────────────────────────────────────────
		float inL = InputBuffer::process(inputs[L_IN_INPUT].getVoltage());
		float inR = InputBuffer::process(inputs[R_IN_INPUT].isConnected()
		                                 ? inputs[R_IN_INPUT].getVoltage()
		                                 : inL); // normalise R to L if unpatched

		// ── Block 1: pre-gain boost ───────────────────────────────────────────
		float gainParam = params[GAIN_PARAM].getValue();
		float pgL = PreGain::process(inL, gainParam);
		float pgR = PreGain::process(inR, gainParam);

		// ── Block 2: envelope follower ────────────────────────────────────────
		float modSrc = params[MOD_SRC_PARAM].getValue(); // 0=L, 1=max, 2=avg
		float envSrcL = pgL;
		float envSrcR = pgR;
		float envSrcMono;
		if (modSrc < 0.5f)       envSrcMono = envSrcL;
		else if (modSrc < 1.5f)  envSrcMono = std::max(std::abs(envSrcL), std::abs(envSrcR));
		else                      envSrcMono = (envSrcL + envSrcR) * 0.5f;

		float atkP = params[ATTACK_PARAM].getValue();
		float relP = params[RELEASE_PARAM].getValue();
		float envOutL = envL.process(envSrcMono, atkP, relP, dt);
		float envOutR = envR.process(envSrcMono, atkP, relP, dt);

		// ── Mod bus ───────────────────────────────────────────────────────────
		float modSrcV;
		if (inputs[MOD_IN_INPUT].isConnected())
			modSrcV = inputs[MOD_IN_INPUT].getVoltage();
		else
			modSrcV = envOutL; // normalise to envelope follower

		float busV = ModBusProcessor::process(modSrcV,
		                                      params[MOD_AMOUNT_PARAM].getValue(),
		                                      params[MOD_OFFSET_PARAM].getValue());

		// Helper: resolve one mod destination
		auto modDest = [&](int cvInput, int attParam) -> float {
			bool has = inputs[cvInput].isConnected();
			return applyDestination(busV,
			                        inputs[cvInput].getVoltage(),
			                        has,
			                        params[attParam].getValue());
		};

		// ── Block 3: triple APF comb filter ──────────────────────────────────
		// Per-group parameters
		float freqV[3] = {
			params[FREQ_1_PARAM].getValue() + modDest(FREQ_CV_1_INPUT, FREQ_ATT_1_PARAM),
			params[FREQ_2_PARAM].getValue() + modDest(FREQ_CV_2_INPUT, FREQ_ATT_2_PARAM),
			params[FREQ_3_PARAM].getValue() + modDest(FREQ_CV_3_INPUT, FREQ_ATT_3_PARAM),
		};
		// MASTER OFFSET adds to all three simultaneously
		float masterOff = params[MASTER_OFFSET_PARAM].getValue()
		                  + modDest(MASTER_OFFSET_CV_INPUT, MASTER_OFFSET_ATT_PARAM);
		for (int i = 0; i < 3; i++) freqV[i] += masterOff;

		float fbGain[3] = {
			clamp(params[FB_1_PARAM].getValue() + modDest(FB_CV_1_INPUT, FB_ATT_1_PARAM), 0.f, 1.f),
			clamp(params[FB_2_PARAM].getValue() + modDest(FB_CV_2_INPUT, FB_ATT_2_PARAM), 0.f, 1.f),
			clamp(params[FB_3_PARAM].getValue() + modDest(FB_CV_3_INPUT, FB_ATT_3_PARAM), 0.f, 1.f),
		};

		int polSwitch = (int)std::round(params[POLARITY_PARAM].getValue()); // 0=pos, 1=off, 2=neg
		float polarity[3];
		float polVal = (polSwitch == 0) ? 1.f : (polSwitch == 2) ? -1.f : 0.f;
		for (int i = 0; i < 3; i++) polarity[i] = polVal;

		float blendParam = clamp(params[FB_DIST_BLEND_PARAM].getValue()
		                         + modDest(BLEND_CV_INPUT, BLEND_ATT_PARAM), 0.f, 1.f);
		float blendArr[3] = {blendParam, blendParam, blendParam};

		float combBypass = clamp(params[COMB_BYPASS_PARAM].getValue()
		                         + modDest(BYPASS_CV_INPUT, BYPASS_ATT_PARAM), 0.f, 1.f);
		float widthParam = params[WIDTH_PARAM].getValue(); // ±1 V/oct offset on R

		float combOutL = combL.process(pgL, freqV, fbGain, polarity,
		                               distTapL, blendArr, combBypass, 0.f, fs);
		float combOutR = combR.process(pgR, freqV, fbGain, polarity,
		                               distTapR, blendArr, combBypass, widthParam, fs);

		// ── Block 4: distortion ───────────────────────────────────────────────
		int distMode = (int)std::round(params[DIST_MODE_PARAM].getValue());
		float driveCV[3] = {
			clamp(params[DRIVE_1_PARAM].getValue() + modDest(DRIVE_CV_1_INPUT, DRIVE_ATT_1_PARAM), 0.f, 1.f),
			clamp(params[DRIVE_2_PARAM].getValue() + modDest(DRIVE_CV_2_INPUT, DRIVE_ATT_2_PARAM), 0.f, 1.f),
			clamp(params[DRIVE_3_PARAM].getValue() + modDest(DRIVE_CV_3_INPUT, DRIVE_ATT_3_PARAM), 0.f, 1.f),
		};

		// Process each group independently, then sum with 0.5× per chain
		float distSumL = 0.f, distSumR = 0.f;
		for (int i = 0; i < 3; i++) {
			// Use the APF group outputs as per-group inputs to distortion
			float apcfL = combL.groups[i].prevOut;
			float apcfR = combR.groups[i].prevOut;
			distTapL[i] = Distortion::process(apcfL, driveCV[i], distMode);
			distTapR[i] = Distortion::process(apcfR, driveCV[i], distMode);
			distSumL += distTapL[i] * 0.5f;
			distSumR += distTapR[i] * 0.5f;
		}
		// Clamp summed output
		distSumL = clamp(distSumL, -10.5f, 10.5f);
		distSumR = clamp(distSumR, -10.5f, 10.5f);

		// ── Block VCA ─────────────────────────────────────────────────────────
		float vcaCV  = inputs[VCA_CV_INPUT].isConnected()
		               ? inputs[VCA_CV_INPUT].getVoltage()
		               : busV; // normalise to mod bus
		float vcaAmt = params[VCA_AMT_PARAM].getValue();
		float vcaL   = VcaBlock::process(distSumL, vcaAmt, vcaCV);
		float vcaR   = VcaBlock::process(distSumR, vcaAmt, vcaCV);

		// ── Block 5: LP Filter 1 ─────────────────────────────────────────────
		float lp1CV  = params[LP1_CUTOFF_PARAM].getValue()
		               + modDest(LP1_CUT_CV_INPUT, LP1_CUT_ATT_PARAM);
		float lp1Res = clamp(params[LP1_RESONANCE_PARAM].getValue()
		                     + modDest(LP1_RES_CV_INPUT, LP1_RES_ATT_PARAM) / 10.f,
		                     0.f, 1.f);
		float spreadV = params[LP1_SPREAD_PARAM].getValue();
		float bandL = lp1L.process(vcaL, lp1CV,          lp1Res, fs);
		float bandR = lp1R.process(vcaR, lp1CV + spreadV, lp1Res, fs);

		// ── Block 6: LP Filter 2 ─────────────────────────────────────────────
		float lp2CV  = params[LP2_CUTOFF_PARAM].getValue()
		               + modDest(LP2_CUT_CV_INPUT, LP2_CUT_ATT_PARAM);
		float lp2Res = clamp(params[LP2_RESONANCE_PARAM].getValue()
		                     + modDest(LP2_RES_CV_INPUT, LP2_RES_ATT_PARAM) / 10.f,
		                     0.f, 1.f);
		float lp2L_ = lp2L.process(bandL, lp2CV, lp2Res, fs);
		float lp2R_ = lp2R.process(bandR, lp2CV, lp2Res, fs);

		// ── Block 7: HP Filter ────────────────────────────────────────────────
		float hpCV  = params[HP_CUTOFF_PARAM].getValue()
		              + modDest(HP_CUT_CV_INPUT, HP_CUT_ATT_PARAM);
		float hpRes = clamp(params[HP_RESONANCE_PARAM].getValue()
		                    + modDest(HP_RES_CV_INPUT, HP_RES_ATT_PARAM) / 10.f,
		                    0.f, 1.f);
		float outL = hpL.process(lp2L_, hpCV, hpRes, fs);
		float outR = hpR.process(lp2R_, hpCV, hpRes, fs);

		// ── Block B: output buffers ───────────────────────────────────────────
		outputs[L_OUTPUT].setVoltage(clamp(outL, -11.5f, 11.5f));
		outputs[R_OUTPUT].setVoltage(clamp(outR, -11.5f, 11.5f));
		outputs[BAND_L_OUTPUT].setVoltage(clamp(bandL, -11.5f, 11.5f));
		outputs[BAND_R_OUTPUT].setVoltage(clamp(bandR, -11.5f, 11.5f));
		outputs[ENV_L_OUTPUT].setVoltage(envOutL);
		outputs[ENV_R_OUTPUT].setVoltage(envOutR);
	}
};

// ─────────────────────────────────────────────────────────────────────────
struct PogoWidget : ModuleWidget {
	// Helper: add a centered text label. cx/baseY in mm (SVG coordinates).
	// baseY is the SVG text baseline; we offset up by ~0.75x font size so the
	// cap-height is centred on that row.
	void addLabel(float cx_mm, float baseY_mm, const char* text,
	              NVGcolor col, float sizeMm) {
		const float W  = mm2px(50.f);
		const float H  = mm2px(sizeMm * 1.5f);
		auto* lbl = createWidget<ui::Label>(
			mm2px(Vec(cx_mm - 25.f, baseY_mm - sizeMm * 0.75f))
		);
		lbl->box.size        = Vec(W, H);
		lbl->text            = text;
		lbl->color           = col;
		lbl->fontSize        = mm2px(sizeMm);
		lbl->alignment       = NVG_ALIGN_CENTER;
		addChild(lbl);
	}

	PogoWidget(Pogo* module) {
		setModule(module);
		setPanel(createPanel(asset::plugin(pluginInstance, "res/Pogo.svg")));

		// Colour palette matching the SVG
		const NVGcolor CYAN    = nvgRGB(0x00, 0xd4, 0xff);
		const NVGcolor GRAY_99 = nvgRGB(0x99, 0x99, 0x99);
		const NVGcolor GRAY_88 = nvgRGB(0x88, 0x88, 0x88);
		const NVGcolor GRAY_77 = nvgRGB(0x77, 0x77, 0x77);
		const NVGcolor SUBDUE  = nvgRGB(0x4a, 0x60, 0x70);
		const NVGcolor DIMBLUE = nvgRGB(0x3d, 0x52, 0x60);

		// ── Title bars ─────────────────────────────────────────────────────
		addLabel(101.60f,   3.5f, "POGO  \xc2\xb7  STEREO TRIPLE COMB FILTER", CYAN,    3.5f);
		addLabel(101.60f, 132.0f, "SPACE COAST SYNTHESIZERS  \xc2\xb7  SCS",   SUBDUE,  2.4f);

		// ── Zone headers ───────────────────────────────────────────────────
		addLabel( 10.16f,  9.0f, "INPUT / GAIN", CYAN, 2.4f);
		addLabel( 10.16f, 43.5f, "ENVELOPE",     CYAN, 2.4f);
		addLabel( 10.16f, 94.0f, "MOD BUS",      CYAN, 2.4f);
		addLabel( 35.56f,  9.0f, "CONTROL",      CYAN, 2.4f);
		addLabel( 66.04f,  9.0f, "COMB 1",       CYAN, 2.4f);
		addLabel( 96.52f,  9.0f, "COMB 2",       CYAN, 2.4f);
		addLabel(127.00f,  9.0f, "COMB 3",       CYAN, 2.4f);
		addLabel(152.40f,  9.0f, "VCA",          CYAN, 2.4f);
		addLabel(152.40f, 33.0f, "LP 1",         CYAN, 2.4f);
		addLabel(172.72f,  9.0f, "BAND OUT",     CYAN, 2.4f);
		addLabel(193.04f,  9.0f, "OUT",          CYAN, 2.4f);
		addLabel(172.72f, 33.0f, "LP 2",         CYAN, 2.4f);
		addLabel(193.04f, 33.0f, "HP",           CYAN, 2.4f);

		// Comb frequency-range subtitles
		addLabel( 66.04f, 13.5f, "20Hz-2kHz",   SUBDUE, 1.6f);
		addLabel( 96.52f, 13.5f, "200Hz-8kHz",  SUBDUE, 1.6f);
		addLabel(127.00f, 13.5f, "1kHz-20kHz",  SUBDUE, 1.6f);

		// ── Zone 0a: INPUT / GAIN ──────────────────────────────────────────
		addLabel(  5.08f, 23.5f, "L IN",    GRAY_88, 1.8f);
		addLabel( 15.24f, 23.5f, "R IN",    GRAY_88, 1.8f);
		addLabel( 10.16f, 37.0f, "GAIN",    GRAY_99, 1.8f);
		// Switch position labels
		addLabel(  7.91f, 33.0f, "1\xc3\x97", DIMBLUE, 1.6f);
		addLabel( 12.41f, 33.0f, "5\xc3\x97", DIMBLUE, 1.6f);

		// ── Zone 0b: ENVELOPE ─────────────────────────────────────────────
		addLabel( 10.16f, 48.0f, "MOD SRC", DIMBLUE, 1.6f);
		// Switch position labels
		addLabel(  6.16f, 54.5f, "L",   DIMBLUE, 1.6f);
		addLabel( 10.16f, 54.5f, "MAX", DIMBLUE, 1.6f);
		addLabel( 14.16f, 54.5f, "AVG", DIMBLUE, 1.6f);
		addLabel(  5.08f, 69.5f, "ATTACK",  GRAY_99, 1.8f);
		addLabel( 15.24f, 69.5f, "RELEASE", GRAY_99, 1.8f);
		addLabel(  5.08f, 87.0f, "ENV L",   GRAY_88, 1.8f);
		addLabel( 15.24f, 87.0f, "ENV R",   GRAY_88, 1.8f);

		// ── Zone 0c: MOD BUS ──────────────────────────────────────────────
		addLabel(  5.08f, 108.5f, "AMOUNT", GRAY_99, 1.8f);
		addLabel( 15.24f, 108.5f, "OFFSET", GRAY_99, 1.8f);
		addLabel( 10.16f, 124.5f, "MOD IN", GRAY_88, 1.8f);

		// ── Zone 1: CONTROL — COMB section ────────────────────────────────
		addLabel( 29.00f,  28.5f, "COMB",         GRAY_99, 1.8f);
		addLabel( 29.00f,  30.8f, "BYPASS",       GRAY_99, 1.8f);
		addLabel( 42.14f,  28.5f, "WIDTH",        GRAY_99, 1.8f);
		// POLARITY switch position labels
		addLabel( 31.56f,  40.5f, "POS", DIMBLUE, 1.6f);
		addLabel( 35.56f,  40.5f, "OFF", DIMBLUE, 1.6f);
		addLabel( 39.56f,  40.5f, "NEG", DIMBLUE, 1.6f);
		addLabel( 35.56f,  44.0f, "POLARITY",     GRAY_99, 1.8f);
		addLabel( 35.56f,  69.0f, "MASTER OFFSET",GRAY_99, 1.8f);

		// ── Zone 1: CONTROL — DIST section ────────────────────────────────
		// MODE switch: vertical (CKSSThree), position labels to its right
		addLabel( 29.40f,  83.5f, "SFT", DIMBLUE, 1.4f);
		addLabel( 29.40f,  87.5f, "HRD", DIMBLUE, 1.4f);
		addLabel( 29.40f,  91.5f, "WFD", DIMBLUE, 1.4f);
		addLabel( 28.00f,  96.5f, "MODE",         GRAY_99, 1.8f);
		addLabel( 40.00f,  94.5f, "FB DIST",      GRAY_99, 1.8f);
		addLabel( 40.00f,  96.8f, "BLEND",        GRAY_99, 1.8f);

		// ── Zone 1: unified bottom row CV jacks ───────────────────────────
		addLabel( 25.40f, 124.5f, "BYPASS", GRAY_77, 1.8f);
		addLabel( 35.56f, 124.5f, "OFFSET", GRAY_77, 1.8f);
		addLabel( 45.72f, 124.5f, "BLEND",  GRAY_77, 1.8f);

		// ── Zone 2a: COMB 1 ───────────────────────────────────────────────
		addLabel( 66.04f,  44.0f, "FREQ",  GRAY_99, 1.8f);
		addLabel( 66.04f,  71.0f, "FB",    GRAY_99, 1.8f);
		addLabel( 66.04f,  97.0f, "DRIVE", GRAY_99, 1.8f);
		addLabel( 55.88f, 124.5f, "FREQ",  GRAY_77, 1.8f);
		addLabel( 66.04f, 124.5f, "FB",    GRAY_77, 1.8f);
		addLabel( 76.20f, 124.5f, "DRIVE", GRAY_77, 1.8f);

		// ── Zone 2b: COMB 2 ───────────────────────────────────────────────
		addLabel( 96.52f,  44.0f, "FREQ",  GRAY_99, 1.8f);
		addLabel( 96.52f,  71.0f, "FB",    GRAY_99, 1.8f);
		addLabel( 96.52f,  97.0f, "DRIVE", GRAY_99, 1.8f);
		addLabel( 86.36f, 124.5f, "FREQ",  GRAY_77, 1.8f);
		addLabel( 96.52f, 124.5f, "FB",    GRAY_77, 1.8f);
		addLabel(106.68f, 124.5f, "DRIVE", GRAY_77, 1.8f);

		// ── Zone 2c: COMB 3 ───────────────────────────────────────────────
		addLabel(127.00f,  44.0f, "FREQ",  GRAY_99, 1.8f);
		addLabel(127.00f,  71.0f, "FB",    GRAY_99, 1.8f);
		addLabel(127.00f,  97.0f, "DRIVE", GRAY_99, 1.8f);
		addLabel(116.84f, 124.5f, "FREQ",  GRAY_77, 1.8f);
		addLabel(127.00f, 124.5f, "FB",    GRAY_77, 1.8f);
		addLabel(137.16f, 124.5f, "DRIVE", GRAY_77, 1.8f);

		// ── Zone 3: VCA + LP1 ─────────────────────────────────────────────
		addLabel(147.32f,  24.5f, "AMT",   GRAY_99, 1.8f);
		addLabel(157.48f,  24.5f, "CV IN", GRAY_77, 1.8f);
		addLabel(152.40f,  57.0f, "CUTOFF",       GRAY_99, 1.8f);
		addLabel(152.40f,  77.5f, "STEREO SPREAD", GRAY_99, 1.8f);
		addLabel(152.40f,  79.8f, "OFFSET",        GRAY_99, 1.8f);
		addLabel(152.40f, 101.0f, "RESONANCE",     GRAY_99, 1.8f);
		addLabel(147.32f, 124.5f, "CUT", GRAY_77, 1.8f);
		addLabel(157.48f, 124.5f, "RES", GRAY_77, 1.8f);

		// ── Zone 4: BAND OUT + LP2 ────────────────────────────────────────
		addLabel(167.64f,  24.5f, "LP1 L", GRAY_88, 1.8f);
		addLabel(177.80f,  24.5f, "LP1 R", GRAY_88, 1.8f);
		addLabel(172.72f,  38.0f, "CUTOFF",   GRAY_99, 1.8f);
		addLabel(172.72f, 101.0f, "RESONANCE",GRAY_99, 1.8f);
		addLabel(167.64f, 124.5f, "CUT", GRAY_77, 1.8f);
		addLabel(177.80f, 124.5f, "RES", GRAY_77, 1.8f);

		// ── Zone 5: OUT + HP ──────────────────────────────────────────────
		addLabel(187.96f,  24.5f, "LEFT",  GRAY_88, 1.8f);
		addLabel(198.12f,  24.5f, "RIGHT", GRAY_88, 1.8f);
		addLabel(193.04f,  38.0f, "CUTOFF",   GRAY_99, 1.8f);
		addLabel(193.04f, 101.0f, "RESONANCE",GRAY_99, 1.8f);
		addLabel(187.96f, 124.5f, "CUT", GRAY_77, 1.8f);
		addLabel(198.12f, 124.5f, "RES", GRAY_77, 1.8f);

		// ── Zone 0a — INPUT / GAIN ──────────────────────────────────────
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(5.08f, 16.f)), module, Pogo::L_IN_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(15.24f, 16.f)), module, Pogo::R_IN_INPUT));
		// GAIN: 2-pos horizontal switch
		addParam(createParamCentered<PogoSwitchH2>(mm2px(Vec(10.16f, 28.2f)), module, Pogo::GAIN_PARAM));

		// ── Zone 0b — ENVELOPE ─────────────────────────────────────────────
		// MOD SRC: 3-pos horizontal switch
		addParam(createParamCentered<PogoSwitchH3>(mm2px(Vec(10.16f, 51.f)), module, Pogo::MOD_SRC_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(5.08f, 64.f)), module, Pogo::ATTACK_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(15.24f, 64.f)), module, Pogo::RELEASE_PARAM));
		addOutput(createOutputCentered<PJ301MPort>(mm2px(Vec(5.08f, 80.f)), module, Pogo::ENV_L_OUTPUT));
		addOutput(createOutputCentered<PJ301MPort>(mm2px(Vec(15.24f, 80.f)), module, Pogo::ENV_R_OUTPUT));

		// ── Zone 0c — MOD BUS ──────────────────────────────────────────────
		addParam(createParamCentered<Trimpot>(mm2px(Vec(5.08f, 103.f)), module, Pogo::MOD_AMOUNT_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(15.24f, 103.f)), module, Pogo::MOD_OFFSET_PARAM));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(10.16f, 118.f)), module, Pogo::MOD_IN_INPUT));

		// ── Zone 1 — CONTROL / COMB ────────────────────────────────────────
		addParam(createParamCentered<RoundBlackKnob>(mm2px(Vec(29.0f, 21.f)), module, Pogo::COMB_BYPASS_PARAM));
		addParam(createParamCentered<RoundBlackKnob>(mm2px(Vec(42.14f, 21.f)), module, Pogo::WIDTH_PARAM));
		// POLARITY: 3-pos horizontal switch
		addParam(createParamCentered<PogoSwitchH3>(mm2px(Vec(35.56f, 35.2f)), module, Pogo::POLARITY_PARAM));
		addParam(createParamCentered<RoundHugeBlackKnob>(mm2px(Vec(35.56f, 57.f)), module, Pogo::MASTER_OFFSET_PARAM));

		// ── Zone 1 — CONTROL / DIST ────────────────────────────────────────
		// MODE: 3-pos vertical switch (correct orientation)
		addParam(createParamCentered<CKSSThree>(mm2px(Vec(28.f, 87.f)), module, Pogo::DIST_MODE_PARAM));
		addParam(createParamCentered<RoundBlackKnob>(mm2px(Vec(40.f, 87.f)), module, Pogo::FB_DIST_BLEND_PARAM));

		// ── Zone 1 — unified bottom row ────────────────────────────────────
		addParam(createParamCentered<Trimpot>(mm2px(Vec(25.40f, 109.f)), module, Pogo::BYPASS_ATT_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(35.56f, 109.f)), module, Pogo::MASTER_OFFSET_ATT_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(45.72f, 109.f)), module, Pogo::BLEND_ATT_PARAM));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(25.40f, 118.f)), module, Pogo::BYPASS_CV_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(35.56f, 118.f)), module, Pogo::MASTER_OFFSET_CV_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(45.72f, 118.f)), module, Pogo::BLEND_CV_INPUT));

		// ── Zone 2a — COMB 1 ───────────────────────────────────────────────
		addParam(createParamCentered<RoundHugeBlackKnob>(mm2px(Vec(66.04f, 32.f)), module, Pogo::FREQ_1_PARAM));
		addParam(createParamCentered<RoundLargeBlackKnob>(mm2px(Vec(66.04f, 61.f)), module, Pogo::FB_1_PARAM));
		addParam(createParamCentered<RoundLargeBlackKnob>(mm2px(Vec(66.04f, 87.f)), module, Pogo::DRIVE_1_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(55.88f, 109.f)), module, Pogo::FREQ_ATT_1_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(66.04f, 109.f)), module, Pogo::FB_ATT_1_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(76.20f, 109.f)), module, Pogo::DRIVE_ATT_1_PARAM));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(55.88f, 118.f)), module, Pogo::FREQ_CV_1_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(66.04f, 118.f)), module, Pogo::FB_CV_1_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(76.20f, 118.f)), module, Pogo::DRIVE_CV_1_INPUT));

		// ── Zone 2b — COMB 2 ───────────────────────────────────────────────
		addParam(createParamCentered<RoundHugeBlackKnob>(mm2px(Vec(96.52f, 32.f)), module, Pogo::FREQ_2_PARAM));
		addParam(createParamCentered<RoundLargeBlackKnob>(mm2px(Vec(96.52f, 61.f)), module, Pogo::FB_2_PARAM));
		addParam(createParamCentered<RoundLargeBlackKnob>(mm2px(Vec(96.52f, 87.f)), module, Pogo::DRIVE_2_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(86.36f, 109.f)), module, Pogo::FREQ_ATT_2_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(96.52f, 109.f)), module, Pogo::FB_ATT_2_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(106.68f, 109.f)), module, Pogo::DRIVE_ATT_2_PARAM));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(86.36f, 118.f)), module, Pogo::FREQ_CV_2_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(96.52f, 118.f)), module, Pogo::FB_CV_2_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(106.68f, 118.f)), module, Pogo::DRIVE_CV_2_INPUT));

		// ── Zone 2c — COMB 3 ───────────────────────────────────────────────
		addParam(createParamCentered<RoundHugeBlackKnob>(mm2px(Vec(127.00f, 32.f)), module, Pogo::FREQ_3_PARAM));
		addParam(createParamCentered<RoundLargeBlackKnob>(mm2px(Vec(127.00f, 61.f)), module, Pogo::FB_3_PARAM));
		addParam(createParamCentered<RoundLargeBlackKnob>(mm2px(Vec(127.00f, 87.f)), module, Pogo::DRIVE_3_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(116.84f, 109.f)), module, Pogo::FREQ_ATT_3_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(127.00f, 109.f)), module, Pogo::FB_ATT_3_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(137.16f, 109.f)), module, Pogo::DRIVE_ATT_3_PARAM));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(116.84f, 118.f)), module, Pogo::FREQ_CV_3_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(127.00f, 118.f)), module, Pogo::FB_CV_3_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(137.16f, 118.f)), module, Pogo::DRIVE_CV_3_INPUT));

		// ── Zone 3 — VCA (top strip) ───────────────────────────────────────
		addParam(createParamCentered<Trimpot>(mm2px(Vec(147.32f, 16.f)), module, Pogo::VCA_AMT_PARAM));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(157.48f, 16.f)), module, Pogo::VCA_CV_INPUT));

		// ── Zone 3 — LP1 ───────────────────────────────────────────────────
		addParam(createParamCentered<RoundLargeBlackKnob>(mm2px(Vec(152.40f, 47.f)), module, Pogo::LP1_CUTOFF_PARAM));
		addParam(createParamCentered<RoundBlackKnob>(mm2px(Vec(152.40f, 70.f)), module, Pogo::LP1_SPREAD_PARAM));
		addParam(createParamCentered<RoundBlackKnob>(mm2px(Vec(152.40f, 93.f)), module, Pogo::LP1_RESONANCE_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(147.32f, 109.f)), module, Pogo::LP1_CUT_ATT_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(157.48f, 109.f)), module, Pogo::LP1_RES_ATT_PARAM));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(147.32f, 118.f)), module, Pogo::LP1_CUT_CV_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(157.48f, 118.f)), module, Pogo::LP1_RES_CV_INPUT));

		// ── Zone 4 — BAND OUT (top strip) ─────────────────────────────────
		addOutput(createOutputCentered<PJ301MPort>(mm2px(Vec(167.64f, 16.f)), module, Pogo::BAND_L_OUTPUT));
		addOutput(createOutputCentered<PJ301MPort>(mm2px(Vec(177.80f, 16.f)), module, Pogo::BAND_R_OUTPUT));

		// ── Zone 4 — LP2 ───────────────────────────────────────────────────
		// LP2 CUTOFF: vertical slider, 13mm x 45mm, center at track midpoint
		addParam(createParamCentered<PogoSlider>(mm2px(Vec(172.72f, 62.5f)), module, Pogo::LP2_CUTOFF_PARAM));
		addParam(createParamCentered<RoundBlackKnob>(mm2px(Vec(172.72f, 93.f)), module, Pogo::LP2_RESONANCE_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(167.64f, 109.f)), module, Pogo::LP2_CUT_ATT_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(177.80f, 109.f)), module, Pogo::LP2_RES_ATT_PARAM));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(167.64f, 118.f)), module, Pogo::LP2_CUT_CV_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(177.80f, 118.f)), module, Pogo::LP2_RES_CV_INPUT));

		// ── Zone 5 — OUT (top strip) ───────────────────────────────────────
		addOutput(createOutputCentered<PJ301MPort>(mm2px(Vec(187.96f, 16.f)), module, Pogo::L_OUTPUT));
		addOutput(createOutputCentered<PJ301MPort>(mm2px(Vec(198.12f, 16.f)), module, Pogo::R_OUTPUT));

		// ── Zone 5 — HP ────────────────────────────────────────────────────
		// HP CUTOFF: vertical slider, matching LP2 geometry
		addParam(createParamCentered<PogoSlider>(mm2px(Vec(193.04f, 62.5f)), module, Pogo::HP_CUTOFF_PARAM));
		addParam(createParamCentered<RoundBlackKnob>(mm2px(Vec(193.04f, 93.f)), module, Pogo::HP_RESONANCE_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(187.96f, 109.f)), module, Pogo::HP_CUT_ATT_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(198.12f, 109.f)), module, Pogo::HP_RES_ATT_PARAM));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(187.96f, 118.f)), module, Pogo::HP_CUT_CV_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(198.12f, 118.f)), module, Pogo::HP_RES_CV_INPUT));
	}
};

Model* modelPogo = createModel<Pogo, PogoWidget>("Pogo");
