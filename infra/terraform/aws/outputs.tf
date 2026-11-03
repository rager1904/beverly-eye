output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
  sensitive   = true
}

output "eks_cluster_certificate_authority" {
  description = "EKS cluster certificate authority data"
  value       = module.eks.cluster_certificate_authority
  sensitive   = true
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = module.database.endpoint
  sensitive   = true
}

output "rds_reader_endpoint" {
  description = "RDS PostgreSQL reader endpoint"
  value       = module.database.reader_endpoint
  sensitive   = true
}

output "redis_primary_endpoint" {
  description = "ElastiCache Redis primary endpoint"
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
  sensitive   = true
}

output "redis_reader_endpoint" {
  description = "ElastiCache Redis reader endpoint"
  value       = aws_elasticache_replication_group.redis.reader_endpoint_address
  sensitive   = true
}

output "s3_model_storage" {
  description = "S3 bucket for ML model storage"
  value       = aws_s3_bucket.models.id
}

output "s3_medical_images" {
  description = "S3 bucket for medical images"
  value       = aws_s3_bucket.medical_images.id
}

output "s3_backups" {
  description = "S3 bucket for backups"
  value       = aws_s3_bucket.backups.id
}

output "s3_audit_logs" {
  description = "S3 bucket for audit logs"
  value       = aws_s3_bucket.audit_logs.id
}

output "route53_zone_id" {
  description = "Route53 hosted zone ID"
  value       = aws_route53_zone.primary.zone_id
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = aws_cloudfront_distribution.main.id
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.main.domain_name
}

output "waf_acl_id" {
  description = "WAF WebACL ID"
  value       = aws_wafv2_web_acl.main.id
}

output "alb_dns_name" {
  description = "Application Load Balancer DNS name"
  value       = aws_lb.api.dns_name
}

output "ecr_repository_urls" {
  description = "Map of ECR repository names to URLs"
  value = {
    for repo in aws_ecr_repository.services : repo.name => repo.repository_url
  }
}

output "sns_topic_arn" {
  description = "SNS topic ARN for alerts"
  value       = aws_sns_topic.alerts.arn
}

output "sqs_queue_url" {
  description = "SQS queue URL for notifications"
  value       = aws_sqs_queue.notifications.id
}

output "backup_vault_arn" {
  description = "Backup vault ARN"
  value       = aws_backup_vault.main.arn
}

output "cloudwatch_log_group_arns" {
  description = "Map of CloudWatch log group ARNs"
  value = {
    api      = aws_cloudwatch_log_group.api.arn
    redis    = aws_cloudwatch_log_group.redis.arn
    database = aws_cloudwatch_log_group.database.arn
    waf      = aws_cloudwatch_log_group.waf.arn
  }
}

output "kms_key_ids" {
  description = "Map of KMS key IDs"
  value = {
    s3        = aws_kms_key.s3.key_id
    rds       = aws_kms_key.rds.key_id
    redis     = aws_kms_key.redis.key_id
    ecr       = aws_kms_key.ecr.key_id
    cloudwatch = aws_kms_key.cloudwatch.key_id
    backup    = aws_kms_key.backup.key_id
  }
  sensitive = true
}

output "region" {
  description = "AWS region"
  value       = var.aws_region
}

output "environment" {
  description = "Deployment environment"
  value       = var.environment
}

output "domain_name" {
  description = "Primary domain name"
  value       = var.domain_name
}

output "database_subnet_group" {
  description = "Database subnet group name"
  value       = module.database.subnet_group_name
}

output "eks_node_role_arn" {
  description = "EKS node IAM role ARN"
  value       = aws_iam_role.eks_node_role.arn
}

output "eks_oidc_provider" {
  description = "EKS OIDC provider"
  value       = module.eks.oidc_provider
}

output "eks_oidc_provider_arn" {
  description = "EKS OIDC provider ARN"
  value       = module.eks.oidc_provider_arn
}
