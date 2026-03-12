"""Cloud Terraform configuration tests."""

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
TERRAFORM_ROOT = REPO_ROOT / "Cloud" / "terraform"


class TestCloudTerraformConfig(unittest.TestCase):
    """Validate Cloud Terraform wiring with lightweight static assertions."""

    def test_root_declares_required_providers(self):
        """Root Terraform config should declare required providers."""
        content = (TERRAFORM_ROOT / "main.tf").read_text(encoding="utf-8")

        self.assertIn('required_providers {', content)
        self.assertIn('source  = "hashicorp/aws"', content)
        self.assertIn('source  = "hashicorp/google"', content)
        self.assertIn('source  = "hashicorp/azurerm"', content)
        self.assertIn('source  = "hashicorp/random"', content)

    def test_root_modules_pass_required_variables(self):
        """Root modules should pass the variables required by child modules."""
        content = (TERRAFORM_ROOT / "main.tf").read_text(encoding="utf-8")

        self.assertIn('bucket_name_prefix = var.aws_bucket_name_prefix', content)
        self.assertIn('gcp_project        = var.gcp_project', content)
        self.assertIn('gcp_region         = var.gcp_region', content)
        self.assertIn('resource_group_name         = var.azure_resource_group_name', content)
        self.assertIn('azure_region                = var.azure_region', content)
        self.assertIn(
            'storage_account_name_prefix = var.azure_storage_account_name_prefix',
            content,
        )

    def test_azure_module_creates_resource_group_and_safe_name_length(self):
        """Azure module should create its resource group and keep names within limits."""
        content = (TERRAFORM_ROOT / "modules" / "azure" / "main.tf").read_text(
            encoding="utf-8"
        )

        self.assertIn('resource "azurerm_resource_group" "example"', content)
        self.assertIn('resource_group_name      = azurerm_resource_group.example.name', content)
        self.assertIn('byte_length = 6', content)

    def test_gcp_module_declares_used_variables(self):
        """GCP module should declare the variables used by its resources."""
        content = (TERRAFORM_ROOT / "modules" / "gcp" / "variables.tf").read_text(
            encoding="utf-8"
        )

        self.assertIn('variable "gcp_project"', content)
        self.assertIn('variable "gcp_region"', content)
        self.assertIn('variable "bucket_name_prefix"', content)

    def test_example_tfvars_and_outputs_exist(self):
        """Terraform examples and outputs should be present for operator use."""
        tfvars = (TERRAFORM_ROOT / "terraform.tfvars.example").read_text(
            encoding="utf-8"
        )
        outputs = (TERRAFORM_ROOT / "outputs.tf").read_text(encoding="utf-8")

        self.assertIn('gcp_project', tfvars)
        self.assertIn('azure_subscription_id', tfvars)
        self.assertIn('output "aws_s3_bucket_name"', outputs)
        self.assertIn('output "azure_storage_account_name"', outputs)
