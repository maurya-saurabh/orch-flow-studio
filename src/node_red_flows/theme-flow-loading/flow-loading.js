/**
 * Flow loading overlay - show until flow is fully loaded.
 * Uses polling to detect when workspace has nodes/tabs. Avoids workspace:show/change
 * to prevent hiding too early (which would cause flash / "flow updating" effect).
 * After hiding, programmatically focuses and activates the workspace canvas so the
 * flow displays without requiring a user click (fixes "flow gone until I click
 * canvas" issue).
 */
(function () {
  "use strict";

  var POLL_INTERVAL_MS = 80;
  var STABLE_CYCLES_REQUIRED = 3; // Require nodes visible for 3 polls (more stable)
  var MAX_WAIT_MS = 20000; // Large flows can take time to render
  var FADE_OUT_MS = 350;
  var FOCUS_DELAY_MS = 150; // Delay before first focus attempt
  var FOCUS_RETRY_MS = 300; // Retry focus at 150ms, 450ms, 750ms
  var FOCUS_RETRIES = 3;

  function createOverlay() {
    var overlay = document.createElement("div");
    overlay.id = "orch-flow-loading-overlay";
    overlay.innerHTML =
      '<div class="orch-flow-loading-content">' +
      '<div class="orch-flow-loading-spinner"></div>' +
      '<div class="orch-flow-loading-text">Loading flow…</div>' +
      '<div class="orch-flow-loading-hint">Click to continue if stuck</div>' +
      "</div>";
    document.body.appendChild(overlay);
    return overlay;
  }

  /**
   * Find the workspace canvas. Node-RED 4 may use different IDs/classes.
   */
  function findCanvasElement() {
    var chart = document.getElementById("red-ui-workspace-chart") ||
      document.getElementById("chart");
    if (chart) return chart;
    var workspace = document.querySelector(".red-ui-workspace");
    if (workspace) {
      var canvas = workspace.querySelector("#red-ui-workspace-chart, #chart");
      if (canvas) return canvas;
      var svg = workspace.querySelector("svg");
      if (svg) return svg.parentElement || svg;
    }
    return null;
  }

  /**
   * Simulate a full click (mousedown + mouseup) on the canvas. Node-RED needs
   * this to properly render/redraw the flow; without it the flow stays blank.
   */
  function focusWorkspaceCanvas() {
    var chart = findCanvasElement();
    if (!chart) return;
    var target = chart.querySelector("svg") || chart;
    var rect = target.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return;

    var cx = rect.left + rect.width / 2;
    var cy = rect.top + rect.height / 2;
    var base = { bubbles: true, cancelable: true, view: window, clientX: cx, clientY: cy, button: 0 };

    target.dispatchEvent(new MouseEvent("mousedown", Object.assign({}, base, { buttons: 1 })));
    target.dispatchEvent(new MouseEvent("mouseup", Object.assign({}, base, { buttons: 0 })));
    target.dispatchEvent(new MouseEvent("click", base));
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
        for (var i = 0; i < FOCUS_RETRIES; i++) {
          setTimeout(focusWorkspaceCanvas, FOCUS_DELAY_MS + i * FOCUS_RETRY_MS);
        }
      }, FADE_OUT_MS);
    }

    function checkWorkspaceReady() {
      var workspace = document.querySelector(".red-ui-workspace");
      if (!workspace || !workspace.offsetParent) return false;
      var nodes = workspace.querySelectorAll(".red-ui-flow-node, .flow-node, [class*=\"flow-node\"]");
      var tabs = document.querySelectorAll(".red-ui-tab, [class*=\"red-ui-tab\"]");
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

    overlay.addEventListener("click", function () {
      if (!hidden) hideOverlay();
    });

    setTimeout(pollForReady, 150);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
