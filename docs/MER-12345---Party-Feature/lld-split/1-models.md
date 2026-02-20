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
