# ABOUTME: Path constants for the processing_unit pipeline.
# ABOUTME: All paths are derived from config_dir (sourced from .env via settings).

from autobots_orch_flow_studio.configs.settings import AppSettings

# ---------------------------------------------------------------------------
# Base path - single source of truth from .env
# ---------------------------------------------------------------------------
_settings = AppSettings()
KB_PATH: str = str(_settings.dynagent_config_root_dir)

# ---------------------------------------------------------------------------
# Output directory components
# ---------------------------------------------------------------------------
OEPY_DOCS_DIR = "oepy-docs"
AGENTIC_GENERATOR_META_DIR = "agentic-generator-meta"
KG_NODE_META_DIR = "kg-node-meta"

# ---------------------------------------------------------------------------
# Derived output paths (relative to file-server root)
# ---------------------------------------------------------------------------
EXTRACTION_GUIDE_DIR = f"{KB_PATH}/{OEPY_DOCS_DIR}/{AGENTIC_GENERATOR_META_DIR}"
EXTRACTION_GUIDE_FILE = "node-kg-extraction-guide.md"
EXTRACTION_GUIDE_PATH = f"{EXTRACTION_GUIDE_DIR}/{EXTRACTION_GUIDE_FILE}"

NODE_META_DIR = f"{KB_PATH}/{OEPY_DOCS_DIR}/{AGENTIC_GENERATOR_META_DIR}/{KG_NODE_META_DIR}"


# ---------------------------------------------------------------------------
# Agent names
# ---------------------------------------------------------------------------
KBE_APP_NAME = "kbe-pay"
SCHEMA_PROCESSOR_AGENT = "schema_processor"
NODE_KG_EXTRACTION_AGENT = "node_kg_extraction"


# Input directory path components
COMMON_MODELS_DIR = "common/models"

# Output directory path components
OEPY_DOCS_DIR = "oepy-docs"
AGENTIC_GENERATOR_META_DIR = "agentic-generator-meta"
KG_MODEL_META_DIR = "kg-model-meta"
KG_NODE_META_DIR = "kg-node-meta"
KG_FLOW_META_DIR = "kg-flow-meta"
MODELS_SPEC_DIR = "models/specs"
MODELS_TEST_PARAMS_DIR = "models/test-params"
JSON_EXTENSION = ".json"

# Template file names (under docs/templates)
TEMPLATE_MODEL_JSON = "model.json"
TEMPLATE_MODEL_TEST_PARAMS_JSON = "model_test_params.json"

# Node KBE paths
NODES_DIR = "nodes"
NODE_PREFIX = "node-red-contrib-"
LIB_DIR = "lib"

# KB reference paths
KB_DOCS_DIR = "oepy-docs/knowledge-base"
INTERFACES_ASYNC_DIR = "interfaces/async"
INTERFACES_SYNC_DIR = "interfaces/sync"

# Generated artifacts
EXTRACTION_GUIDE_DIR = "oepy-docs/agentic-generator-meta"
EXTRACTION_GUIDE_FILE = "node-kg-extraction-guide.md"

# Model Name
SCHEMA_PROCESSOR_MODEL_NAME = "schema_processor"
RECURSION_TOOL_LIMIT = 50


APP_NAME = "payments-kbe"
CURRENT_DIR = "."

KB_PATH = "knowledge_base/payments"
PROCESSING_UNITS_DIR = "processing-units"
NODE_REGISTRY_FILE = "node-registry.json"

# LLD processor: base directory for split MD output (one subfolder per source MD)
LLD_SPLIT_MD_SUBDIR = "lld-split"
# LLD_SPLIT_OUTPUT_BASE_DIR = f"{KB_PATH}/{OEPY_DOCS_DIR}/{AGENTIC_GENERATOR_META_DIR}/{LLD_SPLIT_MD_SUBDIR}"
LLD_SPLIT_OUTPUT_BASE_DIR = (
    f"/Users/saurabh/Documents/server/orch-ai-studio/data/{LLD_SPLIT_MD_SUBDIR}"
)
INPUT_LLD_DIR = "/Users/saurabh/Documents/server/orch-ai-studio/orch-flow-studio/docs/sample_md"
