variable "resource_group_name" {
  description = "Azure resource group name"
  type        = string
}

variable "azure_region" {
  description = "Azure region for deployment"
  type        = string
  default     = "East US"
}

variable "storage_account_name_prefix" {
  description = "Prefix for the Azure storage account name"
  type        = string
  default     = "robotsa"
}
