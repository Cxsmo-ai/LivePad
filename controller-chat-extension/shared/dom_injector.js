(function (root) {
  "use strict";

  function visible(element) {
    if (!element || element.disabled) return false;
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
  }

  function firstVisible(selectors) {
    for (const selector of selectors) {
      for (const element of document.querySelectorAll(selector)) if (visible(element)) return element;
    }
    return null;
  }

  function composerValue(element) {
    if ("value" in element) return String(element.value || "").trim();
    return String(element.textContent || "").trim();
  }

  function writeComposer(element, value) {
    element.focus();
    if (element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement) {
      const prototype = element instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      const setter = Object.getOwnPropertyDescriptor(prototype, "value")?.set;
      if (setter) setter.call(element, value); else element.value = value;
    } else {
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(element);
      selection.removeAllRanges();
      selection.addRange(range);
      if (!document.execCommand("insertText", false, value)) element.textContent = value;
    }
    element.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: value }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function selectors(platform) {
    if (platform === "twitch") return {
      inputs: ["[data-a-target='chat-input']"],
      sends: ["[data-a-target='chat-send-button']"]
    };
    if (platform === "youtube") return {
      inputs: ["yt-live-chat-text-input-field-renderer #input[contenteditable='true']", "#input[contenteditable='true']"],
      sends: ["#send-button button", "#send-button"]
    };
    if (platform === "tiktok") return {
      inputs: [
        "[data-e2e='room-chat-input-field'][contenteditable]",
        "[data-e2e='comment-input'] [contenteditable]",
        "[data-e2e='comment-input'][contenteditable]",
        "textarea[data-e2e='comment-input']"
      ],
      sends: [
        "[data-e2e='room-chat-send-btn']",
        "[data-e2e='comment-post']",
        "[data-e2e='comment-send']"
      ]
    };
    return { inputs: [], sends: [] };
  }

  async function injectPacket(packet, platform) {
    const compact = /^!?hm1 [0-9a-z]+ [0-9a-z]+ -?\d+,-?\d+,-?\d+,-?\d+,\d+,\d+ [0-9a-f]+ [0-9a-f]+ \d+$/;
    const friendly = /^!?pad [0-9a-z]+ q[0-9a-z]+ e[0-9a-z]+(?: (?:ll|lr|lu|ld|lt|rt|w|s|a|d)\d{1,3})*(?: h[0-9a-f]{1,4})?(?: t[0-9a-f]{1,4})?$/;
    if (!compact.test(packet) && !friendly.test(packet)) {
      return { ok: false, error: "Invalid controller packet" };
    }
    const set = selectors(platform);
    const input = firstVisible(set.inputs);
    if (!input) return { ok: false, error: "Composer not found in this frame" };
    if (composerValue(input)) return { ok: false, error: "Composer contains your text; controller send paused" };
    writeComposer(input, packet);
    await new Promise((resolve) => setTimeout(resolve, 60));
    const send = firstVisible(set.sends);
    if (send) send.click();
    else input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", code: "Enter", bubbles: true, cancelable: true }));
    return { ok: true, frameUrl: location.href };
  }

  const api = Object.freeze({ composerValue, injectPacket, selectors });
  root.HMInjector = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
