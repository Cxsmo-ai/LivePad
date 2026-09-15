(function (root) {
  "use strict";

  const Protocol = root.HMProtocol || (typeof require === "function" ? require("./protocol.js") : null);
  const BUTTON_INDEX = Object.freeze({
    0: "a", 1: "b", 2: "x", 3: "y", 4: "lb", 5: "rb",
    8: "back", 9: "start", 10: "l3", 11: "r3",
    12: "dpad_up", 13: "dpad_down", 14: "dpad_left", 15: "dpad_right", 16: "guide"
  });
  const PLATFORM_TIMINGS = Object.freeze({
    // Twitch's regular-user bucket is 20 messages per 30 seconds, so its
    // automatic cadence stays just above 1.5 seconds. TikTok and YouTube do
    // not publish an equivalent browser-chat interval; these are conservative
    // application defaults that can be tuned in the popup.
    twitch: Object.freeze({ cadenceMs: 1550, keepaliveMs: 2500 }),
    youtube: Object.freeze({ cadenceMs: 2000, keepaliveMs: 3500 }),
    tiktok: Object.freeze({ cadenceMs: 350, keepaliveMs: 900 })
  });
  const PLATFORM_CADENCE_MS = Object.freeze(Object.fromEntries(
    Object.entries(PLATFORM_TIMINGS).map(([platform, timing]) => [platform, timing.cadenceMs])
  ));
  const NEUTRAL_FINGERPRINT = "0/0/0/0/0/0/0";

  function clamp(value, minimum, maximum) {
    return Math.max(minimum, Math.min(maximum, value));
  }

  function radialDeadzone(x, y, deadzone = 0.14, curve = 1.0) {
    const magnitude = Math.hypot(x, y);
    if (magnitude <= deadzone) return [0, 0];
    const normalizedMagnitude = Math.min(1, (magnitude - deadzone) / (1 - deadzone));
    const curved = Math.pow(normalizedMagnitude, clamp(curve, 0.5, 3));
    const scale = curved / magnitude;
    return [clamp(x * scale, -1, 1), clamp(y * scale, -1, 1)];
  }

  function quantizePercent(value, step = 5) {
    const safeStep = clamp(Math.round(step), 1, 25);
    const percent = clamp(value, -1, 1) * 100;
    return clamp(Math.round(percent / safeStep) * safeStep, -100, 100);
  }

  function sampleStandardGamepad(gamepad, settings = {}, previousHeldMask = 0) {
    if (!gamepad || gamepad.connected === false) throw new Error("gamepad unavailable");
    if (gamepad.mapping && gamepad.mapping !== "standard") {
      throw new Error("controller does not expose the standard browser mapping");
    }
    const axes = gamepad.axes || [];
    const buttons = gamepad.buttons || [];
    const deadzone = Number(settings.deadzone ?? 0.14);
    const curve = Number(settings.curve ?? 1.0);
    const step = Number(settings.quantizeStep ?? 5);
    const [leftX, leftYBrowser] = radialDeadzone(Number(axes[0] || 0), Number(axes[1] || 0), deadzone, curve);
    const [rightX, rightYBrowser] = radialDeadzone(Number(axes[2] || 0), Number(axes[3] || 0), deadzone, curve);

    let heldMask = 0;
    for (const [indexText, name] of Object.entries(BUTTON_INDEX)) {
      const button = buttons[Number(indexText)];
      if (button && (button.pressed || Number(button.value) >= 0.5)) heldMask |= Protocol.BUTTONS[name];
    }
    const triggerDeadzone = Number(settings.triggerDeadzone ?? 0.05);
    const trigger = (button) => {
      const value = clamp(Number(button?.value || 0), 0, 1);
      return value <= triggerDeadzone ? 0 : (value - triggerDeadzone) / (1 - triggerDeadzone);
    };
    const tapMask = heldMask & ~previousHeldMask;
    return {
      lx: quantizePercent(leftX, step),
      // Browser standard mapping reports up as negative. The host protocol defines forward/up positive.
      ly: quantizePercent(-leftYBrowser, step),
      rx: quantizePercent(rightX, step),
      ry: quantizePercent(-rightYBrowser, step),
      lt: clamp(Math.round(trigger(buttons[6]) * 100), 0, 100),
      rt: clamp(Math.round(trigger(buttons[7]) * 100), 0, 100),
      heldMask,
      tapMask
    };
  }

  function fingerprint(state) {
    return [state.lx, state.ly, state.rx, state.ry, state.lt, state.rt, state.heldMask].join("/");
  }

  function timingFor(platform, configuredCadence) {
    const defaults = PLATFORM_TIMINGS[platform] || { cadenceMs: 1000, keepaliveMs: 2500 };
    const cadenceMs = clamp(Number(configuredCadence || defaults.cadenceMs), 50, 10000);
    const keepaliveMs = clamp(Math.max(defaults.keepaliveMs, cadenceMs * 1.5), 750, 4000);
    const leaseMs = clamp(keepaliveMs + Math.max(500, Math.min(1000, cadenceMs * 2)), 750, 5000);
    return { cadenceMs, keepaliveMs, leaseMs };
  }

  class FrameEngine {
    constructor(options = {}) {
      this.session = options.session || Protocol.createSession();
      this.sequence = 0;
      this.pendingTapMask = 0;
      this.previousHeldMask = 0;
      this.current = { lx: 0, ly: 0, rx: 0, ry: 0, lt: 0, rt: 0, heldMask: 0, tapMask: 0 };
      this.lastSentFingerprint = NEUTRAL_FINGERPRINT;
      this.lastSentAt = -Infinity;
      this.dirty = false;
    }

    update(gamepad, settings = {}) {
      const sampled = sampleStandardGamepad(gamepad, settings, this.previousHeldMask);
      this.previousHeldMask = sampled.heldMask;
      this.pendingTapMask |= sampled.tapMask;
      this.current = sampled;
      const nextFingerprint = fingerprint(sampled);
      if (nextFingerprint !== this.lastSentFingerprint || this.pendingTapMask) this.dirty = true;
      return sampled;
    }

    neutral() {
      this.current = { lx: 0, ly: 0, rx: 0, ry: 0, lt: 0, rt: 0, heldMask: 0, tapMask: 0 };
      this.previousHeldMask = 0;
      this.pendingTapMask = 0;
      this.dirty = false;
    }

    packet(now, platform, configuredCadence) {
      const timing = timingFor(platform, configuredCadence);
      const elapsed = now - this.lastSentAt;
      const active = fingerprint(this.current) !== NEUTRAL_FINGERPRINT;
      // When controller is at neutral (centered sticks, released buttons),
      // send no commands. Streamer engine automatically expires leases to neutral.
      if (!active) return null;

      if (this.dirty) {
        if (elapsed < timing.cadenceMs) return null;
      } else {
        if (elapsed < timing.keepaliveMs) return null;
      }
      const frame = {
        session: this.session,
        sequence: this.sequence + 1,
        ...this.current,
        tapMask: this.pendingTapMask,
        leaseMs: timing.leaseMs
      };
      return platform === "tiktok"
        ? Protocol.encodeFriendlyFrame(frame)
        : Protocol.encodeFrame(frame);
    }

    markSent(now, packet) {
      const sent = packet ? Protocol.decodeFrame(packet) : { ...this.current, sequence: this.sequence + 1, tapMask: this.pendingTapMask };
      this.sequence = Math.max(this.sequence + 1, sent.sequence);
      this.lastSentAt = now;
      this.lastSentFingerprint = fingerprint(sent);
      // Preserve any new rising edges sampled while DOM injection was in flight.
      this.pendingTapMask &= ~sent.tapMask;
      this.dirty = fingerprint(this.current) !== this.lastSentFingerprint || Boolean(this.pendingTapMask);
    }
  }

  const api = Object.freeze({ BUTTON_INDEX, PLATFORM_CADENCE_MS, PLATFORM_TIMINGS, radialDeadzone, quantizePercent, sampleStandardGamepad, timingFor, FrameEngine });
  root.HMGamepad = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
