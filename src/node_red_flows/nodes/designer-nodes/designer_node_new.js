/**
 * designer_node_new - Node that takes config object and name.
 * Supports dynamic number of outputs.
 */
module.exports = function (RED) {
    "use strict";

    function DesignerNodeNew(config) {
        RED.nodes.createNode(this, config);
        var node = this;
        node.name = config.name;
        node.config = config.config || {};
        node.outputs = config.outputs || 1;

        node.on("input", function (msg, send, done) {
            send = send || function () {
                node.send.apply(node, arguments);
            };

            try {
                // Add config to message and pass through to configured outputs
                var outputCount = node.outputCount || node.outputs || 1;
                msg.payload = msg.payload || {};
                if (typeof msg.payload === "object") {
                    msg.payload._designerConfig = node.config;
                }
                var messages = new Array(outputCount);
                messages[0] = msg;
                send(messages);
            } catch (err) {
                if (done) {
                    done(err);
                } else {
                    node.error(err, msg);
                }
                return;
            }

            if (done) {
                done();
            }
        });
    }

    RED.nodes.registerType("designer_node_new", DesignerNodeNew);
};
