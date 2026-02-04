# GCP resources configuration

resource "google_storage_bucket" "example" {
  name     = "example-bucket-${random_id.bucket_id.hex}"
  location = var.gcp_region
}

resource "random_id" "bucket_id" {
  byte_length = 8
}