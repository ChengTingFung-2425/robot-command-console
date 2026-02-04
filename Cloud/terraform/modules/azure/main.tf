# Azure resources configuration

resource "azurerm_storage_account" "example" {
  name                     = "examplestor${random_id.storage_id.hex}"
  resource_group_name      = var.resource_group_name
  location                 = var.azure_region
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "random_id" "storage_id" {
  byte_length = 8
}

variable "resource_group_name" {
  description = "Azure resource group name"
  type        = string
}

variable "azure_region" {
  description = "Azure region for deployment"
  type        = string
  default     = "East US"
}