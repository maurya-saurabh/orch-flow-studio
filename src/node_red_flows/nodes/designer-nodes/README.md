# Node-RED Designer Nodes

Custom nodes for Orch Flow Studio with dynamic outputs and dotted borders.

## Nodes

### designer_node_existing

- **Properties**: `name`, `id`
- **Display**: The name is shown as the label in the flow
- **Outputs**: Configurable (1–128) via the edit dialog
- **Border**: Dotted

### designer_node_new

- **Properties**: `config` (JSON object), `name`
- **Display**: The name is shown as the label in the flow
- **Outputs**: Configurable (1–128) via the edit dialog
- **Border**: Dotted
- **Config**: Pass a JSON object; it is attached to `msg.payload._designerConfig` for downstream nodes

## Usage

1. Run Node-RED: `make node-red` from the orch-flow-studio project root
2. Open http://localhost:1880
3. Find the **designer** category in the palette
4. Drag **designer_node_existing** or **designer_node_new** onto the flow
5. Configure name, id/config, and number of outputs
