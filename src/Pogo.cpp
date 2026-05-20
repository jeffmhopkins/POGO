#include "plugin.hpp"

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
		configSwitch(GAIN_PARAM, 0.f, 1.f, 0.f, "Gain", {"1×", "5×"});

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
		configParam(DRIVE_1_PARAM, 0.f, 1.f, 0.f, "Comb 1 Drive");
		configParam(FREQ_ATT_1_PARAM, -1.f, 1.f, 0.f, "Comb 1 Freq CV Depth");
		configParam(FB_ATT_1_PARAM, -1.f, 1.f, 0.f, "Comb 1 FB CV Depth");
		configParam(DRIVE_ATT_1_PARAM, -1.f, 1.f, 0.f, "Comb 1 Drive CV Depth");

		// Comb 2
		configParam(FREQ_2_PARAM, -5.f, 5.f, 0.f, "Comb 2 Freq", " V/oct");
		configParam(FB_2_PARAM, 0.f, 1.f, 0.f, "Comb 2 Feedback");
		configParam(DRIVE_2_PARAM, 0.f, 1.f, 0.f, "Comb 2 Drive");
		configParam(FREQ_ATT_2_PARAM, -1.f, 1.f, 0.f, "Comb 2 Freq CV Depth");
		configParam(FB_ATT_2_PARAM, -1.f, 1.f, 0.f, "Comb 2 FB CV Depth");
		configParam(DRIVE_ATT_2_PARAM, -1.f, 1.f, 0.f, "Comb 2 Drive CV Depth");

		// Comb 3
		configParam(FREQ_3_PARAM, -5.f, 5.f, 0.f, "Comb 3 Freq", " V/oct");
		configParam(FB_3_PARAM, 0.f, 1.f, 0.f, "Comb 3 Feedback");
		configParam(DRIVE_3_PARAM, 0.f, 1.f, 0.f, "Comb 3 Drive");
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

	void process(const ProcessArgs& args) override {
		// Stage 0: pass audio straight through; all DSP is stubbed
		outputs[L_OUTPUT].setVoltage(inputs[L_IN_INPUT].getVoltage());
		outputs[R_OUTPUT].setVoltage(inputs[R_IN_INPUT].getVoltage());
		outputs[BAND_L_OUTPUT].setVoltage(inputs[L_IN_INPUT].getVoltage());
		outputs[BAND_R_OUTPUT].setVoltage(inputs[R_IN_INPUT].getVoltage());
		outputs[ENV_L_OUTPUT].setVoltage(0.f);
		outputs[ENV_R_OUTPUT].setVoltage(0.f);
	}
};

struct PogoWidget : ModuleWidget {
	PogoWidget(Pogo* module) {
		setModule(module);
		setPanel(createPanel(asset::plugin(pluginInstance, "res/Pogo.svg")));

		// ── Zone 0a — INPUT / GAIN ──────────────────────────────────────────
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(5.08f, 16.f)), module, Pogo::L_IN_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(15.24f, 16.f)), module, Pogo::R_IN_INPUT));
		// GAIN: 2-pos horizontal switch, body centered at (10.16, 28.2)
		addParam(createParamCentered<CKSS>(mm2px(Vec(10.16f, 28.2f)), module, Pogo::GAIN_PARAM));

		// ── Zone 0b — ENVELOPE ─────────────────────────────────────────────
		// MOD SRC: 3-pos horizontal switch at (10.16, 51)
		addParam(createParamCentered<CKSSThree>(mm2px(Vec(10.16f, 51.f)), module, Pogo::MOD_SRC_PARAM));
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
		// POLARITY: 3-pos horizontal switch, body center at (35.56, 35.2)
		addParam(createParamCentered<CKSSThree>(mm2px(Vec(35.56f, 35.2f)), module, Pogo::POLARITY_PARAM));
		addParam(createParamCentered<RoundHugeBlackKnob>(mm2px(Vec(35.56f, 57.f)), module, Pogo::MASTER_OFFSET_PARAM));

		// ── Zone 1 — CONTROL / DIST ────────────────────────────────────────
		// MODE: 3-pos vertical switch, center at (28, 87)
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
		// LP2 CUTOFF is a vertical slider (ALPS RS4515N); knob placeholder at track midpoint (Stage 0)
		addParam(createParamCentered<RoundBlackKnob>(mm2px(Vec(172.72f, 62.5f)), module, Pogo::LP2_CUTOFF_PARAM));
		addParam(createParamCentered<RoundBlackKnob>(mm2px(Vec(172.72f, 93.f)), module, Pogo::LP2_RESONANCE_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(167.64f, 109.f)), module, Pogo::LP2_CUT_ATT_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(177.80f, 109.f)), module, Pogo::LP2_RES_ATT_PARAM));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(167.64f, 118.f)), module, Pogo::LP2_CUT_CV_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(177.80f, 118.f)), module, Pogo::LP2_RES_CV_INPUT));

		// ── Zone 5 — OUT (top strip) ───────────────────────────────────────
		addOutput(createOutputCentered<PJ301MPort>(mm2px(Vec(187.96f, 16.f)), module, Pogo::L_OUTPUT));
		addOutput(createOutputCentered<PJ301MPort>(mm2px(Vec(198.12f, 16.f)), module, Pogo::R_OUTPUT));

		// ── Zone 5 — HP ────────────────────────────────────────────────────
		// HP CUTOFF is a vertical slider; knob placeholder at track midpoint (Stage 0)
		addParam(createParamCentered<RoundBlackKnob>(mm2px(Vec(193.04f, 62.5f)), module, Pogo::HP_CUTOFF_PARAM));
		addParam(createParamCentered<RoundBlackKnob>(mm2px(Vec(193.04f, 93.f)), module, Pogo::HP_RESONANCE_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(187.96f, 109.f)), module, Pogo::HP_CUT_ATT_PARAM));
		addParam(createParamCentered<Trimpot>(mm2px(Vec(198.12f, 109.f)), module, Pogo::HP_RES_ATT_PARAM));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(187.96f, 118.f)), module, Pogo::HP_CUT_CV_INPUT));
		addInput(createInputCentered<PJ301MPort>(mm2px(Vec(198.12f, 118.f)), module, Pogo::HP_RES_CV_INPUT));
	}
};

Model* modelPogo = createModel<Pogo, PogoWidget>("Pogo");
