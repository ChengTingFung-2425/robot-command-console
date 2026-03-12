# Azure resources configuration

resource "azurerm_resource_group" "example" {
  name     = var.resource_group_name
  location = var.azure_region
}

resource "azurerm_storage_account" "example" {
  # Azure storage account names must stay within 24 chars; 6 random bytes -> 12 hex chars,
  # so the validated prefix must stay within 12 lowercase alphanumeric chars.
  name                     = "${var.storage_account_name_prefix}${random_id.storage_id.hex}"
  resource_group_name      = azurerm_resource_group.example.name
  location                 = azurerm_resource_group.example.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "random_id" "storage_id" {
  byte_length = 6
}
