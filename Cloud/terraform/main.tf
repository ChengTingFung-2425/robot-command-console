# Main Terraform configuration for multi-cloud deployment

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
  source = "./modules/aws"
}

module "gcp_resources" {
  source = "./modules/gcp"
}

module "azure_resources" {
  source = "./modules/azure"
}
