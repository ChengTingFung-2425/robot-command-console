# Main Terraform configuration for multi-cloud deployment

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

provider "google" {
  project = var.gcp_project
  region  = var.gcp_region
}

provider "azurerm" {
  features {}
  subscription_id = var.azure_subscription_id
}

# Define resources for each cloud provider
module "aws_resources" {
  source             = "./modules/aws"
  bucket_name_prefix = var.aws_bucket_name_prefix
}

module "gcp_resources" {
  source             = "./modules/gcp"
  gcp_project        = var.gcp_project
  gcp_region         = var.gcp_region
  bucket_name_prefix = var.gcp_bucket_name_prefix
}

module "azure_resources" {
  source                      = "./modules/azure"
  resource_group_name         = var.azure_resource_group_name
  azure_region                = var.azure_region
  storage_account_name_prefix = var.azure_storage_account_name_prefix
}
