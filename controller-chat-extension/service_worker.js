"use strict";

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
  const ordered = [...frames].sort((a, b) => {
    if (platform === "youtube") return Number(b.frameId !== 0) - Number(a.frameId !== 0);
    return Number(a.frameId !== 0) - Number(b.frameId !== 0);
  });
  for (const frame of ordered) {
    const result = await sendToFrame(tabId, frame.frameId, packet, platform);
    if (result?.ok) return result;
  }
  return { ok: false, error: "Live chat composer was not found or already contains text" };
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type !== "HM_ROUTE_PACKET" || !sender.tab?.id) return false;
  routePacket(sender.tab.id, String(message.packet || ""), String(message.platform || ""))
    .then(sendResponse)
    .catch((error) => sendResponse({ ok: false, error: String(error?.message || error) }));
  return true;
});
