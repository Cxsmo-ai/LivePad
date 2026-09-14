(function (root) {
  "use strict";

  const BUTTONS = Object.freeze({
    a: 0x0001, b: 0x0002, x: 0x0004, y: 0x0008,
    lb: 0x0010, rb: 0x0020, l3: 0x0040, r3: 0x0080,
    back: 0x0100, start: 0x0200, guide: 0x0400,
    dpad_up: 0x0800, dpad_down: 0x1000,
    dpad_left: 0x2000, dpad_right: 0x4000
  });
  const VALID_MASK = 0x7fff;
  let lastSession = 0;

  function clampInteger(value, minimum, maximum) {
    const number = Math.round(Number(value) || 0);
    return Math.max(minimum, Math.min(maximum, number));
  }

  function createSession(now = Date.now()) {
    const candidate = Math.max(Math.floor(now), lastSession + 1);
    lastSession = candidate;
    return candidate;
  }

  function encodeFrame(frame) {
    const session = Math.max(0, Math.floor(frame.session)).toString(36);
    const sequence = Math.max(0, Math.floor(frame.sequence)).toString(36);
    const analog = [
      clampInteger(frame.lx, -100, 100), clampInteger(frame.ly, -100, 100),
      clampInteger(frame.rx, -100, 100), clampInteger(frame.ry, -100, 100),
      clampInteger(frame.lt, 0, 100), clampInteger(frame.rt, 0, 100)
    ].join(",");
    const held = (clampInteger(frame.heldMask, 0, VALID_MASK) & VALID_MASK).toString(16);
    const taps = (clampInteger(frame.tapMask, 0, VALID_MASK) & VALID_MASK).toString(16);
    const lease = clampInteger(frame.leaseMs, 250, 5000);
    const packet = `hm1 ${session} ${sequence} ${analog} ${held} ${taps} ${lease}`;
    if (packet.length > 160) throw new Error("controller frame exceeded protocol limit");
    return packet;
  }

  function decodeFrame(packet) {
    const parts = String(packet).trim().replace(/^!/, "").split(/\s+/);
    if (parts.length !== 7 || parts[0] !== "hm1") throw new Error("invalid controller frame");
    const values = parts[3].split(",").map(Number);
    if (values.length !== 6 || values.some((value) => !Number.isInteger(value))) {
      throw new Error("invalid analog values");
    }
    return {
      session: parseInt(parts[1], 36), sequence: parseInt(parts[2], 36),
      lx: values[0], ly: values[1], rx: values[2], ry: values[3],
      lt: values[4], rt: values[5],
      heldMask: parseInt(parts[4], 16), tapMask: parseInt(parts[5], 16),
      leaseMs: Number(parts[6])
    };
  }

  const api = Object.freeze({ BUTTONS, VALID_MASK, createSession, encodeFrame, decodeFrame });
  root.HMProtocol = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
