/**
 * designer_node_existing - Node that takes name and id, displays name in the flow.
 * Supports dynamic number of outputs.
 */
module.exports = function (RED) {
    "use strict";

    function DesignerNodeExisting(config) {
        RED.nodes.createNode(this, config);
        var node = this;
        node.name = config.name;
        node.id = config.id;
        node.outputs = config.outputs || 1;

        node.on("input", function (msg, send, done) {
            send = send || function () {
                node.send.apply(node, arguments);
            };

            try {
                // Pass through message to configured outputs
                var outputCount = node.outputCount || node.outputs || 1;
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

    RED.nodes.registerType("designer_node_existing", DesignerNodeExisting);
};
