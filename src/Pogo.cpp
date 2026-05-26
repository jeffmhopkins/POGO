#include "plugin.hpp"
#include "dsp/InputBuffer.hpp"
#include "dsp/PreGain.hpp"
#include "dsp/LFO.hpp"
#include "dsp/ModBus.hpp"
#include "dsp/BandpassSVF.hpp"
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
	PogoSlider() {
		box.size   = mm2px(Vec(13.f, 45.f));
		horizontal = false; // vertical fader: drag up = higher value
	}

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

struct FormantFreqQuantity : ParamQuantity {
	float fref = 200.f;
	std::string getDisplayValueString() override {
		float hz = fref * std::pow(2.f, getValue());
		if (hz >= 1000.f)
			return string::f("%.2f kHz", hz / 1000.f);
		return string::f("%.1f Hz", hz);
	}
	std::string getUnit() override { return ""; }
};

// ─────────────────────────────────────────────────────────────────────────
struct Pogo : Module {
	enum ParamId {
		// Zone 0a — INPUT / GAIN
		GAIN_PARAM,
		// Zone 0b — LFO
		LFO1_SPEED_PARAM,
		LFO2_SPEED_PARAM,
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
		ALT_BP_L_INPUT,   // Alt BP3 input L — when patched, replaces BP3 input
		ALT_BP_R_INPUT,   // Alt BP3 input R (normalizes to L alt if only L patched)
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
		LFO1_OUTPUT,
		LFO2_OUTPUT,
		BAND_L_OUTPUT,   // HP bandpass tap L (BAND OUT)
		BAND_R_OUTPUT,   // HP bandpass tap R (BAND OUT)
		L_OUTPUT,
		R_OUTPUT,
		NUM_OUTPUTS
	};

	enum LightId {
		LFO1_LIGHT,
		LFO2_LIGHT,
		MOD_LIGHT,
		NUM_LIGHTS
	};

	Pogo() {
		config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS, NUM_LIGHTS);

		// Zone 0a
		configSwitch(GAIN_PARAM, 0.f, 1.f, 0.f, "Gain", {"1\xc3\x97", "5\xc3\x97"});

		// Zone 0b
		configParam(LFO1_SPEED_PARAM, 0.f, 1.f, 0.3f, "LFO 1 Speed");
		configParam(LFO2_SPEED_PARAM, 0.f, 1.f, 0.3f, "LFO 2 Speed");

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

		// Formant 1
		configParam<FormantFreqQuantity>(FREQ_1_PARAM, -5.f, 5.f, 0.f, "Formant 1 Freq")->fref = 200.f;
		configParam(FB_1_PARAM, 0.f, 1.f, 0.f, "Formant 1 Q");
		configParam(DRIVE_1_PARAM, 0.f, 1.f, 0.20f, "Formant 1 Drive");
		configParam(FREQ_ATT_1_PARAM, -1.f, 1.f, 0.f, "Formant 1 Freq CV Depth");
		configParam(FB_ATT_1_PARAM, -1.f, 1.f, 0.f, "Formant 1 Q CV Depth");
		configParam(DRIVE_ATT_1_PARAM, -1.f, 1.f, 0.f, "Formant 1 Drive CV Depth");

		// Formant 2
		configParam<FormantFreqQuantity>(FREQ_2_PARAM, -5.f, 5.f, 0.f, "Formant 2 Freq")->fref = 1500.f;
		configParam(FB_2_PARAM, 0.f, 1.f, 0.f, "Formant 2 Q");
		configParam(DRIVE_2_PARAM, 0.f, 1.f, 0.20f, "Formant 2 Drive");
		configParam(FREQ_ATT_2_PARAM, -1.f, 1.f, 0.f, "Formant 2 Freq CV Depth");
		configParam(FB_ATT_2_PARAM, -1.f, 1.f, 0.f, "Formant 2 Q CV Depth");
		configParam(DRIVE_ATT_2_PARAM, -1.f, 1.f, 0.f, "Formant 2 Drive CV Depth");

