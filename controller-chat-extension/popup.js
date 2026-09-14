"use strict";

const DEFAULTS = { deadzone: 0.14, triggerDeadzone: 0.05, curve: 1, quantizeStep: 5, cadenceMs: 0 };
let previewArmed = false;
const previewApi = {
  tabs: {
    query: async () => [{ id: 1 }],
    sendMessage: async (_id, message) => {
      if (message.type === "HM_SET_ARMED") previewArmed = Boolean(message.armed);
      return {
        ok: true, platform: "twitch", armed: previewArmed, visible: true,
        gamepad: { id: "Xbox Wireless Controller", index: 0, mapping: "standard" },
        packet: previewArmed ? "hm1 mfr5z7k0 1 0,80,35,0,100,100 40 1 1470" : "",
        lastError: "", lastSentAt: 0
      };
    }
  },
  storage: {
    sync: {
      get: (defaults, callback) => callback(defaults),
      set: async () => {}
    }
  }
};
const extensionApi = globalThis.chrome?.storage?.sync && globalThis.chrome?.tabs
  ? globalThis.chrome
  : previewApi;
const elements = Object.fromEntries([
  "platform", "controller", "relay", "arm", "message", "packet",
  "deadzone", "deadzoneValue", "curve", "quantizeStep", "cadenceMs"
].map((id) => [id, document.getElementById(id)]));
let currentTab = null;
let armed = false;

function setMessage(text, error = false) {
  elements.message.textContent = text;
  elements.message.classList.toggle("error", error);
}

function setStatus(element, text, state = "") {
  element.textContent = text;
  element.className = state;
}

function render(status) {
  if (!status?.ok) {
    setStatus(elements.platform, "Unsupported page", "bad");
    setStatus(elements.controller, "Unavailable", "bad");
    setStatus(elements.relay, "Disarmed", "warn");
    armed = false;
    return;
  }
  armed = Boolean(status.armed);
  setStatus(elements.platform, String(status.platform || "unknown").toUpperCase(), status.platform === "unsupported" ? "bad" : "good");
  setStatus(elements.controller, status.gamepad?.id || "Press any button", status.gamepad ? "good" : "warn");
  setStatus(elements.relay, armed ? "Armed" : "Disarmed", armed ? "good" : "warn");
  elements.arm.textContent = armed ? "DISARM AND SEND NEUTRAL" : "ARM CONTROLLER CHAT";
  elements.arm.classList.toggle("armed", armed);
  elements.packet.textContent = status.packet || "No frame sent yet";
  if (status.lastError) setMessage(status.lastError, true);
  else if (armed) setMessage("Controller activity is being compressed into chat-safe full-state frames.");
}

async function sendToTop(message) {
  if (!currentTab?.id) return { ok: false, error: "No active tab" };
  try { return await extensionApi.tabs.sendMessage(currentTab.id, message, { frameId: 0 }); }
  catch (_) { return { ok: false, error: "Reload this supported stream page after installing the extension" }; }
}

async function refresh() {
  [currentTab] = await extensionApi.tabs.query({ active: true, currentWindow: true });
  render(await sendToTop({ type: "HM_GET_STATUS" }));
}

elements.arm.addEventListener("click", async () => {
  const result = await sendToTop({ type: "HM_SET_ARMED", armed: !armed });
  if (!result?.ok) setMessage(result?.error || "Could not change relay state", true);
  render(result);
});

async function saveSettings() {
  const values = {
    deadzone: Number(elements.deadzone.value) / 100,
    curve: Number(elements.curve.value),
    quantizeStep: Number(elements.quantizeStep.value),
    cadenceMs: Number(elements.cadenceMs.value)
  };
  elements.deadzoneValue.textContent = elements.deadzone.value;
  await extensionApi.storage.sync.set(values);
}

for (const key of ["deadzone", "curve", "quantizeStep", "cadenceMs"]) {
  elements[key].addEventListener("input", saveSettings);
  elements[key].addEventListener("change", saveSettings);
}

extensionApi.storage.sync.get(DEFAULTS, (values) => {
  elements.deadzone.value = Math.round(Number(values.deadzone) * 100);
  elements.deadzoneValue.textContent = elements.deadzone.value;
  elements.curve.value = String(values.curve);
  elements.quantizeStep.value = String(values.quantizeStep);
  elements.cadenceMs.value = String(values.cadenceMs);
});

refresh();
