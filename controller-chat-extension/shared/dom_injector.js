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

  function sleep(milliseconds) {
    return new Promise((resolve) => setTimeout(resolve, milliseconds));
  }

  async function waitFor(check, timeoutMs, intervalMs = 25) {
    const deadline = performance.now() + timeoutMs;
    while (performance.now() < deadline) {
      const result = check();
      if (result) return result;
      await sleep(intervalMs);
    }
    return check();
  }

  function clearOwnedPacket(element, packet) {
    if (!element?.isConnected || composerValue(element) !== packet) return false;
    element.focus();
    if (element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement) {
      const prototype = element instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      const setter = Object.getOwnPropertyDescriptor(prototype, "value")?.set;
      if (setter) setter.call(element, ""); else element.value = "";
    } else {
      element.textContent = "";
    }
    element.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "deleteContentBackward", data: null }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
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

  async function injectPacket(packet, platform, submit) {
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

    const send = await waitFor(() => {
      if (!input.isConnected || composerValue(input) !== packet) return null;
      return firstVisible(set.sends);
    }, platform === "tiktok" ? 1500 : 750);

    if (!send) {
      const changed = input.isConnected && composerValue(input) !== packet;
      if (!changed) clearOwnedPacket(input, packet);
      return {
        ok: false,
        handled: true,
        error: changed
          ? "Composer changed before the controller frame could send"
          : "Chat send control did not become ready"
      };
    }

    // Do not submit if the viewer typed while the site's asynchronous send control rendered.
    if (composerValue(input) !== packet) {
      return { ok: false, handled: true, error: "Composer changed before the controller frame could send" };
    }

    let submitResult = { ok: true };
    if (typeof submit === "function") submitResult = await submit();
    else send.click();
    if (submitResult?.ok === false) {
      clearOwnedPacket(input, packet);
      return { ok: false, handled: true, error: submitResult.error || "Chat send action failed" };
    }
    const submitted = await waitFor(() => {
      if (!input.isConnected) return true;
      return composerValue(input) !== packet;
    }, platform === "tiktok" ? 1500 : 750);

    if (!submitted) {
      clearOwnedPacket(input, packet);
      return { ok: false, handled: true, error: "Chat did not accept the controller frame" };
    }

    const remaining = input.isConnected ? composerValue(input) : "";
    if (remaining) {
      return { ok: false, handled: true, error: "Composer changed while the controller frame was sending" };
    }
    return { ok: true, handled: true, frameUrl: location.href };
  }

  const api = Object.freeze({ clearOwnedPacket, composerValue, injectPacket, selectors, waitFor });
  root.HMInjector = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
