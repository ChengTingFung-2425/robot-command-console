output "aws_s3_bucket_name" {
  description = "AWS S3 bucket managed by Terraform"
  value       = module.aws_resources.bucket_name
}

output "gcp_storage_bucket_name" {
  description = "GCP storage bucket managed by Terraform"
  value       = module.gcp_resources.bucket_name
}

output "azure_resource_group_name" {
  description = "Azure resource group managed by Terraform"
  value       = module.azure_resources.resource_group_name
}

output "azure_storage_account_name" {
  description = "Azure storage account managed by Terraform"
  value       = module.azure_resources.storage_account_name
}