		// Formant 3
		configParam<FormantFreqQuantity>(FREQ_3_PARAM, -5.f, 5.f, 0.f, "Formant 3 Freq")->fref = 6000.f;
		configParam(FB_3_PARAM, 0.f, 1.f, 0.f, "Formant 3 Q");
		configParam(DRIVE_3_PARAM, 0.f, 1.f, 0.20f, "Formant 3 Drive");
		configParam(FREQ_ATT_3_PARAM, -1.f, 1.f, 0.f, "Formant 3 Freq CV Depth");
		configParam(FB_ATT_3_PARAM, -1.f, 1.f, 0.f, "Formant 3 Q CV Depth");
		configParam(DRIVE_ATT_3_PARAM, -1.f, 1.f, 0.f, "Formant 3 Drive CV Depth");

		// VCA
		configParam(VCA_AMT_PARAM, -1.f, 1.f, 0.f, "VCA CV Depth");

		// LP1
		configParam(LP1_CUTOFF_PARAM, -5.f, 5.f, 0.f, "LP1 Cutoff", " V/oct");
		configParam(LP1_SPREAD_PARAM, -1.f, 1.f, 0.f, "LP1 Stereo Spread Offset", " V/oct");
		configParam(LP1_RESONANCE_PARAM, 0.f, 1.f, 0.f, "LP1 Resonance");
		configParam(LP1_CUT_ATT_PARAM, -1.f, 1.f, 0.f, "LP1 Cutoff CV Depth");
		configParam(LP1_RES_ATT_PARAM, -1.f, 1.f, 0.f, "LP1 Resonance CV Depth");

		// LP2
		configParam(LP2_CUTOFF_PARAM, -5.f, 5.f, 2.0f, "LP2 Cutoff", " V/oct");
		configParam(LP2_RESONANCE_PARAM, 0.f, 1.f, 0.f, "LP2 Resonance");
		configParam(LP2_CUT_ATT_PARAM, -1.f, 1.f, 0.f, "LP2 Cutoff CV Depth");
		configParam(LP2_RES_ATT_PARAM, -1.f, 1.f, 0.f, "LP2 Resonance CV Depth");

		// HP
		configParam(HP_CUTOFF_PARAM, -5.f, 5.f, -3.0f, "HP Cutoff", " V/oct");
		configParam(HP_RESONANCE_PARAM, 0.f, 1.f, 0.f, "HP Resonance");
		configParam(HP_CUT_ATT_PARAM, -1.f, 1.f, 0.f, "HP Cutoff CV Depth");
		configParam(HP_RES_ATT_PARAM, -1.f, 1.f, 0.f, "HP Resonance CV Depth");

		// Inputs
		configInput(L_IN_INPUT, "Audio L");
		configInput(R_IN_INPUT, "Audio R");
		configInput(ALT_BP_L_INPUT, "Alt BP3 L");
		configInput(ALT_BP_R_INPUT, "Alt BP3 R");
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
		configOutput(LFO1_OUTPUT, "LFO 1");
		configOutput(LFO2_OUTPUT, "LFO 2");
		configOutput(BAND_L_OUTPUT, "HP Bandpass L");
		configOutput(BAND_R_OUTPUT, "HP Bandpass R");

		// Lights
		configLight(LFO1_LIGHT, "LFO 1 value");
		configLight(LFO2_LIGHT, "LFO 2 value");
		configLight(MOD_LIGHT, "Mod bus signal");
		configOutput(L_OUTPUT, "Audio L");
		configOutput(R_OUTPUT, "Audio R");

