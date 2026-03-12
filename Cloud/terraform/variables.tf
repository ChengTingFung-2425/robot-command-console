# Variables for multi-cloud deployment

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "aws_bucket_name_prefix" {
  description = "Prefix for the AWS S3 bucket name"
  type        = string
  default     = "robot-cloud-aws"
}

variable "gcp_project" {
  description = "GCP project ID for deployment"
  type        = string
}

variable "gcp_region" {
  description = "GCP region for deployment"
  type        = string
  default     = "us-central1"
}

variable "gcp_bucket_name_prefix" {
  description = "Prefix for the GCP storage bucket name"
  type        = string
  default     = "robot-cloud-gcp"
}

variable "azure_subscription_id" {
  description = "Azure subscription ID for deployment"
  type        = string
}

variable "azure_region" {
  description = "Azure region for deployment"
  type        = string
  default     = "East US"
}

variable "azure_resource_group_name" {
  description = "Azure resource group name for Terraform-managed resources"
  type        = string
  default     = "robot-command-console-rg"
}

variable "azure_storage_account_name_prefix" {
  description = "Prefix for the Azure storage account name"
  type        = string
  default     = "robotsa"

  # Keep this aligned with modules/azure/main.tf random_id.byte_length = 6 (12 hex chars).
  validation {
    condition     = can(regex("^[a-z0-9]{1,12}$", var.azure_storage_account_name_prefix))
    error_message = "azure_storage_account_name_prefix must be 1-12 lowercase alphanumeric characters so the prefix plus the 12-char hex suffix stays within Azure's 24-character limit."
  }
}
