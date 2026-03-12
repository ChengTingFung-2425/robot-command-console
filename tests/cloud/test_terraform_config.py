"""Cloud Terraform configuration tests."""

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
TERRAFORM_ROOT = REPO_ROOT / "Cloud" / "terraform"


class TestCloudTerraformConfig(unittest.TestCase):
    """Validate Cloud Terraform wiring with lightweight static assertions."""

    @classmethod
    def setUpClass(cls):
        """Cache Terraform file contents used across tests."""
        cls.root_main = (TERRAFORM_ROOT / "main.tf").read_text(encoding="utf-8")
        cls.root_outputs = (TERRAFORM_ROOT / "outputs.tf").read_text(encoding="utf-8")
        cls.example_tfvars = (TERRAFORM_ROOT / "terraform.tfvars.example").read_text(
            encoding="utf-8"
        )
        cls.azure_main = (TERRAFORM_ROOT / "modules" / "azure" / "main.tf").read_text(
            encoding="utf-8"
        )
        cls.gcp_variables = (
            TERRAFORM_ROOT / "modules" / "gcp" / "variables.tf"
        ).read_text(encoding="utf-8")

    def test_root_declares_required_providers(self):
        """Root Terraform config should declare required providers."""
        self.assertIn('terraform {', self.root_main)
        self.assertIn('required_providers {', self.root_main)
        self.assertIn('source  = "hashicorp/aws"', self.root_main)
        self.assertIn('source  = "hashicorp/google"', self.root_main)
        self.assertIn('source  = "hashicorp/azurerm"', self.root_main)
        self.assertIn('source  = "hashicorp/random"', self.root_main)

    def test_root_modules_pass_required_variables(self):
        """Root modules should pass the variables required by child modules."""
        self.assertIn('bucket_name_prefix = var.aws_bucket_name_prefix', self.root_main)
        self.assertIn('gcp_project        = var.gcp_project', self.root_main)
        self.assertIn('gcp_region         = var.gcp_region', self.root_main)
        self.assertIn('bucket_name_prefix = var.gcp_bucket_name_prefix', self.root_main)
        self.assertIn(
            'resource_group_name         = var.azure_resource_group_name',
            self.root_main,
        )
        self.assertIn('azure_region                = var.azure_region', self.root_main)
        self.assertIn(
            'storage_account_name_prefix = var.azure_storage_account_name_prefix',
            self.root_main,
        )

    def test_azure_module_resource_group_and_name_constraints(self):
        """Azure module should create its resource group and keep names within limits."""
        self.assertIn('resource "azurerm_resource_group" "example"', self.azure_main)
        self.assertIn(
            'resource_group_name      = azurerm_resource_group.example.name',
            self.azure_main,
        )
        self.assertIn('byte_length = 6', self.azure_main)

    def test_gcp_module_declares_used_variables(self):
        """GCP module should declare the variables used by its resources."""
        self.assertIn('variable "gcp_project"', self.gcp_variables)
        self.assertIn('variable "gcp_region"', self.gcp_variables)
        self.assertIn('variable "bucket_name_prefix"', self.gcp_variables)

    def test_example_tfvars_and_outputs_exist(self):
        """Terraform examples and outputs should be present for operator use."""
        self.assertIn('gcp_project', self.example_tfvars)
        self.assertIn('azure_subscription_id', self.example_tfvars)
        self.assertIn('output "aws_s3_bucket_name"', self.root_outputs)
        self.assertIn('output "azure_storage_account_name"', self.root_outputs)
