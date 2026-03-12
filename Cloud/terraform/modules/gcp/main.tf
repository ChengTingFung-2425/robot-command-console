# GCP resources configuration

resource "google_storage_bucket" "example" {
  name     = "${var.bucket_name_prefix}-${random_id.bucket_id.hex}"
  location = var.gcp_region
  project  = var.gcp_project
}

resource "random_id" "bucket_id" {
  byte_length = 8
}
