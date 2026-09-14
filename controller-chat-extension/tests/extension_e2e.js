"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { chromium } = require("playwright");

async function main() {
  const extensionPath = path.resolve(__dirname, "..");
  const profilePath = fs.mkdtempSync(path.join(os.tmpdir(), "hm-controller-chat-"));
  const screenshotPath = path.join(os.tmpdir(), "hm-controller-chat-popup.png");
  const context = await chromium.launchPersistentContext(profilePath, {
    channel: "chromium",
    headless: true,
    args: [
      `--disable-extensions-except=${extensionPath}`,
      `--load-extension=${extensionPath}`
    ]
  });
  try {
    let workers = context.serviceWorkers();
    if (!workers.length) workers = [await context.waitForEvent("serviceworker")];
    const extensionId = new URL(workers[0].url()).host;
    assert.match(extensionId, /^[a-p]{32}$/);

    const popup = await context.newPage();
    const manifestErrors = [];
    popup.on("console", (message) => { if (message.type() === "error") manifestErrors.push(message.text()); });
    await popup.setViewportSize({ width: 370, height: 650 });
    await popup.goto(`chrome-extension://${extensionId}/popup.html`);
    await popup.getByRole("heading", { name: "Controller Chat" }).waitFor();
    await popup.screenshot({ path: screenshotPath });
    assert.equal(await popup.locator("body").evaluate((body) => getComputedStyle(body).backgroundColor), "rgb(22, 24, 29)");

    const chat = await context.newPage();
    await chat.route("https://www.twitch.tv/hm-extension-test", async (route) => {
      await route.fulfill({
        contentType: "text/html",
        body: `<!doctype html><html><body style="background:#16181D">
          <div data-a-target="chat-input" contenteditable="true" style="width:400px;height:50px"></div>
          <button data-a-target="chat-send-button" onclick="document.querySelector('#sent').textContent=document.querySelector('[contenteditable]').textContent">Send</button>
          <output id="sent"></output>
        </body></html>`
      });
    });
    await chat.goto("https://www.twitch.tv/hm-extension-test");
    await chat.waitForTimeout(300);
    const packet = "hm1 mfr5z7k0 1 0,80,35,0,100,100 40 1 1470";
    const injection = await popup.evaluate(async ({ packet }) => {
      const [tab] = await chrome.tabs.query({ url: "https://www.twitch.tv/hm-extension-test" });
      return chrome.tabs.sendMessage(tab.id, { type: "HM_INJECT_PACKET", packet, platform: "twitch" }, { frameId: 0 });
    }, { packet });
    assert.equal(injection.ok, true);
    assert.equal(await chat.locator("#sent").textContent(), packet);

    const tiktok = await context.newPage();
    await tiktok.route("https://www.tiktok.com/@hm-extension-test/live", async (route) => {
      await route.fulfill({
        contentType: "text/html",
        body: `<!doctype html><html><body style="background:#16181D">
          <div data-e2e="live-chat-input-container">
            <div data-e2e="room-chat-input-field" contenteditable="plaintext-only" style="width:400px;height:50px"></div>
            <div data-e2e="room-chat-send-btn" role="button" style="width:40px;height:30px" onclick="document.querySelector('#sent').textContent=document.querySelector('[contenteditable]').textContent">Send</div>
          </div>
          <output id="sent"></output>
        </body></html>`
      });
    });
    await tiktok.goto("https://www.tiktok.com/@hm-extension-test/live");
    await tiktok.waitForTimeout(300);
    const tiktokInjection = await popup.evaluate(async ({ packet }) => {
      const [tab] = await chrome.tabs.query({ url: "https://www.tiktok.com/@hm-extension-test/live" });
      return chrome.tabs.sendMessage(tab.id, { type: "HM_INJECT_PACKET", packet, platform: "tiktok" }, { frameId: 0 });
    }, { packet });
    assert.equal(tiktokInjection.ok, true);
    assert.equal(await tiktok.locator("#sent").textContent(), packet);

    assert.deepEqual(manifestErrors, []);
    console.log(JSON.stringify({ extensionId, screenshotPath, twitchInjected: true, tiktokInjected: true }));
  } finally {
    await context.close();
    fs.rmSync(profilePath, { recursive: true, force: true });
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
