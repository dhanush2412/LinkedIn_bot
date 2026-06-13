// Service worker: opens the side panel and stashes the latest tailored result
// so sidepanel.js can render it.
chrome.runtime.onMessage.addListener((msg, sender) => {
  if (msg.type === "openSidePanel") {
    chrome.storage.local.set({ lastTailored: msg.payload });
    if (sender.tab) {
      chrome.sidePanel.open({ tabId: sender.tab.id }).catch(() => {});
    }
  }
});
