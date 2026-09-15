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
    const lease = clampInteger(frame.leaseMs, 50, 5000);
    const packet = `hm1 ${session} ${sequence} ${analog} ${held} ${taps} ${lease}`;
    if (packet.length > 160) throw new Error("controller frame exceeded protocol limit");
    return packet;
  }

  function encodeFriendlyFrame(frame) {
    const tokens = [
      "pad",
      Math.max(0, Math.floor(frame.session)).toString(36),
      `q${Math.max(0, Math.floor(frame.sequence)).toString(36)}`,
      `e${clampInteger(frame.leaseMs, 50, 5000).toString(36)}`
    ];
    const directional = [
      [frame.ly, "w", "s"], [frame.lx, "d", "a"],
      [frame.rx, "lr", "ll"], [frame.ry, "lu", "ld"]
    ];
    for (const [value, positive, negative] of directional) {
      const amount = clampInteger(Math.abs(value), 0, 100);
      if (amount) tokens.push(`${Number(value) > 0 ? positive : negative}${amount}`);
    }
    const lt = clampInteger(frame.lt, 0, 100);
    const rt = clampInteger(frame.rt, 0, 100);
    if (lt) tokens.push(`lt${lt}`);
    if (rt) tokens.push(`rt${rt}`);
    const held = clampInteger(frame.heldMask, 0, VALID_MASK) & VALID_MASK;
    const taps = clampInteger(frame.tapMask, 0, VALID_MASK) & VALID_MASK;
    if (held) tokens.push(`h${held.toString(16)}`);
    if (taps) tokens.push(`t${taps.toString(16)}`);
    const packet = tokens.join(" ");
    if (packet.length > 150) throw new Error("friendly controller frame exceeded TikTok limit");
    return packet;
  }

  function decodeFrame(packet) {
    const parts = String(packet).trim().replace(/^!/, "").split(/\s+/);
    if (parts[0] === "pad") return decodeFriendlyFrame(parts);
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

  function decodeFriendlyFrame(parts) {
    if (parts.length < 4 || !/^q[0-9a-z]+$/.test(parts[2]) || !/^e[0-9a-z]+$/.test(parts[3])) {
      throw new Error("invalid friendly controller frame");
    }
    const result = {
      session: parseInt(parts[1], 36), sequence: parseInt(parts[2].slice(1), 36),
      lx: 0, ly: 0, rx: 0, ry: 0, lt: 0, rt: 0,
      heldMask: 0, tapMask: 0, leaseMs: parseInt(parts[3].slice(1), 36)
    };
    const directions = { w: ["ly", 1], s: ["ly", -1], a: ["lx", -1], d: ["lx", 1], ll: ["rx", -1], lr: ["rx", 1], lu: ["ry", 1], ld: ["ry", -1] };
    for (const token of parts.slice(4)) {
      const match = token.match(/^(ll|lr|lu|ld|lt|rt|w|s|a|d)(\d{1,3})$/);
      if (match) {
        const [, prefix, amount] = match;
        if (prefix === "lt" || prefix === "rt") result[prefix] = Number(amount);
        else { const [control, sign] = directions[prefix]; result[control] = Number(amount) * sign; }
      } else if (/^h[0-9a-f]{1,4}$/.test(token)) result.heldMask = parseInt(token.slice(1), 16);
      else if (/^t[0-9a-f]{1,4}$/.test(token)) result.tapMask = parseInt(token.slice(1), 16);
      else throw new Error("invalid friendly controller token");
    }
    return result;
  }

  const api = Object.freeze({ BUTTONS, VALID_MASK, createSession, encodeFrame, encodeFriendlyFrame, decodeFrame });
  root.HMProtocol = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
