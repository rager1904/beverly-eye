variable "environment" {
  description = "Deployment environment (prod, staging, dev)"
  type        = string
  default     = "prod"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Must be dev, staging, or prod"
  }
}

variable "aws_region" {
  description = "AWS region for deployment (af-south-1 for Cape Town, closest to Zambia)"
  type        = string
  default     = "af-south-1"
  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-\\d+$", var.aws_region))
    error_message = "Must be a valid AWS region identifier"
  }
}

variable "domain_name" {
  description = "Primary domain name for the platform"
  type        = string
  default     = "zambia-health.example.com"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDR blocks (one per AZ)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "private_subnet_cidrs" {
  description = "Private subnet CIDR blocks (one per AZ)"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24", "10.0.12.0/24"]
}

variable "database_subnet_cidrs" {
  description = "Database subnet CIDR blocks (one per AZ)"
  type        = list(string)
  default     = ["10.0.20.0/24", "10.0.21.0/24", "10.0.22.0/24"]
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.r6g.large"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 200
}

variable "db_username" {
  description = "RDS master username"
  type        = string
  default     = "zambia_health_admin"
  sensitive   = true
}

variable "db_password" {
  description = "RDS master password"
  type        = string
  sensitive   = true
}

variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.r6g.large"
}

variable "allowed_countries" {
  description = "ISO country codes allowed by CloudFront geo-restriction"
  type        = list(string)
  default     = ["ZM", "ZA", "BW", "MZ", "TZ", "MW", "CD", "NA", "ZW"]
}

variable "alert_emails" {
  description = "Email addresses for CloudWatch alarm notifications"
  type        = list(string)
  default     = ["ops@zambia-health.example.com"]
}

variable "ecr_repositories" {
  description = "List of ECR repository names"
  type        = list(string)
  default     = [
    "api-gateway",
    "patient-service",
    "clinical-service",
    "imaging-service",
    "ai-inference",
    "sync-service",
    "notification-service",
    "auth-service",
    "audit-service",
    "offline-agent",
  ]
}

variable "kms_deletion_window" {
  description = "KMS key deletion window in days"
  type        = number
  default     = 30
}

variable "enable_nat_gateway" {
  description = "Enable NAT Gateway for private subnets"
  type        = bool
  default     = true
}

variable "enable_vpn_gateway" {
  description = "Enable VPN Gateway for secure admin access"
  type        = bool
  default     = true
}

variable "enable_flow_logs" {
  description = "Enable VPC Flow Logs for network audit"
  type        = bool
  default     = true
}

variable "eks_node_ami_type" {
  description = "EKS node AMI type (AL2_x86_64, AL2_x86_64_GPU, BOTTLEROCKET_x86_64, etc.)"
  type        = string
  default     = "AL2_x86_64_GPU"
}

variable "eks_kubernetes_version" {
  description = "EKS cluster Kubernetes version"
  type        = string
  default     = "1.30"
}

variable "cluster_autoscaler_enabled" {
  description = "Enable Cluster Autoscaler add-on"
  type        = bool
  default     = true
}

variable "ingress_nginx_enabled" {
  description = "Enable NGINX Ingress Controller"
  type        = bool
  default     = true
}

variable "metrics_server_enabled" {
  description = "Enable Metrics Server add-on"
  type        = bool
  default     = true
}
