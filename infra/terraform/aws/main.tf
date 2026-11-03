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
  backend "s3" {
    bucket         = "zambia-health-tfstate"
    key            = "aws/terraform.tfstate"
    region         = "af-south-1"
    encrypt        = true
    dynamodb_table = "zambia-health-tfstate-lock"
  }
}

locals {
  name        = "zambia-health"
  environment = var.environment
  region      = var.aws_region
  common_tags = {
    Project     = "UbuntuCare"
    Environment = var.environment
    Region      = "Zambia"
    ManagedBy   = "Terraform"
    Compliance  = "HIPAA"
    DataClass   = "PHI"
  }
  azs = slice(data.aws_availability_zones.available.names, 0, 3)
}

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_eks_cluster_auth" "cluster" {
  name = module.eks.cluster_name
}

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

# VPC
module "vpc" {
  source = "../modules/vpc"

  name            = local.name
  environment     = local.environment
  region          = local.region
  cidr_block      = var.vpc_cidr
  azs             = local.azs
  public_subnets  = var.public_subnet_cidrs
  private_subnets = var.private_subnet_cidrs
  tags            = local.common_tags
}

# EKS Cluster
module "eks" {
  source = "../modules/kubernetes"

  name                  = "${local.name}-${local.environment}"
  environment           = local.environment
  cluster_version       = "1.30"
  vpc_id                = module.vpc.vpc_id
  subnet_ids            = module.vpc.private_subnet_ids
  node_role_arn         = aws_iam_role.eks_node_role.arn
  node_security_group_id = aws_security_group.eks_nodes.id

  node_groups = {
    general = {
      name           = "general"
      instance_types = ["m6i.large", "m6a.large"]
      min_size       = 3
      max_size       = 9
      desired_size   = 3
      disk_size      = 100
      subnets        = module.vpc.private_subnet_ids
    }
    gpu = {
      name           = "gpu"
      instance_types = ["g5.xlarge", "p4d.24xlarge"]
      min_size       = 1
      max_size       = 6
      desired_size   = 1
      disk_size      = 500
      subnets        = module.vpc.private_subnet_ids
      gpu            = true
    }
    inference = {
      name           = "inference"
      instance_types = ["inf2.xlarge", "inf2.48xlarge"]
      min_size       = 1
      max_size       = 10
      desired_size   = 1
      disk_size      = 200
      subnets        = module.vpc.private_subnet_ids
    }
  }

  tags = local.common_tags
}

# RDS PostgreSQL with pgvector
module "database" {
  source = "../modules/database"

  name                    = "${local.name}-${local.environment}"
  environment             = local.environment
  engine                  = "postgres"
  engine_version          = "15.7"
  instance_class          = var.db_instance_class
  allocated_storage       = var.db_allocated_storage
  max_allocated_storage   = 1000
  db_name                 = "zambia_health"
  db_username             = var.db_username
  db_password             = var.db_password
  subnet_ids              = module.vpc.database_subnet_ids
  vpc_id                  = module.vpc.vpc_id
  publicly_accessible     = false
  storage_encrypted       = true
  deletion_protection     = true
  backup_retention_period = 35
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:05:00-sun:06:00"
  parameters = [
    { name = "shared_preload_libraries", value = "pgvector,pg_stat_statements" },
    { name = "pgvector.enable_prefilter", value = "1" },
    { name = "log_min_duration_statement", value = "1000" },
    { name = "random_page_cost", value = "1.1" },
    { name = "effective_cache_size", value = "80GB" },
  ]
  tags = local.common_tags
}

# ElastiCache Redis 7
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "${local.name}-${local.environment}"
  description                = "Redis cluster for ${local.name} ${local.environment}"
  engine                     = "redis"
  engine_version             = "7.1"
  node_type                  = var.redis_node_type
  num_cache_clusters         = 3
  parameter_group_family     = "redis7"
  port                       = 6379
  subnet_group_name          = aws_elasticache_subnet_group.redis.name
  security_group_ids         = [aws_security_group.redis.id]
  automatic_failover_enabled = true
  multi_az_enabled           = true
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  kms_key_id                 = aws_kms_key.redis.arn
  snapshot_retention_limit   = 7
  snapshot_window            = "05:00-06:00"
  auto_minor_version_upgrade = true

  log_delivery_configuration {
    destination_type = "cloudwatch-logs"
    destination      = aws_cloudwatch_log_group.redis.name
    log_format       = "json"
  }

  tags = merge(local.common_tags, { Name = "${local.name}-redis" })
}

