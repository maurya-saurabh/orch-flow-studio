/** Node-RED settings for Orch Flow Studio.
 *  Uses flows_chat.json as the flow file.
 *  Theme shows loading overlay until flow is fully loaded.
 */
module.exports = {
  flowFile: "flows_chat.json",
  /** Allow large flow payloads (API POST /flows). Default 5mb; set higher for very large flows. */
  apiMaxLength: "10mb",
  editorTheme: {
    theme: "orch-flow-loading-theme",
  },
};
