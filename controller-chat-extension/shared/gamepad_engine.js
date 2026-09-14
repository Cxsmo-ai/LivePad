(function (root) {
  "use strict";

  const Protocol = root.HMProtocol || (typeof require === "function" ? require("./protocol.js") : null);
  const BUTTON_INDEX = Object.freeze({
    0: "a", 1: "b", 2: "x", 3: "y", 4: "lb", 5: "rb",
    8: "back", 9: "start", 10: "l3", 11: "r3",
    12: "dpad_up", 13: "dpad_down", 14: "dpad_left", 15: "dpad_right", 16: "guide"
  });
  const PLATFORM_CADENCE_MS = Object.freeze({ twitch: 1050, youtube: 2800, tiktok: 1200 });

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

  class FrameEngine {
    constructor(options = {}) {
      this.session = options.session || Protocol.createSession();
      this.sequence = 0;
      this.pendingTapMask = 0;
      this.previousHeldMask = 0;
      this.current = { lx: 0, ly: 0, rx: 0, ry: 0, lt: 0, rt: 0, heldMask: 0, tapMask: 0 };
      this.lastSentFingerprint = "";
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
      this.dirty = true;
    }

    packet(now, platform, configuredCadence) {
      const cadence = clamp(
        Number(configuredCadence || PLATFORM_CADENCE_MS[platform] || 1200), 1000, 10000
      );
      const keepaliveDue = now - this.lastSentAt >= Math.min(4500, cadence * 2);
      if (now - this.lastSentAt < cadence || (!this.dirty && !keepaliveDue)) return null;
      const leaseMs = clamp(Math.ceil(cadence * 1.4), 500, 5000);
      const frame = {
        session: this.session,
        sequence: this.sequence + 1,
        ...this.current,
        tapMask: this.pendingTapMask,
        leaseMs
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

  const api = Object.freeze({ BUTTON_INDEX, PLATFORM_CADENCE_MS, radialDeadzone, quantizePercent, sampleStandardGamepad, FrameEngine });
  root.HMGamepad = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
