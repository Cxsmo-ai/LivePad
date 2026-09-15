"use strict";

// The chat composer normally lives in the same frame for the life of a LIVE
// page. Avoid asking webNavigation for every controller frame; keep the last
// successful frame and fall back to discovery only after it disappears or
// rejects the packet.
const routeFrameCache = new Map();
const framePorts = new Map();
let frameRequestSequence = 0;
const pendingFrameRequests = new Map();

function frameCacheKey(tabId, platform) {
  return `${tabId}:${platform}`;
}

function rememberRouteFrame(tabId, platform, frameId) {
  routeFrameCache.set(frameCacheKey(tabId, platform), { frameId, lastUsed: Date.now() });
}

function forgetRouteFrame(tabId, platform) {
  routeFrameCache.delete(frameCacheKey(tabId, platform));
}

function framePortKey(tabId, frameId) {
  return `${tabId}:${frameId}`;
}

chrome.tabs.onRemoved?.addListener((tabId) => {
  for (const key of routeFrameCache.keys()) {
    if (key.startsWith(`${tabId}:`)) routeFrameCache.delete(key);
  }
  for (const key of framePorts.keys()) {
    if (key.startsWith(`${tabId}:`)) framePorts.delete(key);
  }
});

function triggerTikTokSend() {
  const selectors = [
    "[data-e2e='room-chat-send-btn']",
    "[data-e2e='comment-post']",
    "[data-e2e='comment-send']"
  ];
  const send = selectors
    .flatMap((selector) => Array.from(document.querySelectorAll(selector)))
    .find((candidate) => {
      if (!candidate || candidate.disabled || candidate.getAttribute("aria-disabled") === "true") {
        return false;
      }
      const style = window.getComputedStyle(candidate);
      const rect = candidate.getBoundingClientRect();
      return style.display !== "none" && style.visibility !== "hidden" &&
        rect.width > 0 && rect.height > 0;
    });
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
  const port = framePorts.get(framePortKey(tabId, frameId));
  if (port) {
    const requestId = `${Date.now().toString(36)}-${(++frameRequestSequence).toString(36)}`;
    const result = await new Promise((resolve) => {
      const timeout = setTimeout(() => {
        pendingFrameRequests.delete(requestId);
        resolve(null);
      }, 1500);
        pendingFrameRequests.set(requestId, { resolve, timeout, port });
      try {
        port.postMessage({ type: "HM_INJECT_PACKET", requestId, packet, platform });
      } catch (_) {
        clearTimeout(timeout);
        pendingFrameRequests.delete(requestId);
        resolve(null);
      }
    });
    if (result) return result;
  }
  try {
    return await chrome.tabs.sendMessage(tabId, {
      type: "HM_INJECT_PACKET", packet, platform
    }, { frameId });
  } catch (_) {
    return null;
  }
}

async function routePacket(tabId, packet, platform) {
  const cached = routeFrameCache.get(frameCacheKey(tabId, platform));
  if (cached) {
    const cachedResult = await sendToFrame(tabId, cached.frameId, packet, platform);
    if (cachedResult?.ok) {
      cached.lastUsed = Date.now();
      return cachedResult;
    }
    if (cachedResult?.handled) return cachedResult;
    forgetRouteFrame(tabId, platform);
  }

  const frames = await chrome.webNavigation.getAllFrames({ tabId });
  if (!frames?.length) return { ok: false, error: "No chat frame is available" };
  const errors = [];
  const ordered = [...frames].sort((a, b) => {
    if (platform === "youtube") return Number(b.frameId !== 0) - Number(a.frameId !== 0);
    return Number(a.frameId !== 0) - Number(b.frameId !== 0);
  });
  for (const frame of ordered) {
    const result = await sendToFrame(tabId, frame.frameId, packet, platform);
    if (result?.ok) {
      rememberRouteFrame(tabId, platform, frame.frameId);
      return result;
    }
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

// High-rate controller frames use one reusable Port instead of creating a new
// runtime message channel for every frame. Popup/status traffic continues to
// use the one-shot listener below.
chrome.runtime.onConnect.addListener((port) => {
  if (port.name === "hm-frame") {
    const tabId = port.sender?.tab?.id;
    const frameId = port.sender?.frameId ?? 0;
    if (tabId === undefined) return;
    const key = framePortKey(tabId, frameId);
    const previous = framePorts.get(key);
    previous?.disconnect();
    framePorts.set(key, port);
    port.onMessage.addListener((message) => {
      if (message?.type !== "HM_INJECT_RESULT") return;
      const pending = pendingFrameRequests.get(message.requestId);
      if (!pending) return;
      clearTimeout(pending.timeout);
      pendingFrameRequests.delete(message.requestId);
      pending.resolve(message.result);
    });
    port.onDisconnect.addListener(() => {
      if (framePorts.get(key) === port) framePorts.delete(key);
      for (const [requestId, pending] of pendingFrameRequests) {
        if (pending.port !== port) continue;
        clearTimeout(pending.timeout);
        pendingFrameRequests.delete(requestId);
        pending.resolve(null);
      }
    });
    return;
  }
  if (port.name !== "hm-route") return;
  port.onMessage.addListener((message) => {
    if (message?.type !== "HM_ROUTE_PACKET" || !port.sender?.tab?.id) return;
    routePacket(
      port.sender.tab.id,
      String(message.packet || ""),
      String(message.platform || "")
    ).then((result) => {
      port.postMessage({ type: "HM_ROUTE_RESULT", requestId: message.requestId, result });
    }).catch((error) => {
      port.postMessage({
        type: "HM_ROUTE_RESULT",
        requestId: message.requestId,
        result: { ok: false, error: String(error?.message || error) }
      });
    });
  });
});

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
