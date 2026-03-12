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

  validation {
    condition     = can(regex("^[a-z0-9]{1,12}$", var.storage_account_name_prefix))
    error_message = "storage_account_name_prefix must be 1-12 lowercase alphanumeric characters so the prefix plus the 12-char hex suffix stays within Azure's 24-character limit."
  }
}
