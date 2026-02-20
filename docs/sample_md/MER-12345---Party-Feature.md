# 0. Background
(Template Note: Background information on the feature being described. Can include business requirements and functional overview)
## Purpose
The Party Management System provides a flexible, metadata-driven framework for managing parties (individuals and organizations) and their relationships with domain entities across banking products.
# 1. Models
(Template Note: Schemas to be created as part of this feature. Copy 1.1 and replicate as many times as required)

(Columns marked with Business Key = Y - will be used as pseudo primary keys in case of entity being created from DTO)
## 1.1 PaymentOrder
(Template Note: Data Type can be one of the OAS standard data types (e.g. String), FBP Standard Data Types(e.g. BusinessDateDTO) or refer to other DTOs and Enums defined in section 1 & 2. In case of enhancements to existing schemas, please provide e.g. Is New Model: EXISTING/OLD, else provide Is New Model: NEW)
### Is New Model: False
### Model Structure:
| Column Name | Business Name (Optional) | Data Type | &lt;Can be another model.json&gt; | Business Key [Y/N] | Mandatory [Y/N] | Properties | &lt;can be enum as well&gt; | Default Value | Description |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| coverPaysysId | coverPaysysId | String | Y | N | {maxLength: 12} |  | Business-assigned coverPaysysId |

## 1.2 PoAddnlDtls
(Template Note: Data Type can be one of the OAS standard data types (e.g. String), FBP Standard Data Types(e.g. BusinessDateDTO) or refer to other DTOs and Enums defined in section 1 & 2. In case of enhancements to existing schemas, please provide e.g. Is New Model: EXISTING/OLD, else provide Is New Model: NEW)
### Is New Model: False
### Model Structure:
| Column Name | Business Name (Optional) | Data Type | &lt;Can be another model.json&gt; | Business Key [Y/N] | Mandatory [Y/N] | Properties | &lt;can be enum as well&gt; | Default Value | Description |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| isCoverPaysysDiff | isCoverPaysysDiff | String | N | N | {maxLength: 1} |  | Business-assigned coverPaysysId if different |

# 2. Sync Methods

| Endpoint | Method | Model | Input | Output | Associated Behaviour |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |

# 3. Async Methods

| Queue Name | Flow Name | Type (Send/Receive) |
| --- | --- | --- |
|  |  |  |

# 4. Behaviours:
Type → LLM Assisted / Standard / Manual

Sub-Type → Enrichment / Validation / Host Call / Processing / Persistence

*Assuming Behaviours are functions to be written, or in our case, nodes to be created

## New Nodes to be added:
| behaviour name | to be registered | folder name | node name | file name | config | Cosmetic properties | Business logic |
| --- | --- | --- | --- | --- | --- | --- | --- |
| enrichCovSttlmtAcct | true | oepy-common/SP | cover-sttlmtacct-derivation | enrichCovSttlmtAcct |  | { “Description”: “This node derives cover settlement account” } | {} | This node derives cover settlement account |


