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
    assert.equal(await popup.evaluate(() => chrome.runtime.getManifest().version), "1.2.0");
    await popup.getByRole("heading", { name: "Controller Chat" }).waitFor();
    await popup.screenshot({ path: screenshotPath });
    assert.equal(await popup.locator("body").evaluate((body) => getComputedStyle(body).backgroundColor), "rgb(22, 24, 29)");

    const chat = await context.newPage();
    await chat.route("https://www.twitch.tv/hm-extension-test", async (route) => {
      await route.fulfill({
        contentType: "text/html",
        body: `<!doctype html><html><body style="background:#16181D">
          <div data-a-target="chat-input" contenteditable="true" style="width:400px;height:50px"></div>
          <button data-a-target="chat-send-button" onclick="const input=document.querySelector('[contenteditable]');document.querySelector('#sent').textContent=input.textContent;input.textContent=''">Send</button>
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
          </div>
          <output id="sent"></output>
          <script>
            document.querySelector('[contenteditable]').addEventListener('input', () => {
              if (document.querySelector('[data-e2e="room-chat-send-btn"]')) return;
              setTimeout(() => {
                const button = document.createElement('div');
                button.dataset.e2e = 'room-chat-send-btn';
                button.setAttribute('role', 'button');
                button.style.cssText = 'width:40px;height:30px';
                button.textContent = 'Send';
                button.onclick = () => {
                  const input = document.querySelector('[contenteditable]');
                  document.querySelector('#sent').textContent = input.textContent;
                  input.textContent = '';
                };
                document.querySelector('[data-e2e="live-chat-input-container"]').appendChild(button);
              }, 180);
            });
          </script>
        </body></html>`
      });
    });
    await tiktok.goto("https://www.tiktok.com/@hm-extension-test/live");
    await tiktok.waitForTimeout(300);
    await tiktok.bringToFront();
    const attachmentStatus = await popup.evaluate(async () => {
      await refresh();
      const attached = await attachContentRuntime();
      const status = await sendToTop({ type: "HM_GET_STATUS" });
      return { attached, status };
    });
    assert.equal(attachmentStatus.attached, true);
    assert.equal(attachmentStatus.status.ok, true);
    assert.equal(attachmentStatus.status.version, "1.2.0");
    const friendlyPacket = "pad mfr5z7k0 q1 e14u w80 lr35 lt100 rt100 h40 t1";
    const tiktokInjection = await popup.evaluate(async ({ packet }) => {
      const [tab] = await chrome.tabs.query({ url: "https://www.tiktok.com/@hm-extension-test/live" });
      return chrome.tabs.sendMessage(tab.id, { type: "HM_INJECT_PACKET", packet, platform: "tiktok" }, { frameId: 0 });
    }, { packet: friendlyPacket });
    assert.equal(tiktokInjection.ok, true);
    assert.equal(await tiktok.locator("#sent").textContent(), friendlyPacket);
    assert.equal(await tiktok.locator("[contenteditable]").textContent(), "");

    const rejected = await context.newPage();
    await rejected.route("https://www.tiktok.com/@hm-extension-reject/live", async (route) => {
      await route.fulfill({
        contentType: "text/html",
        body: `<!doctype html><html><body>
          <div data-e2e="room-chat-input-field" contenteditable="plaintext-only" style="width:400px;height:50px"></div>
          <div data-e2e="room-chat-send-btn" role="button" style="width:40px;height:30px">Send</div>
        </body></html>`
      });
    });
    await rejected.goto("https://www.tiktok.com/@hm-extension-reject/live");
    await rejected.waitForTimeout(300);
    const rejectedInjection = await popup.evaluate(async ({ packet }) => {
      const [tab] = await chrome.tabs.query({ url: "https://www.tiktok.com/@hm-extension-reject/live" });
      return chrome.tabs.sendMessage(tab.id, { type: "HM_INJECT_PACKET", packet, platform: "tiktok" }, { frameId: 0 });
    }, { packet: friendlyPacket });
    assert.equal(rejectedInjection.ok, false);
    assert.match(rejectedInjection.error, /did not accept/);
    assert.equal(await rejected.locator("[contenteditable]").textContent(), "");

    assert.deepEqual(manifestErrors, []);
    console.log(JSON.stringify({ extensionId, screenshotPath, twitchInjected: true, tiktokDelayedSend: true, failedSendRecovered: true }));
  } finally {
    await context.close();
    fs.rmSync(profilePath, { recursive: true, force: true });
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
