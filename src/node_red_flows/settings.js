/** Node-RED settings for Orch Flow Studio.
 *  Uses flows_chat.json as the flow file.
 *  editorTheme.page.scripts injects canvas-fix.js to fix blank flow / "click to show" rendering.
 */
var path = require("path");

module.exports = {
  flowFile: "flows_chat.json",
  /** Allow large flow payloads (API POST /flows). Default 5mb; set higher for very large flows. */
  apiMaxLength: "10mb",
  editorTheme: {
    page: {
      scripts: path.join(__dirname, "canvas-fix.js"),
    },
  },
};
