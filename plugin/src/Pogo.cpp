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
		GAIN_MAIN_PARAM,        // switch 0/1: 1× / 5×
		GAIN_BP3_PARAM,         // switch 0/1: 1× / 5× (ALT path pre-gain)
		// Zone 0b — LFO
		LFO1_RATE_PARAM,
		LFO2_RATE_PARAM,
		// Zone 0c — MOD BUS / VCA
		MOD_SCALE_PARAM,        // trimpot 0–1 → 0.2×–5×
		MOD_OFFSET_PARAM,       // trimpot −1–1 → ±5 V
		VCA_AMT_PARAM,          // trimpot −1–1 (bipolar attenuverter)
		VCA_OFS_PARAM,          // trimpot 0–1  (CV floor offset)
		// LP1
		LP1_FREQ_PARAM,         // xl knob −5–5 V/oct
		LP1_TILT_PARAM,         // large knob −1–1 → ±5 V/oct stereo tilt
		LP1_RES_PARAM,          // large knob 0–1
		LP1_FREQ_ATT_PARAM,
		LP1_TILT_ATT_PARAM,
		LP1_RES_ATT_PARAM,
		// BP Control (global)
		BP_TILT_PARAM,          // medium knob ±1 V/oct stereo spread
		BP_DIST_PARAM,          // switch 0/1/2: SOFT / HARD / FOLD
		BP_OFFSET_PARAM,        // large knob ±1.1 V/oct
		BP_MIX_PARAM,           // medium knob 0–1 dry/wet
		BP_FREQ_ATT_PARAM,
		BP_TILT_ATT_PARAM,
		// BP1
		BP1_FREQ_PARAM, BP1_FOCUS_PARAM, BP1_TILT_PARAM, BP1_DIST_PARAM,
		BP1_FREQ_ATT_PARAM, BP1_TILT_ATT_PARAM, BP1_DIST_ATT_PARAM,
		// BP2
		BP2_FREQ_PARAM, BP2_FOCUS_PARAM, BP2_DIST_PARAM,
		BP2_FREQ_ATT_PARAM, BP2_TILT_ATT_PARAM, BP2_DIST_ATT_PARAM,
		// BP3
		BP3_FREQ_PARAM, BP3_FOCUS_PARAM, BP3_DIST_PARAM,
		BP3_FREQ_ATT_PARAM, BP3_TILT_ATT_PARAM, BP3_DIST_ATT_PARAM,
		// HP
		HP_FREQ_PARAM, HP_RES_PARAM,
		HP_FREQ_ATT_PARAM, HP_RES_ATT_PARAM,
		// LP2
		LP2_FREQ_PARAM, LP2_RES_PARAM,
		LP2_FREQ_ATT_PARAM, LP2_RES_ATT_PARAM,
		NUM_PARAMS   // 46
	};

	enum InputId {
		L_IN_INPUT, R_IN_INPUT,
		ALT_BP_L_INPUT, ALT_BP_R_INPUT,
		MOD_INPUT, VCA_INPUT,
		LP1_FREQ_INPUT, LP1_TILT_INPUT, LP1_RES_INPUT,
		BP_FREQ_INPUT, BP_TILT_INPUT,
		BP1_FREQ_INPUT, BP1_TILT_INPUT, BP1_DIST_INPUT,
		BP2_FREQ_INPUT, BP2_TILT_INPUT, BP2_DIST_INPUT,
		BP3_FREQ_INPUT, BP3_TILT_INPUT, BP3_DIST_INPUT,
		HP_FREQ_INPUT, HP_RES_INPUT,
		LP2_FREQ_INPUT, LP2_RES_INPUT,
		NUM_INPUTS   // 24
	};

	enum OutputId {
		LFO1_OUTPUT, LFO2_OUTPUT,
		BP3_L_OUTPUT, BP3_R_OUTPUT,
		MAIN_L_OUTPUT, MAIN_R_OUTPUT,
		NUM_OUTPUTS   // 6
	};

	enum LightId {
		LFO1_LIGHT, LFO2_LIGHT,
		MOD_CLIP_LIGHT, MOD_POS_LIGHT, MOD_NEG_LIGHT,
		NUM_LIGHTS   // 5
	};

	Pogo() {
		config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS, NUM_LIGHTS);

		// Zone 0a
		configSwitch(GAIN_MAIN_PARAM, 0.f, 1.f, 0.f, "Main Gain", {"1\xc3\x97", "5\xc3\x97"});
		configSwitch(GAIN_BP3_PARAM,  0.f, 1.f, 0.f, "Alt BP3 Gain", {"1\xc3\x97", "5\xc3\x97"});

		// Zone 0b
		configParam(LFO1_RATE_PARAM, 0.f, 1.f, 0.3f, "LFO 1 Rate");
		configParam(LFO2_RATE_PARAM, 0.f, 1.f, 0.3f, "LFO 2 Rate");

		// Zone 0c
		configParam(MOD_SCALE_PARAM,  0.f,  1.f, 0.5f, "Mod Scale");
		configParam(MOD_OFFSET_PARAM, -1.f, 1.f, 0.f,  "Mod Offset");
		configParam(VCA_AMT_PARAM,    -1.f, 1.f, 0.f,  "VCA Depth");
		configParam(VCA_OFS_PARAM,     0.f, 1.f, 0.5f, "VCA Floor Offset");

		// LP1
		configParam(LP1_FREQ_PARAM, -5.f, 5.f, 0.f, "LP1 Freq", " V/oct");
		configParam(LP1_TILT_PARAM, -1.f, 1.f, 0.f, "LP1 Stereo Tilt");
		configParam(LP1_RES_PARAM,   0.f, 1.f, 0.f, "LP1 Resonance");
		configParam(LP1_FREQ_ATT_PARAM, -1.f, 1.f, 0.f, "LP1 Freq CV Depth");
		configParam(LP1_TILT_ATT_PARAM, -1.f, 1.f, 0.f, "LP1 Tilt CV Depth");
		configParam(LP1_RES_ATT_PARAM,  -1.f, 1.f, 0.f, "LP1 Res CV Depth");

		// BP Control
		configParam(BP_TILT_PARAM,   -1.f, 1.f, 0.f, "BP Tilt", " V/oct");
		configSwitch(BP_DIST_PARAM, 0.f, 2.f, 0.f, "BP Distortion Mode", {"Soft Clip", "Hard Clip", "Wavefold"});
		configParam(BP_OFFSET_PARAM, -1.1f, 1.1f, 0.f, "BP Master Offset", " V/oct");
		configParam(BP_MIX_PARAM,    0.f, 1.f, 0.5f, "BP Mix");
		configParam(BP_FREQ_ATT_PARAM, -1.f, 1.f, 0.f, "BP Offset CV Depth");
		configParam(BP_TILT_ATT_PARAM, -1.f, 1.f, 0.f, "BP Tilt CV Depth");

		// BP1/2/3 — all sweep 40 Hz–4 kHz (F_REF=400 Hz, ±log2(10) V/oct)
		const float bpR = std::log2(10.f); // 3.322: 400×2^±bpR = [40 Hz, 4 kHz]
		configParam<FormantFreqQuantity>(BP1_FREQ_PARAM,  -bpR, bpR, 0.f, "BP1 Freq")->fref = 400.f;
		configParam(BP1_FOCUS_PARAM,  0.f, 1.f, 0.f,   "BP1 Focus");
		configParam(BP1_TILT_PARAM,  -1.f, 1.f, 0.f,  "BP1 Tilt", " V/oct");
		configParam(BP1_DIST_PARAM,   0.f, 1.f, 0.20f, "BP1 Drive");
		configParam(BP1_FREQ_ATT_PARAM,  -1.f, 1.f, 0.f, "BP1 Freq CV Depth");
		configParam(BP1_TILT_ATT_PARAM, -1.f, 1.f, 0.f, "BP1 Tilt CV Depth");
		configParam(BP1_DIST_ATT_PARAM,  -1.f, 1.f, 0.f, "BP1 Drive CV Depth");

		// BP2
		configParam<FormantFreqQuantity>(BP2_FREQ_PARAM,  -bpR, bpR, 0.f, "BP2 Freq")->fref = 400.f;
		configParam(BP2_FOCUS_PARAM,  0.f, 1.f, 0.f,   "BP2 Focus");
		configParam(BP2_DIST_PARAM,   0.f, 1.f, 0.20f, "BP2 Drive");
		configParam(BP2_FREQ_ATT_PARAM,  -1.f, 1.f, 0.f, "BP2 Freq CV Depth");
		configParam(BP2_TILT_ATT_PARAM, -1.f, 1.f, 0.f, "BP2 Tilt CV Depth");
		configParam(BP2_DIST_ATT_PARAM,  -1.f, 1.f, 0.f, "BP2 Drive CV Depth");

		// BP3
		configParam<FormantFreqQuantity>(BP3_FREQ_PARAM,  -bpR, bpR, 0.f, "BP3 Freq")->fref = 400.f;
		configParam(BP3_FOCUS_PARAM,  0.f, 1.f, 0.f,   "BP3 Focus");
		configParam(BP3_DIST_PARAM,   0.f, 1.f, 0.20f, "BP3 Drive");
		configParam(BP3_FREQ_ATT_PARAM,  -1.f, 1.f, 0.f, "BP3 Freq CV Depth");
		configParam(BP3_TILT_ATT_PARAM, -1.f, 1.f, 0.f, "BP3 Tilt CV Depth");
		configParam(BP3_DIST_ATT_PARAM,  -1.f, 1.f, 0.f, "BP3 Drive CV Depth");

		// HP
		configParam(HP_FREQ_PARAM, -5.f, 5.f, -3.f, "HP Freq", " V/oct");
		configParam(HP_RES_PARAM,   0.f, 1.f,  0.f, "HP Resonance");
		configParam(HP_FREQ_ATT_PARAM, -1.f, 1.f, 0.f, "HP Freq CV Depth");
		configParam(HP_RES_ATT_PARAM,  -1.f, 1.f, 0.f, "HP Res CV Depth");

		// LP2
		configParam(LP2_FREQ_PARAM, -5.f, 5.f, 2.f, "LP2 Freq", " V/oct");
		configParam(LP2_RES_PARAM,   0.f, 1.f, 0.f, "LP2 Resonance");
		configParam(LP2_FREQ_ATT_PARAM, -1.f, 1.f, 0.f, "LP2 Freq CV Depth");
		configParam(LP2_RES_ATT_PARAM,  -1.f, 1.f, 0.f, "LP2 Res CV Depth");

		// Inputs (24)
		configInput(L_IN_INPUT,      "Audio L");
		configInput(R_IN_INPUT,      "Audio R");
		configInput(ALT_BP_L_INPUT,  "Alt BP L");
		configInput(ALT_BP_R_INPUT,  "Alt BP R");
		configInput(MOD_INPUT,       "Mod Source");
		configInput(VCA_INPUT,       "VCA CV");
		configInput(LP1_FREQ_INPUT,  "LP1 Freq CV");
		configInput(LP1_TILT_INPUT,  "LP1 Tilt CV");
		configInput(LP1_RES_INPUT,   "LP1 Res CV");
		configInput(BP_FREQ_INPUT,   "BP Offset CV");
		configInput(BP_TILT_INPUT,   "BP Tilt CV");
		configInput(BP1_FREQ_INPUT,  "BP1 Freq CV");
		configInput(BP1_TILT_INPUT,  "BP1 Tilt CV");
		configInput(BP1_DIST_INPUT,  "BP1 Drive CV");
		configInput(BP2_FREQ_INPUT,  "BP2 Freq CV");
		configInput(BP2_TILT_INPUT,  "BP2 Tilt CV");
		configInput(BP2_DIST_INPUT,  "BP2 Drive CV");
		configInput(BP3_FREQ_INPUT,  "BP3 Freq CV");
		configInput(BP3_TILT_INPUT,  "BP3 Tilt CV");
		configInput(BP3_DIST_INPUT,  "BP3 Drive CV");
		configInput(HP_FREQ_INPUT,   "HP Freq CV");
		configInput(HP_RES_INPUT,    "HP Res CV");
		configInput(LP2_FREQ_INPUT,  "LP2 Freq CV");
		configInput(LP2_RES_INPUT,   "LP2 Res CV");

		// Outputs (6)
		configOutput(LFO1_OUTPUT,   "LFO 1");
		configOutput(LFO2_OUTPUT,   "LFO 2");
		configOutput(BP3_L_OUTPUT,  "BP3 L");
		configOutput(BP3_R_OUTPUT,  "BP3 R");
		configOutput(MAIN_L_OUTPUT, "Audio L");
		configOutput(MAIN_R_OUTPUT, "Audio R");

		// Lights (5)
		configLight(LFO1_LIGHT,     "LFO 1");
		configLight(LFO2_LIGHT,     "LFO 2");
		configLight(MOD_CLIP_LIGHT, "Mod Clip");
		configLight(MOD_POS_LIGHT,  "Mod +");
		configLight(MOD_NEG_LIGHT,  "Mod \xe2\x88\x92");
	}

	// ── DSP state ────────────────────────────────────────────────────────────
	LFO lfo1, lfo2;
	TripleBandpass bandpassL, bandpassR;
	// Distortion taps — post-SVF per-group distorted outputs
	float distTapL[3] = {}, distTapR[3] = {};
	LPFilter lp1L, lp1R;
	LPFilter lp2L, lp2R;
	HPFilter hpL, hpR;

	void onReset() override {
		lfo1.reset(); lfo2.reset();
		bandpassL.reset(); bandpassR.reset();
		for (int i = 0; i < 3; i++) distTapL[i] = distTapR[i] = 0.f;
		lp1L.reset(); lp1R.reset();
		lp2L.reset(); lp2R.reset();
		hpL.reset();  hpR.reset();
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

		// ── Block 1: pre-gain boost (main path) ──────────────────────────────
		float pgL = PreGain::process(inL, params[GAIN_MAIN_PARAM].getValue());
		float pgR = PreGain::process(inR, params[GAIN_MAIN_PARAM].getValue());

		// ALT path: ALT_BP_L/R → GAIN_BP3 → bypasses VCA+LP1, feeds BP directly
		bool altLConn = inputs[ALT_BP_L_INPUT].isConnected();
		bool altRConn = inputs[ALT_BP_R_INPUT].isConnected();
		float altL = altLConn
		    ? PreGain::process(inputs[ALT_BP_L_INPUT].getVoltage(), params[GAIN_BP3_PARAM].getValue())
		    : 0.f;
		float altR = altRConn
		    ? PreGain::process(inputs[ALT_BP_R_INPUT].getVoltage(), params[GAIN_BP3_PARAM].getValue())
		    : (altLConn ? altL : 0.f); // normalise R to L alt if only L patched

		// ── LFOs ─────────────────────────────────────────────────────────────
		float lfo1Raw = lfo1.process(params[LFO1_RATE_PARAM].getValue(), dt);
		float lfo2Raw = lfo2.process(params[LFO2_RATE_PARAM].getValue(), dt);
		float lfo1V   = lfo1Raw * 5.f;   // ±5 V
		float lfo2V   = lfo2Raw * 5.f;   // ±5 V

		// ── Mod bus ───────────────────────────────────────────────────────────
		// LFO1 normalises to mod bus; MOD_INPUT jack overrides when patched
		float modSrcV = inputs[MOD_INPUT].isConnected()
		                ? inputs[MOD_INPUT].getVoltage()
		                : lfo1V;

		float busV = ModBusProcessor::process(modSrcV,
		                                      params[MOD_SCALE_PARAM].getValue(),
		                                      params[MOD_OFFSET_PARAM].getValue());

		// Helper: resolve one mod destination (bus normalised to CV override + att)
		auto modDest = [&](int cvInput, int attParam) -> float {
			bool has = inputs[cvInput].isConnected();
			return applyDestination(busV,
			                        inputs[cvInput].getVoltage(),
			                        has,
			                        params[attParam].getValue());
		};

		// ── Block VCA ─────────────────────────────────────────────────────────
		// VCA_INPUT normalises to mod bus; VCA_OFS shifts effective CV floor.
		float vcaCVraw = inputs[VCA_INPUT].isConnected()
		                 ? inputs[VCA_INPUT].getVoltage()
		                 : busV;
		float vcaCV = clamp(vcaCVraw + params[VCA_OFS_PARAM].getValue() * 5.f, 0.f, 10.f);
		float vcaAmt = params[VCA_AMT_PARAM].getValue();
		float vcaOutL = VcaBlock::process(pgL, vcaAmt, vcaCV);
		float vcaOutR = VcaBlock::process(pgR, vcaAmt, vcaCV);

		// ── Block LP1: 2-pole SVF LP (stereo tilt) ───────────────────────────
		// L cutoff = base + tiltV;  R cutoff = base − tiltV
		float lp1FreqBase = params[LP1_FREQ_PARAM].getValue()
		                    + modDest(LP1_FREQ_INPUT, LP1_FREQ_ATT_PARAM);
		float lp1TiltV    = params[LP1_TILT_PARAM].getValue() * 5.f   // −1→+1 knob → ±5 V/oct
		                    + modDest(LP1_TILT_INPUT, LP1_TILT_ATT_PARAM);
		float lp1Res      = clamp(params[LP1_RES_PARAM].getValue()
		                    + modDest(LP1_RES_INPUT, LP1_RES_ATT_PARAM) / 10.f, 0.f, 1.f);
		float bandL = lp1L.process(vcaOutL, lp1FreqBase + lp1TiltV, lp1Res, fs);
		float bandR = lp1R.process(vcaOutR, lp1FreqBase - lp1TiltV, lp1Res, fs);

		// ── Block BP: 2× oversampled triple bandpass + distortion ────────────
		// Pre-compute all BP CVs at base rate
		float bpOffsetCv = params[BP_OFFSET_PARAM].getValue()
		                   + modDest(BP_FREQ_INPUT, BP_FREQ_ATT_PARAM);
		float bpTiltCv   = params[BP_TILT_PARAM].getValue()
		                   + modDest(BP_TILT_INPUT, BP_TILT_ATT_PARAM); // stereo tilt: L+=, R-=

		int distMode    = (int)std::round(params[BP_DIST_PARAM].getValue());
		float mix       = params[BP_MIX_PARAM].getValue();

		float freqV[3] = {
			bpOffsetCv + params[BP1_FREQ_PARAM].getValue() + modDest(BP1_FREQ_INPUT, BP1_FREQ_ATT_PARAM),
			bpOffsetCv + params[BP2_FREQ_PARAM].getValue() + modDest(BP2_FREQ_INPUT, BP2_FREQ_ATT_PARAM),
			bpOffsetCv + params[BP3_FREQ_PARAM].getValue() + modDest(BP3_FREQ_INPUT, BP3_FREQ_ATT_PARAM),
		};
		float focusCv[3] = {
			clamp(params[BP1_FOCUS_PARAM].getValue(), 0.f, 1.f),
			clamp(params[BP2_FOCUS_PARAM].getValue(), 0.f, 1.f),
			clamp(params[BP3_FOCUS_PARAM].getValue(), 0.f, 1.f),
		};
		// Per-group tilt: knob (±1 V/oct) + scaled CV (±1.1 oct at full att); added to global bpTiltCv
		float groupTiltV[3] = {
			params[BP1_TILT_PARAM].getValue() + modDest(BP1_TILT_INPUT, BP1_TILT_ATT_PARAM) * 0.22f,
			modDest(BP2_TILT_INPUT, BP2_TILT_ATT_PARAM) * 0.22f,
			modDest(BP3_TILT_INPUT, BP3_TILT_ATT_PARAM) * 0.22f,
		};
		float driveCv[3] = {
			clamp(params[BP1_DIST_PARAM].getValue() + modDest(BP1_DIST_INPUT, BP1_DIST_ATT_PARAM), 0.f, 1.f),
			clamp(params[BP2_DIST_PARAM].getValue() + modDest(BP2_DIST_INPUT, BP2_DIST_ATT_PARAM), 0.f, 1.f),
			clamp(params[BP3_DIST_PARAM].getValue() + modDest(BP3_DIST_INPUT, BP3_DIST_ATT_PARAM), 0.f, 1.f),
		};

		// ALT path feeds BP3 only (VCA-applied); BP1+BP2 always use LP1 output
		float bp3InL = altLConn ? VcaBlock::process(altL, vcaAmt, vcaCV) : bandL;
		float bp3InR = (altLConn || altRConn) ? VcaBlock::process(altR, vcaAmt, vcaCV) : bandR;

		// Per-group tilt: global bpTiltCv + per-band groupTiltV; L gets +, R gets −
		float tiltL[3] = { bpTiltCv + groupTiltV[0], bpTiltCv + groupTiltV[1], bpTiltCv + groupTiltV[2] };
		float tiltR[3] = { -(bpTiltCv + groupTiltV[0]), -(bpTiltCv + groupTiltV[1]), -(bpTiltCv + groupTiltV[2]) };
		bandpassL.process(bandL, bp3InL, freqV, focusCv, tiltL, fs);
		bandpassR.process(bandR, bp3InR, freqV, focusCv, tiltR, fs);

		float dSumL = 0.f, dSumR = 0.f;
		for (int i = 0; i < 3; i++) {
			distTapL[i] = Distortion::process(bandpassL.prevOut[i], driveCv[i], distMode);
			distTapR[i] = Distortion::process(bandpassR.prevOut[i], driveCv[i], distMode);
			dSumL += distTapL[i];
			dSumR += distTapR[i];
		}
		float wetL    = clamp(dSumL, -10.5f, 10.5f);
		float wetR    = clamp(dSumR, -10.5f, 10.5f);
		float bp3OutL = distTapL[2];
		float bp3OutR = distTapR[2];

		// BP_MIX: crossfade — CCW (0) = LP1 bypass, CW (1) = full BP only
		float bpOutL = clamp(bandL * (1.f - mix) + wetL * mix, -12.f, 12.f);
		float bpOutR = clamp(bandR * (1.f - mix) + wetR * mix, -12.f, 12.f);

		// ── Block HP: 2-pole SVF HP ───────────────────────────────────────────
		float hpFreqCv = params[HP_FREQ_PARAM].getValue()
		                 + modDest(HP_FREQ_INPUT, HP_FREQ_ATT_PARAM);
		float hpResCv  = clamp(params[HP_RES_PARAM].getValue()
		                 + modDest(HP_RES_INPUT, HP_RES_ATT_PARAM) / 10.f, 0.f, 1.f);
		float hpOutL = hpL.process(bpOutL, hpFreqCv, hpResCv, fs);
		float hpOutR = hpR.process(bpOutR, hpFreqCv, hpResCv, fs);

		// ── Block LP2: 2-pole SVF LP ──────────────────────────────────────────
		float lp2FreqCv = params[LP2_FREQ_PARAM].getValue()
		                  + modDest(LP2_FREQ_INPUT, LP2_FREQ_ATT_PARAM);
		float lp2ResCv  = clamp(params[LP2_RES_PARAM].getValue()
		                  + modDest(LP2_RES_INPUT, LP2_RES_ATT_PARAM) / 10.f, 0.f, 1.f);
		float outL = lp2L.process(hpOutL, lp2FreqCv, lp2ResCv, fs);
		float outR = lp2R.process(hpOutR, lp2FreqCv, lp2ResCv, fs);

		// ── Block B: output buffers ───────────────────────────────────────────
		outputs[MAIN_L_OUTPUT].setVoltage(clamp(outL,    -11.f, 11.f));
		outputs[MAIN_R_OUTPUT].setVoltage(clamp(outR,    -11.f, 11.f));
		outputs[BP3_L_OUTPUT ].setVoltage(clamp(bp3OutL, -11.f, 11.f));
		outputs[BP3_R_OUTPUT ].setVoltage(clamp(
		    outputs[BP3_R_OUTPUT].isConnected() ? bp3OutR : bp3OutL, -11.f, 11.f));
		outputs[LFO1_OUTPUT  ].setVoltage(lfo1V);
		outputs[LFO2_OUTPUT  ].setVoltage(lfo2V);

		// LEDs
		lights[LFO1_LIGHT    ].setBrightness((lfo1Raw + 1.f) * 0.5f);
		lights[LFO2_LIGHT    ].setBrightness((lfo2Raw + 1.f) * 0.5f);
		lights[MOD_CLIP_LIGHT].setBrightness(std::abs(busV) >= 9.9f ? 1.f : 0.f);
		lights[MOD_POS_LIGHT ].setBrightness(busV >  0.f ? clamp( busV / 10.f, 0.f, 1.f) : 0.f);
		lights[MOD_NEG_LIGHT ].setBrightness(busV < 0.f ? clamp(-busV / 10.f, 0.f, 1.f) : 0.f);
	}
};

