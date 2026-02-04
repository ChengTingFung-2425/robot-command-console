# AWS resources configuration

resource "aws_s3_bucket" "example" {
  bucket = "example-bucket-${random_id.bucket_id.hex}"
  acl    = "private"
}

resource "random_id" "bucket_id" {
  byte_length = 8
}