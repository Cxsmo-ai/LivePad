"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const Protocol = require("../shared/protocol.js");
const Gamepad = require("../shared/gamepad_engine.js");

function button(value = 0) { return { value, pressed: value >= 0.5 }; }
function fakePad({ axes = [0, 0, 0, 0], buttons = [] } = {}) {
  return { connected: true, mapping: "standard", axes, buttons: Array.from({ length: 17 }, (_, i) => buttons[i] || button()) };
}

test("browser up becomes positive protocol forward", () => {
  const state = Gamepad.sampleStandardGamepad(fakePad({ axes: [0, -1, 0.4, -0.5] }), { deadzone: 0, quantizeStep: 1 });
  assert.equal(state.ly, 100);
  assert.equal(state.rx, 40);
  assert.equal(state.ry, 50);
});

test("radial deadzone preserves direction and eliminates drift", () => {
  assert.deepEqual(Gamepad.radialDeadzone(0.05, -0.05, 0.14), [0, 0]);
  const [x, y] = Gamepad.radialDeadzone(0.8, 0.8, 0.14);
  assert.ok(Math.hypot(x, y) <= 1.000001);
  assert.ok(Math.abs(x - y) < 1e-9);
});

test("all standard digital buttons map to stable held and rising-edge masks", () => {
  const buttons = [];
  buttons[0] = button(1);
  buttons[2] = button(1);
  buttons[10] = button(1);
  const first = Gamepad.sampleStandardGamepad(fakePad({ buttons }), {}, 0);
  assert.equal(first.heldMask, Protocol.BUTTONS.a | Protocol.BUTTONS.x | Protocol.BUTTONS.l3);
  assert.equal(first.tapMask, first.heldMask);
  const held = Gamepad.sampleStandardGamepad(fakePad({ buttons }), {}, first.heldMask);
  assert.equal(held.tapMask, 0);
});

test("triggers stay analog and are not mistaken for buttons", () => {
  const buttons = [];
  buttons[6] = button(0.525);
  buttons[7] = button(1);
  const state = Gamepad.sampleStandardGamepad(fakePad({ buttons }), { triggerDeadzone: 0.05 });
  assert.equal(state.lt, 50);
  assert.equal(state.rt, 100);
  assert.equal(state.heldMask, 0);
});

test("frame engine coalesces changes and carries missed taps", () => {
  const engine = new Gamepad.FrameEngine({ session: 123 });
  const buttons = [];
  buttons[0] = button(1);
  engine.update(fakePad({ axes: [0, -0.8, 0.35, 0], buttons }), { deadzone: 0, quantizeStep: 1 });
  buttons[0] = button(0);
  engine.update(fakePad({ axes: [0, -0.8, 0.35, 0], buttons }), { deadzone: 0, quantizeStep: 1 });
  const packet = engine.packet(0, "twitch");
  const decoded = Protocol.decodeFrame(packet);
  assert.equal(decoded.ly, 80);
  assert.equal(decoded.rx, 35);
  assert.equal(decoded.heldMask, 0);
  assert.equal(decoded.tapMask, Protocol.BUTTONS.a);
  assert.ok(packet.length < 80);
});

test("platform cadence is enforced and keepalive is a full snapshot", () => {
  const engine = new Gamepad.FrameEngine({ session: 456 });
  engine.update(fakePad({ axes: [0, -1, 0, 0] }), { deadzone: 0 });
  const first = engine.packet(0, "twitch");
  assert.ok(first);
  engine.markSent(0, first);
  assert.equal(engine.packet(1000, "twitch"), null);
  assert.ok(engine.packet(2100, "twitch"));
});

test("an input edge sampled during DOM send is not lost", () => {
  const engine = new Gamepad.FrameEngine({ session: 789 });
  engine.update(fakePad({ axes: [0, -1, 0, 0] }), { deadzone: 0 });
  const inFlight = engine.packet(0, "twitch");
  const buttons = [];
  buttons[0] = button(1);
  engine.update(fakePad({ axes: [0, -1, 0, 0], buttons }), { deadzone: 0 });
  engine.markSent(0, inFlight);
  assert.equal(engine.pendingTapMask, Protocol.BUTTONS.a);
  assert.equal(engine.dirty, true);
  const next = Protocol.decodeFrame(engine.packet(1050, "twitch"));
  assert.equal(next.tapMask, Protocol.BUTTONS.a);
  assert.equal(next.heldMask, Protocol.BUTTONS.a);
});
