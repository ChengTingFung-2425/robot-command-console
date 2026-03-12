output "bucket_name" {
  description = "AWS S3 bucket name"
  value       = aws_s3_bucket.example.bucket
}