resource "aws_elasticache_subnet_group" "redis" {
  name       = "${local.name}-${local.environment}-redis-subnet"
  subnet_ids = module.vpc.private_subnet_ids
}

# S3 Buckets
resource "aws_s3_bucket" "models" {
  bucket        = "${local.name}-${local.environment}-models"
  force_destroy = false
}

resource "aws_s3_bucket" "medical_images" {
  bucket        = "${local.name}-${local.environment}-medical-images"
  force_destroy = false
}

resource "aws_s3_bucket" "backups" {
  bucket        = "${local.name}-${local.environment}-backups"
  force_destroy = false
}

resource "aws_s3_bucket" "audit_logs" {
  bucket        = "${local.name}-${local.environment}-audit-logs"
  force_destroy = false
}

resource "aws_s3_bucket" "offline_sync" {
  bucket        = "${local.name}-${local.environment}-offline-sync"
  force_destroy = false
}

resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    id     = "transition-to-glacier"
    status = "Enabled"
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
    expiration {
      days = 365
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "audit_logs" {
  bucket = aws_s3_bucket.audit_logs.id

  rule {
    id     = "expire-audit-logs"
    status = "Enabled"
    expiration {
      days = 2555
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "all" {
  for_each = {
    models        = aws_s3_bucket.models.id
    medical_images = aws_s3_bucket.medical_images.id
    backups       = aws_s3_bucket.backups.id
    audit_logs    = aws_s3_bucket.audit_logs.id
    offline_sync  = aws_s3_bucket.offline_sync.id
  }

  bucket = each.value

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.s3.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "all" {
  for_each = {
    models        = aws_s3_bucket.models.id
    medical_images = aws_s3_bucket.medical_images.id
    backups       = aws_s3_bucket.backups.id
    audit_logs    = aws_s3_bucket.audit_logs.id
    offline_sync  = aws_s3_bucket.offline_sync.id
  }

  bucket = each.value

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Route53 DNS
resource "aws_route53_zone" "primary" {
  name = var.domain_name

  tags = local.common_tags
}

resource "aws_route53_record" "api" {
  zone_id = aws_route53_zone.primary.zone_id
  name    = "api.${var.domain_name}"
  type    = "A"
  alias {
    name                   = aws_lb.api.dns_name
    zone_id                = aws_lb.api.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "app" {
  zone_id = aws_route53_zone.primary.zone_id
  name    = "app.${var.domain_name}"
  type    = "A"
  alias {
    name                   = aws_cloudfront_distribution.main.domain_name
    zone_id                = aws_cloudfront_distribution.main.hosted_zone_id
    evaluate_target_health = false
  }
}

# CloudFront CDN
resource "aws_cloudfront_distribution" "main" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "CDN for ${local.name} ${local.environment}"
  default_root_object = "index.html"
  price_class         = "PriceClass_100"
  aliases             = ["app.${var.domain_name}"]

  origin {
    domain_name = aws_s3_bucket_website_configuration.frontend.bucket_regional_domain_name
    origin_id   = "frontend"
    origin_path = ""

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id       = "frontend"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 3600
    max_ttl     = 86400
  }

  ordered_cache_behavior {
    path_pattern           = "/api/*"
    target_origin_id       = "api"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true
    forwarded_values {
      query_string = true
      cookies {
        forward = "all"
      }
      headers = ["Authorization", "Content-Type", "X-API-Key"]
    }
    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
  }

  restrictions {
    geo_restriction {
      restriction_type = "whitelist"
      locations        = var.allowed_countries
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate.main.arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  logging_config {
    include_cookies = false
    bucket          = aws_s3_bucket.audit_logs.bucket_domain_name
    prefix          = "cloudfront/"
  }

  tags = local.common_tags
}

resource "aws_s3_bucket_website_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  index_document {
    suffix = "index.html"
  }
  error_document {
    key = "index.html"
  }
}

resource "aws_s3_bucket" "frontend" {
  bucket = "${local.name}-${local.environment}-frontend"
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  policy = data.aws_iam_policy_document.frontend_oai.json
}

data "aws_iam_policy_document" "frontend_oai" {
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.frontend.arn}/*"]
    principals {
      type        = "AWS"
      identifiers = [aws_cloudfront_origin_access_identity.main.iam_arn]
    }
  }
}

resource "aws_cloudfront_origin_access_identity" "main" {
  comment = "OAI for ${local.name} frontend"
}

# ACM Certificate (us-east-1 for CloudFront)
resource "aws_acm_certificate" "main" {
  provider                  = aws.useast1
  domain_name               = "*.${var.domain_name}"
  validation_method         = "DNS"
  subject_alternative_names = [var.domain_name]

  options {
    certificate_transparency_logging_preference = "ENABLED"
  }

  lifecycle {
    create_before_destroy = true
  }

  tags = local.common_tags
}

resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.main.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = aws_route53_zone.primary.zone_id
}

resource "aws_acm_certificate_validation" "main" {
  provider                = aws.useast1
  certificate_arn         = aws_acm_certificate.main.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

# WAF
resource "aws_wafv2_web_acl" "main" {
  name        = "${local.name}-${local.environment}-waf"
  description = "WAF for ${local.name} ${local.environment}"
  scope       = "REGIONAL"

  default_action {
    allow {}
  }

  rule {
    name     = "AWS-AWSManagedRulesCommonRuleSet"
    priority = 1
    override_action {
      none {}
    }
    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesCommonRuleSet"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesCommonRuleSet"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWS-AWSManagedRulesSQLiRuleSet"
    priority = 2
    override_action {
      none {}
    }
    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesSQLiRuleSet"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesSQLiRuleSet"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWS-AWSManagedRulesKnownBadInputsRuleSet"
    priority = 3
    override_action {
      none {}
    }
    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesKnownBadInputsRuleSet"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "rate-limit"
    priority = 10
    action {
      block {}
    }
    statement {
      rate_based_statement {
        limit              = 5000
        aggregate_key_type = "IP"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "RateLimit"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${local.name}-waf"
    sampled_requests_enabled   = true
  }

  tags = local.common_tags
}

resource "aws_wafv2_web_acl_association" "api" {
  resource_arn = aws_lb.api.arn
  web_acl_arn  = aws_wafv2_web_acl.main.arn
}

# ALB / Load Balancer
resource "aws_lb" "api" {
  name               = "${local.name}-${local.environment}-api"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = module.vpc.public_subnet_ids

  enable_deletion_protection = true
  enable_http2              = true
  idle_timeout              = 300

  access_logs {
    bucket  = aws_s3_bucket.audit_logs.id
    prefix  = "alb"
    enabled = true
  }

  tags = local.common_tags
}

resource "aws_lb_target_group" "api" {
  name        = "${local.name}-${local.environment}-api-tg"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 4
    timeout             = 10
    interval            = 30
    path                = "/health"
    port                = 3000
    matcher             = "200-399"
  }

  tags = local.common_tags
}

resource "aws_lb_listener" "api_https" {
  load_balancer_arn = aws_lb.api.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.api.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

resource "aws_lb_listener" "api_http_redirect" {
  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_acm_certificate" "api" {
  domain_name       = "api.${var.domain_name}"
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = local.common_tags
}

resource "aws_route53_record" "api_cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.api.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = aws_route53_zone.primary.zone_id
}

resource "aws_acm_certificate_validation" "api" {
  certificate_arn         = aws_acm_certificate.api.arn
  validation_record_fqdns = [for record in aws_route53_record.api_cert_validation : record.fqdn]
}

# ECR Repositories
resource "aws_ecr_repository" "services" {
  for_each = toset(var.ecr_repositories)

  name                 = "${local.name}-${local.environment}-${each.value}"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "KMS"
    kms_key         = aws_kms_key.ecr.arn
  }

  tags = local.common_tags
}

resource "aws_ecr_lifecycle_policy" "services" {
  for_each = aws_ecr_repository.services

  repository = each.value.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 production images"
        selection = {
          tagStatus   = "tagged"
          tagPrefixList = ["prod-"]
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Remove untagged images after 7 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countNumber = 7
          countUnit   = "days"
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# SNS / SQS
resource "aws_sns_topic" "alerts" {
  name              = "${local.name}-${local.environment}-alerts"
  kms_master_key_id = aws_kms_key.sns.arn

  tags = local.common_tags
}

resource "aws_sns_topic_subscription" "alerts_email" {
  for_each = toset(var.alert_emails)
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = each.value
}

resource "aws_sqs_queue" "notifications" {
  name                       = "${local.name}-${local.environment}-notifications"
  delay_seconds              = 0
  max_message_size           = 262144
  message_retention_seconds  = 86400
  receive_wait_time_seconds  = 10
  visibility_timeout_seconds = 120

  kms_master_key_id                 = aws_kms_key.sqs.arn
  kms_data_key_reuse_period_seconds = 300

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.notifications_dlq.arn
    maxReceiveCount     = 3
  })

  tags = local.common_tags
}

resource "aws_sqs_queue" "notifications_dlq" {
  name                      = "${local.name}-${local.environment}-notifications-dlq"
  message_retention_seconds = 1209600

  kms_master_key_id                 = aws_kms_key.sqs.arn
  kms_data_key_reuse_period_seconds = 300

  tags = local.common_tags
}

resource "aws_sqs_queue_policy" "notifications" {
  queue_url = aws_sqs_queue.notifications.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "sns.amazonaws.com"
        }
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.notifications.arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = aws_sns_topic.alerts.arn
          }
        }
      }
    ]
  })
}

resource "aws_sns_topic_subscription" "notifications_sqs" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.notifications.arn
}

# CloudWatch Logs
resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/eks/${local.name}-${local.environment}/api"
  retention_in_days = 90
  kms_key_id        = aws_kms_key.cloudwatch.arn
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "redis" {
  name              = "/aws/elasticache/${local.name}-${local.environment}/redis"
  retention_in_days = 30
  kms_key_id        = aws_kms_key.cloudwatch.arn
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "database" {
  name              = "/aws/rds/${local.name}-${local.environment}/postgres"
  retention_in_days = 30
  kms_key_id        = aws_kms_key.cloudwatch.arn
  tags              = local.common_tags
}

resource "aws_cloudwatch_log_group" "waf" {
  name              = "/aws/waf/${local.name}-${local.environment}"
  retention_in_days = 30
  kms_key_id        = aws_kms_key.cloudwatch.arn
  tags              = local.common_tags
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "eks_cpu" {
  alarm_name          = "${local.name}-${local.environment}-eks-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 5
  metric_name         = "node_cpu_utilization"
  namespace           = "ContainerInsights"
  period              = 60
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "EKS cluster CPU utilization high"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    ClusterName = module.eks.cluster_name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "rds_connections" {
  alarm_name          = "${local.name}-${local.environment}-rds-connections"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = 60
  statistic           = "Average"
  threshold           = 100
  alarm_description   = "RDS database connections high"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    DBInstanceIdentifier = module.database.identifier
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "redis_cpu" {
  alarm_name          = "${local.name}-${local.environment}-redis-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = 60
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Redis CPU utilization high"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    CacheClusterId = aws_elasticache_replication_group.redis.id
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "alb_5xx" {
  alarm_name          = "${local.name}-${local.environment}-alb-5xx"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "ALB 5xx errors high"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    LoadBalancer = aws_lb.api.arn_suffix
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${local.name}-${local.environment}"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "TargetResponseTime", { LoadBalancer = aws_lb.api.arn_suffix }],
            [".", "RequestCount", "."],
            [".", "HTTPCode_Target_2XX_Count", "."],
            [".", "HTTPCode_Target_5XX_Count", "."]
          ]
          period = 300
          stat   = "Average"
          region = local.region
          title  = "API Load Balancer"
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["ContainerInsights", "node_cpu_utilization", { ClusterName = module.eks.cluster_name }],
            [".", "node_memory_utilization", "."]
          ]
          period = 300
          stat   = "Average"
          region = local.region
          title  = "EKS Cluster"
        }
      }
    ]
  })
}

# Backup Vault
resource "aws_backup_vault" "main" {
  name        = "${local.name}-${local.environment}-backup-vault"
  kms_key_arn = aws_kms_key.backup.arn

  tags = local.common_tags
}

resource "aws_backup_plan" "main" {
  name = "${local.name}-${local.environment}-backup-plan"

  rule {
    rule_name         = "daily"
    target_vault_name = aws_backup_vault.main.name
    schedule          = "cron(0 2 * * ? *)"
    start_window      = 60
    completion_window = 360
    lifecycle {
      delete_after = 90
    }
    recovery_point_tags = local.common_tags
  }

  rule {
    rule_name         = "weekly"
    target_vault_name = aws_backup_vault.main.name
    schedule          = "cron(0 3 * * SUN *)"
    start_window      = 60
    completion_window = 360
    lifecycle {
      delete_after = 365
    }
    recovery_point_tags = local.common_tags
  }

  tags = local.common_tags
}

resource "aws_backup_selection" "main" {
  name         = "${local.name}-${local.environment}-backup-selection"
  plan_id      = aws_backup_plan.main.id
  iam_role_arn = aws_iam_role.backup.arn

  resources = concat(
    [module.database.arn],
    [for repo in aws_ecr_repository.services : repo.arn],
    [aws_elasticache_replication_group.redis.arn],
    [aws_s3_bucket.backups.arn]
  )
}

# Provider configuration
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

provider "aws" {
  alias  = "useast1"
  region = "us-east-1"

  default_tags {
    tags = local.common_tags
  }
}
