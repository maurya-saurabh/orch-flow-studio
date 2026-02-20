/**
 * Node-RED canvas fix: Force flow to render without requiring manual click.
 * Addresses blank canvas / "click to show" issue (GitHub #2631-style).
 * - Enables DEBUG_SYNC_REDRAW (bypasses RAF when it blocks render)
 * - Triggers resize + redraw on workspace events and after load
 */
(function () {
  "use strict";

  function forceRedraw() {
    try {
      if (typeof window.RED !== "undefined" && window.RED.view) {
        if (typeof window.RED.view.redraw === "function") {
          window.RED.view.redraw();
        }
      }
    } catch (e) {}
    window.dispatchEvent(new Event("resize"));
  }

  function applyFix() {
    if (typeof window.RED === "undefined") return false;
    try {
      if (window.RED.view && "DEBUG_SYNC_REDRAW" in window.RED.view) {
        window.RED.view.DEBUG_SYNC_REDRAW = true;
      }
      if (window.RED.events) {
        ["workspace:show", "workspace:change"].forEach(function (ev) {
          window.RED.events.on(ev, function () {
            setTimeout(forceRedraw, 50);
          });
        });
      }
      document.addEventListener("visibilitychange", function () {
        if (document.visibilityState === "visible") setTimeout(forceRedraw, 100);
      });
      setTimeout(forceRedraw, 300);
      setTimeout(forceRedraw, 800);
      setTimeout(forceRedraw, 1500);
      return true;
    } catch (e) {
      return false;
    }
  }

  function init() {
    if (applyFix()) return;
    var attempts = 0;
    var iv = setInterval(function () {
      attempts++;
      if (applyFix() || attempts > 60) clearInterval(iv);
    }, 100);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
