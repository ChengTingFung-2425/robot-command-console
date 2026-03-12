output "bucket_name" {
  description = "GCP storage bucket name"
  value       = google_storage_bucket.example.name
}