// ─────────────────────────────────────────────────────────────────────────
struct PogoWidget : ModuleWidget {
	PogoWidget(Pogo* module) {
		setModule(module);
		setPanel(createPanel(asset::plugin(pluginInstance, "res/Pogo.svg")));
		// All text labels are in res/Pogo.svg — no addLabel() calls needed.

		// ── Zone 0a — INPUT / GAIN ─────────────────────────────────────
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(7.62f, 17.00f)), module, Pogo::L_IN_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(19.05f, 17.00f)), module, Pogo::R_IN_INPUT));
		addParam(createParamCentered<PogoSwitchH2>(mm2px(Vec(30.48f, 17.00f)), module, Pogo::GAIN_MAIN_PARAM));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(7.62f, 31.50f)), module, Pogo::ALT_BP_L_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(19.05f, 31.50f)), module, Pogo::ALT_BP_R_INPUT));
		addParam(createParamCentered<PogoSwitchH2>(mm2px(Vec(30.48f, 31.50f)), module, Pogo::GAIN_BP3_PARAM));

		// ── Zone 0b — LFO ──────────────────────────────────────────────
		addOutput(createOutputCentered<PJ301MPort>(mm2px(Vec(7.62f, 51.50f)), module, Pogo::LFO1_OUTPUT));
		addChild(createLightCentered<SmallLight<GreenLight>>(mm2px(Vec(19.05f, 51.50f)), module, Pogo::LFO1_LIGHT));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(30.48f, 51.50f)), module, Pogo::LFO1_RATE_PARAM));
		addOutput(createOutputCentered<PJ301MPort>(mm2px(Vec(7.62f, 65.90f)), module, Pogo::LFO2_OUTPUT));
		addChild(createLightCentered<SmallLight<GreenLight>>(mm2px(Vec(19.05f, 65.90f)), module, Pogo::LFO2_LIGHT));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(30.48f, 65.90f)), module, Pogo::LFO2_RATE_PARAM));

		// ── Zone 0c — MOD BUS / VCA ────────────────────────────────────
		addParam(createParamCentered<Trimpot>(mm2px(Vec(7.62f, 83.00f)), module, Pogo::MOD_SCALE_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(30.48f, 83.00f)), module, Pogo::VCA_AMT_PARAM));
		addChild(createLightCentered<SmallLight<GreenLight>>(mm2px(Vec(19.05f, 83.00f)), module, Pogo::MOD_CLIP_LIGHT));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(7.62f, 96.34f)), module, Pogo::MOD_OFFSET_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(30.48f, 96.34f)), module, Pogo::VCA_OFS_PARAM));
		addChild(createLightCentered<SmallLight<GreenLight>>(mm2px(Vec(19.05f, 96.34f)), module, Pogo::MOD_POS_LIGHT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(7.62f, 112.00f)), module, Pogo::MOD_INPUT));
		addChild(createLightCentered<SmallLight<GreenLight>>(mm2px(Vec(19.05f, 112.00f)), module, Pogo::MOD_NEG_LIGHT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(30.48f, 112.00f)), module, Pogo::VCA_INPUT));

		// ── Zone — LP1 Low-Pass Filter ─────────────────────────────────
		addParam(createParamCentered<RoundHugeBlackKnob>(mm2px(Vec(53.34f, 24.80f)), module, Pogo::LP1_FREQ_PARAM));
		addParam(createParamCentered<RoundLargeBlackKnob>(mm2px(Vec(53.34f, 52.40f)), module, Pogo::LP1_TILT_PARAM));
		addParam(createParamCentered<RoundLargeBlackKnob>(mm2px(Vec(53.34f, 78.00f)), module, Pogo::LP1_RES_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(41.91f, 100.00f)), module, Pogo::LP1_FREQ_ATT_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(53.34f, 100.00f)), module, Pogo::LP1_TILT_ATT_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(64.77f, 100.00f)), module, Pogo::LP1_RES_ATT_PARAM));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(41.91f, 112.00f)), module, Pogo::LP1_FREQ_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(53.34f, 112.00f)), module, Pogo::LP1_TILT_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(64.77f, 112.00f)), module, Pogo::LP1_RES_INPUT));

		// ── Zone — BP CONTROL ──────────────────────────────────────────
		addParam(createParamCentered<RoundBlackKnob>(mm2px(Vec(81.915f, 24.80f)), module, Pogo::BP_OFFSET_PARAM));
		addParam(createParamCentered<RoundBlackKnob>(mm2px(Vec(81.915f, 43.20f)), module, Pogo::BP_TILT_PARAM));
		addParam(createParamCentered<RoundBlackKnob>(mm2px(Vec(81.915f, 61.60f)), module, Pogo::BP_MIX_PARAM));
		addParam(createParamCentered<PogoSwitchH3>(mm2px(Vec(81.915f, 80.00f)), module, Pogo::BP_DIST_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(76.200f, 100.00f)), module, Pogo::BP_FREQ_ATT_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(87.630f, 100.00f)), module, Pogo::BP_TILT_ATT_PARAM));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(76.200f, 112.00f)), module, Pogo::BP_FREQ_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(87.630f, 112.00f)), module, Pogo::BP_TILT_INPUT));

		// ── Zone — BP 1 ────────────────────────────────────────────────
		addParam(createParamCentered<RoundHugeBlackKnob>(mm2px(Vec(114.49f,  24.80f)), module, Pogo::BP1_FREQ_PARAM));
		addParam(createParamCentered<RoundLargeBlackKnob>(mm2px(Vec(101.345f, 47.69f)), module, Pogo::BP1_FOCUS_PARAM));
		addParam(createParamCentered<RoundLargeBlackKnob>(mm2px(Vec(119.635f, 63.85f)), module, Pogo::BP1_TILT_PARAM));
		addParam(createParamCentered<RoundLargeBlackKnob>(mm2px(Vec(101.345f, 80.00f)), module, Pogo::BP1_DIST_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(99.06f, 100.00f)), module, Pogo::BP1_FREQ_ATT_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(110.49f, 100.00f)), module, Pogo::BP1_TILT_ATT_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(121.92f, 100.00f)), module, Pogo::BP1_DIST_ATT_PARAM));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(99.06f, 112.00f)), module, Pogo::BP1_FREQ_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(110.49f, 112.00f)), module, Pogo::BP1_TILT_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(121.92f, 112.00f)), module, Pogo::BP1_DIST_INPUT));

		// ── Zone — BP 2 ────────────────────────────────────────────────
		addParam(createParamCentered<RoundHugeBlackKnob>(mm2px(Vec(144.78f, 24.80f)), module, Pogo::BP2_FREQ_PARAM));
		addParam(createParamCentered<RoundLargeBlackKnob>(mm2px(Vec(144.78f, 52.40f)), module, Pogo::BP2_FOCUS_PARAM));
		addParam(createParamCentered<RoundLargeBlackKnob>(mm2px(Vec(144.78f, 78.00f)), module, Pogo::BP2_DIST_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(133.35f, 100.00f)), module, Pogo::BP2_FREQ_ATT_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(144.78f, 100.00f)), module, Pogo::BP2_TILT_ATT_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(156.21f, 100.00f)), module, Pogo::BP2_DIST_ATT_PARAM));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(133.35f, 112.00f)), module, Pogo::BP2_FREQ_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(144.78f, 112.00f)), module, Pogo::BP2_TILT_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(156.21f, 112.00f)), module, Pogo::BP2_DIST_INPUT));

		// ── Zone — BP 3 ────────────────────────────────────────────────
		addParam(createParamCentered<RoundHugeBlackKnob>(mm2px(Vec(179.07f, 24.80f)), module, Pogo::BP3_FREQ_PARAM));
		addParam(createParamCentered<RoundLargeBlackKnob>(mm2px(Vec(179.07f, 52.40f)), module, Pogo::BP3_FOCUS_PARAM));
		addParam(createParamCentered<RoundLargeBlackKnob>(mm2px(Vec(179.07f, 78.00f)), module, Pogo::BP3_DIST_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(167.64f, 100.00f)), module, Pogo::BP3_FREQ_ATT_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(179.07f, 100.00f)), module, Pogo::BP3_TILT_ATT_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(190.50f, 100.00f)), module, Pogo::BP3_DIST_ATT_PARAM));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(167.64f, 112.00f)), module, Pogo::BP3_FREQ_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(179.07f, 112.00f)), module, Pogo::BP3_TILT_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(190.50f, 112.00f)), module, Pogo::BP3_DIST_INPUT));

		// ── Zone — BP3 OUT ─────────────────────────────────────────────
		addOutput(createOutputCentered<PJ301MPort>(mm2px(Vec(201.93f, 17.00f)), module, Pogo::BP3_L_OUTPUT));
		addOutput(createOutputCentered<PJ301MPort>(mm2px(Vec(213.36f, 17.00f)), module, Pogo::BP3_R_OUTPUT));

		// ── Zone — HP ──────────────────────────────────────────────────
		addParam(createParamCentered<PogoSlider>(mm2px(Vec(207.65f, 54.00f)), module, Pogo::HP_FREQ_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(207.645f, 87.00f)), module, Pogo::HP_RES_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(201.93f, 100.00f)), module, Pogo::HP_FREQ_ATT_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(213.36f, 100.00f)), module, Pogo::HP_RES_ATT_PARAM));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(201.93f, 112.00f)), module, Pogo::HP_FREQ_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(213.36f, 112.00f)), module, Pogo::HP_RES_INPUT));

		// ── Zone — MAIN OUT ────────────────────────────────────────────
		addOutput(createOutputCentered<PJ301MPort>(mm2px(Vec(224.79f, 17.00f)), module, Pogo::MAIN_L_OUTPUT));
		addOutput(createOutputCentered<PJ301MPort>(mm2px(Vec(236.22f, 17.00f)), module, Pogo::MAIN_R_OUTPUT));

		// ── Zone — LP2 ─────────────────────────────────────────────────
		addParam(createParamCentered<PogoSlider>(mm2px(Vec(230.50f, 54.00f)), module, Pogo::LP2_FREQ_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(230.505f, 87.00f)), module, Pogo::LP2_RES_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(224.79f, 100.00f)), module, Pogo::LP2_FREQ_ATT_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(236.22f, 100.00f)), module, Pogo::LP2_RES_ATT_PARAM));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(224.79f, 112.00f)), module, Pogo::LP2_FREQ_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(236.22f, 112.00f)), module, Pogo::LP2_RES_INPUT));
	}
};

Model* modelPogo = createModel<Pogo, PogoWidget>("Pogo");
