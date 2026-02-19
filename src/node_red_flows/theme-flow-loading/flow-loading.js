/**
 * Flow loading overlay - show until flow is fully loaded.
 * Uses polling to detect when workspace has nodes/tabs. Avoids workspace:show/change
 * to prevent hiding too early (which would cause flash / "flow updating" effect).
 * After hiding, programmatically focuses the workspace canvas so the flow displays
 * without requiring a user click (fixes "flow gone until I click canvas" issue).
 */
(function () {
  "use strict";

  var POLL_INTERVAL_MS = 80;
  var STABLE_CYCLES_REQUIRED = 2; // Require nodes visible for 2 polls to avoid flash
  var MAX_WAIT_MS = 15000; // Large flows can take time to render
  var FADE_OUT_MS = 350;
  var FOCUS_DELAY_MS = 100; // Delay before focusing canvas (let overlay fully hide)

  function createOverlay() {
    var overlay = document.createElement("div");
    overlay.id = "orch-flow-loading-overlay";
    overlay.innerHTML =
      '<div class="orch-flow-loading-content">' +
      '<div class="orch-flow-loading-spinner"></div>' +
      '<div class="orch-flow-loading-text">Loading flow…</div>' +
      "</div>";
    document.body.appendChild(overlay);
    return overlay;
  }

  /**
   * Focus the workspace canvas so the flow displays. Node-RED needs focus/click
   * on the canvas to properly render; without this the flow stays blank until
   * the user manually clicks.
   */
  function focusWorkspaceCanvas() {
    var chart = document.getElementById("red-ui-workspace-chart");
    if (!chart) return;
    var svg = chart.querySelector("svg");
    var target = svg || chart;
    var rect = target.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return;
    var evt = new MouseEvent("mousedown", {
      bubbles: true,
      cancelable: true,
      view: window,
      clientX: rect.left + rect.width / 2,
      clientY: rect.top + rect.height / 2,
      button: 0,
      buttons: 1,
    });
    target.dispatchEvent(evt);
    if (chart.focus) chart.focus();
  }

  function init() {
    var overlay = document.getElementById("orch-flow-loading-overlay");
    if (!overlay) overlay = createOverlay();

    var hidden = false;
    var pollCount = 0;
    var stableCount = 0;
    var startTime = Date.now();

    function hideOverlay() {
      if (hidden) return;
      hidden = true;
      overlay.classList.add("orch-flow-loaded");
      setTimeout(function () {
        overlay.style.display = "none";
        setTimeout(focusWorkspaceCanvas, FOCUS_DELAY_MS);
      }, FADE_OUT_MS);
    }

    function checkWorkspaceReady() {
      var workspace = document.querySelector(".red-ui-workspace");
      if (!workspace || !workspace.offsetParent) return false;
      var nodes = workspace.querySelectorAll(".red-ui-flow-node");
      var tabs = document.querySelectorAll(".red-ui-tab");
      return nodes.length > 0 || tabs.length > 0;
    }

    function pollForReady() {
      pollCount++;
      if (hidden) return;
      if (Date.now() - startTime > MAX_WAIT_MS) {
        hideOverlay();
        return;
      }
      if (checkWorkspaceReady()) {
        stableCount++;
        if (stableCount >= STABLE_CYCLES_REQUIRED) {
          hideOverlay();
          return;
        }
      } else {
        stableCount = 0;
      }
      setTimeout(pollForReady, POLL_INTERVAL_MS);
    }

    setTimeout(pollForReady, 150);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
