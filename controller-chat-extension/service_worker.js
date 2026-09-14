"use strict";

function triggerTikTokSend() {
  const send = document.querySelector("[data-e2e='room-chat-send-btn']");
  if (!send) return { ok: false, error: "TikTok send control disappeared" };

  // TikTok currently ignores an isolated-world element.click(). Calling the page's
  // own React handler in MAIN world follows the same submit path as its visible control.
  const reactPropsKey = Object.keys(send).find((key) => key.startsWith("__reactProps$"));
  const onClick = reactPropsKey && send[reactPropsKey]?.onClick;
  if (typeof onClick === "function") {
    try {
      onClick({
        type: "click",
        target: send,
        currentTarget: send,
        nativeEvent: {},
        preventDefault() {},
        stopPropagation() {}
      });
      return { ok: true, method: "react" };
    } catch (error) {
      return { ok: false, error: `TikTok submit handler failed: ${String(error)}` };
    }
  }

  send.click();
  return { ok: true, method: "dom" };
}

async function submitTikTok(tabId, frameId) {
  const results = await chrome.scripting.executeScript({
    target: { tabId, frameIds: [frameId] },
    world: "MAIN",
    func: triggerTikTokSend
  });
  return results?.[0]?.result || { ok: false, error: "TikTok submit did not run" };
}

async function sendToFrame(tabId, frameId, packet, platform) {
  try {
    return await chrome.tabs.sendMessage(tabId, {
      type: "HM_INJECT_PACKET", packet, platform
    }, { frameId });
  } catch (_) {
    return null;
  }
}

async function routePacket(tabId, packet, platform) {
  const frames = await chrome.webNavigation.getAllFrames({ tabId });
  if (!frames) return { ok: false, error: "No chat frame is available" };
  const errors = [];
  const ordered = [...frames].sort((a, b) => {
    if (platform === "youtube") return Number(b.frameId !== 0) - Number(a.frameId !== 0);
    return Number(a.frameId !== 0) - Number(b.frameId !== 0);
  });
  for (const frame of ordered) {
    const result = await sendToFrame(tabId, frame.frameId, packet, platform);
    if (result?.ok) return result;
    if (result?.error) errors.push(result.error);
    if (result?.handled) return result;
  }
  return {
    ok: false,
    error: errors.find((error) => !error.includes("not found"))
      || errors[0]
      || "Live chat composer was not found or already contains text"
  };
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "HM_TIKTOK_SUBMIT" && sender.tab?.id) {
    let isTikTok = false;
    try {
      const host = new URL(sender.url || sender.tab.url || "").hostname.toLowerCase();
      isTikTok = host === "tiktok.com" || host.endsWith(".tiktok.com");
    } catch (_) {}
    if (!isTikTok) {
      sendResponse({ ok: false, error: "TikTok submit was requested from an unsupported page" });
      return false;
    }
    submitTikTok(sender.tab.id, sender.frameId ?? 0)
      .then(sendResponse)
      .catch((error) => sendResponse({ ok: false, error: String(error?.message || error) }));
    return true;
  }
  if (message?.type !== "HM_ROUTE_PACKET" || !sender.tab?.id) return false;
  routePacket(sender.tab.id, String(message.packet || ""), String(message.platform || ""))
    .then(sendResponse)
    .catch((error) => sendResponse({ ok: false, error: String(error?.message || error) }));
  return true;
});
