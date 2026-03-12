output "resource_group_name" {
  description = "Azure resource group name"
  value       = azurerm_resource_group.example.name
}

output "storage_account_name" {
  description = "Azure storage account name"
  value       = azurerm_storage_account.example.name
}
