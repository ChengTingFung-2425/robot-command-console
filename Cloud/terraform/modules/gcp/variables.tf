variable "gcp_project" {
  description = "GCP project ID for deployment"
  type        = string
}

variable "gcp_region" {
  description = "GCP region for deployment"
  type        = string
  default     = "us-central1"
}

variable "bucket_name_prefix" {
  description = "Prefix for the GCP storage bucket name"
  type        = string
  default     = "robot-cloud-gcp"
}