		// LP1, LP2, and HP all use f_ref = 632 Hz at 0 V (struct defaults; no override needed)
	}

	// ── DSP state ────────────────────────────────────────────────────────────
	LFO lfo1, lfo2;
	TripleBandpass bandpassL, bandpassR;
	// Distortion taps — post-SVF output fed into Block 4; not routed back into SVF input.
	float distTapL[3] = {}, distTapR[3] = {};
	LPFilter lp1L, lp1R;
	LPFilter lp2L, lp2R;
	HPFilter hpL, hpR;

	// 2× oversampling for Blocks 3+4 (APF comb + distortion).
	// QUALITY=8 gives ~90 dB stopband attenuation, acceptable CPU on modern hw.
	static constexpr int OS = 2;
	static constexpr int OS_QUALITY = 8;
	dsp::Upsampler<OS, OS_QUALITY> upL, upR;
	dsp::Decimator<OS, OS_QUALITY> decL, decR;

	void onReset() override {
		lfo1.reset(); lfo2.reset();
		bandpassL.reset(); bandpassR.reset();
		for (int i = 0; i < 3; i++) distTapL[i] = distTapR[i] = 0.f;
		lp1L.reset(); lp1R.reset();
		lp2L.reset(); lp2R.reset();
		hpL.reset();  hpR.reset();
		upL.reset();  upR.reset();
		decL.reset(); decR.reset();
	}

	void onSampleRateChange() override {
		// Filter state holds frequency-dependent memory; reset on rate change
		// so transients don't appear at the new rate.
		onReset();
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

		// ── Block 2: LFOs ────────────────────────────────────────────────────
		float lfo1Raw = lfo1.process(params[LFO1_SPEED_PARAM].getValue(), dt);
		float lfo2Raw = lfo2.process(params[LFO2_SPEED_PARAM].getValue(), dt);
		float lfo1V   = lfo1Raw * 5.f;   // ±5V
		float lfo2V   = lfo2Raw * 5.f;   // ±5V

		// ── Mod bus ───────────────────────────────────────────────────────────
		// LFO1 normalizes to mod bus; MOD_IN jack overrides when patched
		float modSrcV = inputs[MOD_IN_INPUT].isConnected()
		                ? inputs[MOD_IN_INPUT].getVoltage()
		                : lfo1V;

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

		// ── Block 3: triple bandpass SVF (formant F1/F2/F3) ─────────────────
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

		float qParam[3] = {
			clamp(params[FB_1_PARAM].getValue() + modDest(FB_CV_1_INPUT, FB_ATT_1_PARAM), 0.f, 1.f),
			clamp(params[FB_2_PARAM].getValue() + modDest(FB_CV_2_INPUT, FB_ATT_2_PARAM), 0.f, 1.f),
			clamp(params[FB_3_PARAM].getValue() + modDest(FB_CV_3_INPUT, FB_ATT_3_PARAM), 0.f, 1.f),
		};

		int polSwitch = (int)std::round(params[POLARITY_PARAM].getValue()); // 0=pos, 1=off, 2=neg
		int polarityVal = (polSwitch == 0) ? 1 : (polSwitch == 2) ? -1 : 0;

		// ── Block VCA ─────────────────────────────────────────────────────────
		float vcaCV  = inputs[VCA_CV_INPUT].isConnected()
		               ? inputs[VCA_CV_INPUT].getVoltage()
		               : busV; // normalise to mod bus
		float vcaAmt = params[VCA_AMT_PARAM].getValue();
		float vcaL   = VcaBlock::process(pgL, vcaAmt, vcaCV);
		float vcaR   = VcaBlock::process(pgR, vcaAmt, vcaCV);

		// ── Block 5: LP Filter 1 ─────────────────────────────────────────────
		float lp1CV  = params[LP1_CUTOFF_PARAM].getValue()
		               + modDest(LP1_CUT_CV_INPUT, LP1_CUT_ATT_PARAM);
		float lp1Res = clamp(params[LP1_RESONANCE_PARAM].getValue()
		                     + modDest(LP1_RES_CV_INPUT, LP1_RES_ATT_PARAM) / 10.f,
		                     0.f, 1.f);
		float spreadV = params[LP1_SPREAD_PARAM].getValue();
		float bandL = lp1L.process(vcaL, lp1CV,          lp1Res, fs);
		float bandR = lp1R.process(vcaR, lp1CV + spreadV, lp1Res, fs);

		float combBypass = clamp(params[COMB_BYPASS_PARAM].getValue()
		                         + modDest(BYPASS_CV_INPUT, BYPASS_ATT_PARAM), 0.f, 1.f);
		float widthParam = params[WIDTH_PARAM].getValue(); // ±1 V/oct offset on R

		// ── Blocks 3+4: 2× oversampled SVF bandpass + distortion ───────────
		int distMode = (int)std::round(params[DIST_MODE_PARAM].getValue());
		float driveCV[3] = {
			clamp(params[DRIVE_1_PARAM].getValue() + modDest(DRIVE_CV_1_INPUT, DRIVE_ATT_1_PARAM), 0.f, 1.f),
			clamp(params[DRIVE_2_PARAM].getValue() + modDest(DRIVE_CV_2_INPUT, DRIVE_ATT_2_PARAM), 0.f, 1.f),
			clamp(params[DRIVE_3_PARAM].getValue() + modDest(DRIVE_CV_3_INPUT, DRIVE_ATT_3_PARAM), 0.f, 1.f),
		};

		// Alt BP3 inputs: when patched, bypass VCA+LP1 and feed directly into SVF.
		// R normalizes to L alt if only L is patched.
		bool altLConn = inputs[ALT_BP_L_INPUT].isConnected();
		bool altRConn = inputs[ALT_BP_R_INPUT].isConnected();
		float bpInL = altLConn ? inputs[ALT_BP_L_INPUT].getVoltage() : bandL;
		float bpInR = altRConn ? inputs[ALT_BP_R_INPUT].getVoltage()
		            : altLConn ? inputs[ALT_BP_L_INPUT].getVoltage()
		            : bandR;

		float upBufL[OS], upBufR[OS];
		upL.process(bpInL, upBufL);
		upR.process(bpInR, upBufR);

		float postL[OS], postR[OS];
		const float fs2 = 2.f * fs;
		for (int s = 0; s < OS; s++) {
			// SVF at 2× rate; clean audio in, no distortion feedback path
			bandpassL.process(upBufL[s], freqV, qParam, polarityVal, 0.f,        fs2);
			bandpassR.process(upBufR[s], freqV, qParam, polarityVal, widthParam, fs2);

			// Distortion per group; update distTap for next OS step's SVF blend
			float dSumL = 0.f, dSumR = 0.f;
			for (int i = 0; i < 3; i++) {
				distTapL[i] = Distortion::process(bandpassL.prevOut[i], driveCV[i], distMode);
				distTapR[i] = Distortion::process(bandpassR.prevOut[i], driveCV[i], distMode);
				dSumL += distTapL[i] * 0.5f;
				dSumR += distTapR[i] * 0.5f;
			}
			// COMB BYPASS crossfade at oversampled rate
			postL[s] = clamp(upBufL[s] * (1.f - combBypass) + dSumL * combBypass, -10.5f, 10.5f);
			postR[s] = clamp(upBufR[s] * (1.f - combBypass) + dSumR * combBypass, -10.5f, 10.5f);
		}

		// Decimate back to base rate
		float distSumL = decL.process(postL);
		float distSumR = decR.process(postR);

		// ── Block 7: HP Filter ────────────────────────────────────────────────
		float hpCV  = params[HP_CUTOFF_PARAM].getValue()
		              + modDest(HP_CUT_CV_INPUT, HP_CUT_ATT_PARAM);
		float hpRes = clamp(params[HP_RESONANCE_PARAM].getValue()
		                    + modDest(HP_RES_CV_INPUT, HP_RES_ATT_PARAM) / 10.f,
		                    0.f, 1.f);
		float hpOutL = hpL.process(distSumL, hpCV, hpRes, fs);
		float hpOutR = hpR.process(distSumR, hpCV, hpRes, fs);

		// ── Block 6: LP Filter 2 ─────────────────────────────────────────────
		float lp2CV  = params[LP2_CUTOFF_PARAM].getValue()
		               + modDest(LP2_CUT_CV_INPUT, LP2_CUT_ATT_PARAM);
		float lp2Res = clamp(params[LP2_RESONANCE_PARAM].getValue()
		                     + modDest(LP2_RES_CV_INPUT, LP2_RES_ATT_PARAM) / 10.f,
		                     0.f, 1.f);
		float outL = lp2L.process(hpOutL, lp2CV, lp2Res, fs);
		float outR = lp2R.process(hpOutR, lp2CV, lp2Res, fs);

		// ── Block B: output buffers (LM4562, ±11 V swing on ±12 V rails) ─────
		outputs[L_OUTPUT].setVoltage(clamp(outL, -11.0f, 11.0f));
		outputs[R_OUTPUT].setVoltage(clamp(outR, -11.0f, 11.0f));
		outputs[BAND_L_OUTPUT].setVoltage(clamp(hpL.prevBP, -11.0f, 11.0f));
		outputs[BAND_R_OUTPUT].setVoltage(clamp(hpR.prevBP, -11.0f, 11.0f));
		outputs[LFO1_OUTPUT].setVoltage(lfo1V);
		outputs[LFO2_OUTPUT].setVoltage(lfo2V);

		// LEDs: LFO [-1,+1] → [0,1]; MOD ±5V → [0,1]
		lights[LFO1_LIGHT].setBrightness((lfo1Raw + 1.f) * 0.5f);
		lights[LFO2_LIGHT].setBrightness((lfo2Raw + 1.f) * 0.5f);
		lights[MOD_LIGHT].setBrightness(clamp((modSrcV / 5.f + 1.f) * 0.5f, 0.f, 1.f));
	}
};

