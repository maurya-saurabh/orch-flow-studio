/** Theme plugin: show loading overlay until flow is fully loaded */
var path = require("path");

module.exports = function (RED) {
  RED.plugins.registerPlugin("orch-flow-loading-theme", {
    type: "node-red-theme",
    css: path.join(__dirname, "flow-loading.css"),
    scripts: path.join(__dirname, "flow-loading.js"),
  });
};
