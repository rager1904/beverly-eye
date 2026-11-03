terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

variable "name" {
  description = "Base name for CDN resources"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "domain_name" {
  description = "Domain name for the CDN"
  type        = string
}

variable "aliases" {
  description = "Additional domain aliases"
  type        = list(string)
  default     = []
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN"
  type        = string
}

variable "origin_bucket_domain_name" {
  description = "Origin S3 bucket domain name"
  type        = string
}

variable "origin_bucket_arn" {
  description = "Origin S3 bucket ARN"
  type        = string
}

variable "api_origin_domain_name" {
  description = "API origin domain name"
  type        = string
}

variable "allowed_countries" {
  description = "Allowed country codes"
  type        = list(string)
  default     = []
}

variable "price_class" {
  description = "CloudFront price class"
  type        = string
  default     = "PriceClass_100"
}

variable "waf_web_acl_arn" {
  description = "WAF WebACL ARN"
  type        = string
  default     = ""
}

variable "logging_bucket" {
  description = "S3 bucket for access logs"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}

locals {
  name = "${var.name}-${var.environment}"
}

# Origin Access Identity
resource "aws_cloudfront_origin_access_identity" "main" {
  comment = "OAI for ${local.name}"
}

# CloudFront Distribution
resource "aws_cloudfront_distribution" "main" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "CDN for ${local.name}"
  default_root_object = "index.html"
  price_class         = var.price_class
  aliases             = concat([var.domain_name], var.aliases)

  # Static origin
  origin {
    domain_name = var.origin_bucket_domain_name
    origin_id   = "static"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.main.cloudfront_access_identity_path
    }
  }

  # API origin
  origin {
    domain_name = var.api_origin_domain_name
    origin_id   = "api"

    custom_origin_config {
      http_port                = 80
      https_port               = 443
      origin_protocol_policy   = "https-only"
      origin_ssl_protocols     = ["TLSv1.2"]
      origin_read_timeout      = 60
      origin_keepalive_timeout = 5
    }
  }

  # Default cache behavior (static)
  default_cache_behavior {
    target_origin_id       = "static"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS", "PUT", "PATCH", "POST", "DELETE"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 86400
    max_ttl     = 31536000
  }

  # API cache behavior
  ordered_cache_behavior {
    path_pattern           = "/api/*"
    target_origin_id       = "api"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Content-Type", "X-API-Key", "Accept"]
      cookies {
        forward = "all"
      }
    }

    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
  }

  # Static assets cache behavior
  ordered_cache_behavior {
    path_pattern           = "/static/*"
    target_origin_id       = "static"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD", "OPTIONS"]
    compress               = true

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 31536000
    max_ttl     = 31536000
  }

  # Geo restriction
  dynamic "restrictions" {
    for_each = length(var.allowed_countries) > 0 ? [1] : []
    content {
      geo_restriction {
        restriction_type = "whitelist"
        locations        = var.allowed_countries
      }
    }
  }

  # Viewer certificate
  viewer_certificate {
    acm_certificate_arn      = var.acm_certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  # WAF
  dynamic "web_acl_id" {
    for_each = var.waf_web_acl_arn != "" ? [var.waf_web_acl_arn] : []
    content {
      web_acl_id = web_acl_id.value
    }
  }

  # Logging
  dynamic "logging_config" {
    for_each = var.logging_bucket != "" ? [1] : []
    content {
      include_cookies = false
      bucket          = var.logging_bucket
      prefix          = "cloudfront/"
    }
  }

  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }

  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  tags = merge(var.tags, {
    Name = "${local.name}-cdn"
  })
}

# S3 bucket policy for OAI
resource "aws_s3_bucket_policy" "origin" {
  bucket = var.origin_bucket_arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = aws_cloudfront_origin_access_identity.main.iam_arn
        }
        Action   = "s3:GetObject"
        Resource = "${var.origin_bucket_arn}/*"
      }
    ]
  })
}

# Outputs
output "distribution_id" {
  value = aws_cloudfront_distribution.main.id
}

output "distribution_arn" {
  value = aws_cloudfront_distribution.main.arn
}

output "domain_name" {
  value = aws_cloudfront_distribution.main.domain_name
}

output "hosted_zone_id" {
  value = aws_cloudfront_distribution.main.hosted_zone_id
}

output "origin_access_identity_iam_arn" {
  value = aws_cloudfront_origin_access_identity.main.iam_arn
}