// ─────────────────────────────────────────────────────────────────────────
struct PogoWidget : ModuleWidget {
	PogoWidget(Pogo* module) {
		setModule(module);
		setPanel(createPanel(asset::plugin(pluginInstance, "res/Pogo.svg")));
		// All text labels are in res/Pogo.svg — no addLabel() calls needed.

		// ── Zone 0a — INPUT / GAIN ──────────────────────────────────────
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(5.08f, 16.f)), module, Pogo::L_IN_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(15.24f, 16.f)), module, Pogo::R_IN_INPUT));
		addParam(createParamCentered<PogoSwitchH2>(mm2px(Vec(10.16f, 32.f)), module, Pogo::GAIN_PARAM));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(5.08f, 43.f)), module, Pogo::ALT_BP_L_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(15.24f, 43.f)), module, Pogo::ALT_BP_R_INPUT));

		// ── Zone 0b — LFO ──────────────────────────────────────────────────
		addParam(createParamCentered<Trimpot>(mm2px(Vec(5.08f, 62.6f)), module, Pogo::LFO1_SPEED_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(15.24f, 62.6f)), module, Pogo::LFO2_SPEED_PARAM));
		addChild(createLightCentered<SmallLight<RedLight>>(mm2px(Vec(5.08f, 73.3f)), module, Pogo::LFO1_LIGHT));
		addChild(createLightCentered<SmallLight<RedLight>>(mm2px(Vec(15.24f, 73.3f)), module, Pogo::LFO2_LIGHT));
		addOutput(createOutputCentered<PJ301MPort>(mm2px(Vec(5.08f, 82.f)), module, Pogo::LFO1_OUTPUT));
		addOutput(createOutputCentered<PJ301MPort>(mm2px(Vec(15.24f, 82.f)), module, Pogo::LFO2_OUTPUT));

		// ── Zone 0c — MOD BUS ──────────────────────────────────────────────
		addParam(createParamCentered<Trimpot>(mm2px(Vec(5.08f, 105.f)), module, Pogo::MOD_AMOUNT_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(15.24f, 105.f)), module, Pogo::MOD_OFFSET_PARAM));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(5.08f, 118.f)), module, Pogo::MOD_IN_INPUT));
		addChild(createLightCentered<SmallLight<RedLight>>(mm2px(Vec(15.24f, 118.f)), module, Pogo::MOD_LIGHT));

		// ── Zone 1 — CONTROL / COMB ────────────────────────────────────────
		addParam(createParamCentered<RoundBlackKnob>(mm2px(Vec(29.0f, 23.f)), module, Pogo::COMB_BYPASS_PARAM));
		addParam(createParamCentered<RoundBlackKnob>(mm2px(Vec(42.14f, 23.f)), module, Pogo::WIDTH_PARAM));
		// POLARITY: 3-pos horizontal switch
		addParam(createParamCentered<PogoSwitchH3>(mm2px(Vec(35.56f, 37.2f)), module, Pogo::POLARITY_PARAM));
		addParam(createParamCentered<RoundHugeBlackKnob>(mm2px(Vec(35.56f, 59.f)), module, Pogo::MASTER_OFFSET_PARAM));

		// ── Zone 1 — CONTROL / DIST ────────────────────────────────────────
		// MODE: 3-pos vertical switch (correct orientation)
		addParam(createParamCentered<CKSSThree>(mm2px(Vec(28.f, 89.f)), module, Pogo::DIST_MODE_PARAM));
		addParam(createParamCentered<RoundBlackKnob>(mm2px(Vec(40.f, 89.f)), module, Pogo::FB_DIST_BLEND_PARAM));

		// ── Zone 1 — unified bottom row ────────────────────────────────────
		addParam(createParamCentered<Trimpot>(mm2px(Vec(25.40f, 111.f)), module, Pogo::BYPASS_ATT_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(35.56f, 111.f)), module, Pogo::MASTER_OFFSET_ATT_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(45.72f, 111.f)), module, Pogo::BLEND_ATT_PARAM));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(25.40f, 118.f)), module, Pogo::BYPASS_CV_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(35.56f, 118.f)), module, Pogo::MASTER_OFFSET_CV_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(45.72f, 118.f)), module, Pogo::BLEND_CV_INPUT));

		// ── Zone 2a — COMB 1 ───────────────────────────────────────────────
		addParam(createParamCentered<RoundHugeBlackKnob>(mm2px(Vec(66.04f, 34.f)), module, Pogo::FREQ_1_PARAM));
		addParam(createParamCentered<RoundLargeBlackKnob>(mm2px(Vec(66.04f, 63.f)), module, Pogo::FB_1_PARAM));
		addParam(createParamCentered<RoundLargeBlackKnob>(mm2px(Vec(66.04f, 89.f)), module, Pogo::DRIVE_1_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(55.88f, 111.f)), module, Pogo::FREQ_ATT_1_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(66.04f, 111.f)), module, Pogo::FB_ATT_1_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(76.20f, 111.f)), module, Pogo::DRIVE_ATT_1_PARAM));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(55.88f, 118.f)), module, Pogo::FREQ_CV_1_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(66.04f, 118.f)), module, Pogo::FB_CV_1_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(76.20f, 118.f)), module, Pogo::DRIVE_CV_1_INPUT));

		// ── Zone 2b — COMB 2 ───────────────────────────────────────────────
		addParam(createParamCentered<RoundHugeBlackKnob>(mm2px(Vec(96.52f, 34.f)), module, Pogo::FREQ_2_PARAM));
		addParam(createParamCentered<RoundLargeBlackKnob>(mm2px(Vec(96.52f, 63.f)), module, Pogo::FB_2_PARAM));
		addParam(createParamCentered<RoundLargeBlackKnob>(mm2px(Vec(96.52f, 89.f)), module, Pogo::DRIVE_2_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(86.36f, 111.f)), module, Pogo::FREQ_ATT_2_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(96.52f, 111.f)), module, Pogo::FB_ATT_2_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(106.68f, 111.f)), module, Pogo::DRIVE_ATT_2_PARAM));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(86.36f, 118.f)), module, Pogo::FREQ_CV_2_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(96.52f, 118.f)), module, Pogo::FB_CV_2_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(106.68f, 118.f)), module, Pogo::DRIVE_CV_2_INPUT));

		// ── Zone 2c — COMB 3 ───────────────────────────────────────────────
		addParam(createParamCentered<RoundHugeBlackKnob>(mm2px(Vec(127.00f, 34.f)), module, Pogo::FREQ_3_PARAM));
		addParam(createParamCentered<RoundLargeBlackKnob>(mm2px(Vec(127.00f, 63.f)), module, Pogo::FB_3_PARAM));
		addParam(createParamCentered<RoundLargeBlackKnob>(mm2px(Vec(127.00f, 89.f)), module, Pogo::DRIVE_3_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(116.84f, 111.f)), module, Pogo::FREQ_ATT_3_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(127.00f, 111.f)), module, Pogo::FB_ATT_3_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(137.16f, 111.f)), module, Pogo::DRIVE_ATT_3_PARAM));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(116.84f, 118.f)), module, Pogo::FREQ_CV_3_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(127.00f, 118.f)), module, Pogo::FB_CV_3_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(137.16f, 118.f)), module, Pogo::DRIVE_CV_3_INPUT));

		// ── Zone 3 — VCA (top strip) ───────────────────────────────────────
		addParam(createParamCentered<Trimpot>(mm2px(Vec(147.32f, 16.f)), module, Pogo::VCA_AMT_PARAM));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(157.48f, 16.f)), module, Pogo::VCA_CV_INPUT));

		// ── Zone 3 — LP1 ───────────────────────────────────────────────────
		addParam(createParamCentered<RoundLargeBlackKnob>(mm2px(Vec(152.40f, 49.f)), module, Pogo::LP1_CUTOFF_PARAM));
		addParam(createParamCentered<RoundBlackKnob>(mm2px(Vec(152.40f, 72.f)), module, Pogo::LP1_SPREAD_PARAM));
		addParam(createParamCentered<RoundBlackKnob>(mm2px(Vec(152.40f, 95.f)), module, Pogo::LP1_RESONANCE_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(147.32f, 111.f)), module, Pogo::LP1_CUT_ATT_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(157.48f, 111.f)), module, Pogo::LP1_RES_ATT_PARAM));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(147.32f, 118.f)), module, Pogo::LP1_CUT_CV_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(157.48f, 118.f)), module, Pogo::LP1_RES_CV_INPUT));

		// ── Zone 4 — BAND OUT (top strip) ─────────────────────────────────
		addOutput(createOutputCentered<PJ301MPort>(mm2px(Vec(167.64f, 16.f)), module, Pogo::BAND_L_OUTPUT));
		addOutput(createOutputCentered<PJ301MPort>(mm2px(Vec(177.80f, 16.f)), module, Pogo::BAND_R_OUTPUT));

		// ── Zone 4 — LP2 ───────────────────────────────────────────────────
		// LP2 CUTOFF: vertical slider, 13mm x 45mm, center at track midpoint
		addParam(createParamCentered<PogoSlider>(mm2px(Vec(172.72f, 64.5f)), module, Pogo::LP2_CUTOFF_PARAM));
		addParam(createParamCentered<RoundBlackKnob>(mm2px(Vec(172.72f, 95.f)), module, Pogo::LP2_RESONANCE_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(167.64f, 111.f)), module, Pogo::LP2_CUT_ATT_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(177.80f, 111.f)), module, Pogo::LP2_RES_ATT_PARAM));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(167.64f, 118.f)), module, Pogo::LP2_CUT_CV_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(177.80f, 118.f)), module, Pogo::LP2_RES_CV_INPUT));

		// ── Zone 5 — OUT (top strip) ───────────────────────────────────────
		addOutput(createOutputCentered<PJ301MPort>(mm2px(Vec(187.96f, 16.f)), module, Pogo::L_OUTPUT));
		addOutput(createOutputCentered<PJ301MPort>(mm2px(Vec(198.12f, 16.f)), module, Pogo::R_OUTPUT));

		// ── Zone 5 — HP ────────────────────────────────────────────────────
		// HP CUTOFF: vertical slider, matching LP2 geometry
		addParam(createParamCentered<PogoSlider>(mm2px(Vec(193.04f, 64.5f)), module, Pogo::HP_CUTOFF_PARAM));
		addParam(createParamCentered<RoundBlackKnob>(mm2px(Vec(193.04f, 95.f)), module, Pogo::HP_RESONANCE_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(187.96f, 111.f)), module, Pogo::HP_CUT_ATT_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(198.12f, 111.f)), module, Pogo::HP_RES_ATT_PARAM));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(187.96f, 118.f)), module, Pogo::HP_CUT_CV_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(198.12f, 118.f)), module, Pogo::HP_RES_CV_INPUT));
	}
};

Model* modelPogo = createModel<Pogo, PogoWidget>("Pogo");
