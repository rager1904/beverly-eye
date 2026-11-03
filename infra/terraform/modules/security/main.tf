terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "name" {
  description = "Base name for security resources"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "allowed_ssh_cidrs" {
  description = "CIDR blocks allowed for SSH"
  type        = list(string)
  default     = ["10.0.0.0/8"]
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}

locals {
  name = "${var.name}-${var.environment}"
}

# KMS Key
resource "aws_kms_key" "main" {
  description             = "KMS key for ${local.name}"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  multi_region            = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EnableRootAccess"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      }
    ]
  })

  tags = merge(var.tags, {
    Name = "${local.name}-kms"
  })
}

resource "aws_kms_alias" "main" {
  name          = "alias/${local.name}"
  target_key_id = aws_kms_key.main.key_id
}

# Bastion Security Group
resource "aws_security_group" "bastion" {
  name        = "${local.name}-bastion-sg"
  description = "Security group for bastion host"
  vpc_id      = var.vpc_id

  ingress {
    description = "SSH from allowed CIDRs"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidrs
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${local.name}-bastion-sg"
  })
}

# Internal Security Group
resource "aws_security_group" "internal" {
  name        = "${local.name}-internal-sg"
  description = "Internal security group - allows all traffic within security group"
  vpc_id      = var.vpc_id

  ingress {
    description = "All internal traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    self        = true
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${local.name}-internal-sg"
  })
}

# IAM Password Policy
resource "aws_iam_account_password_policy" "main" {
  minimum_password_length      = 14
  require_lowercase_characters = true
  require_uppercase_characters = true
  require_numbers              = true
  require_symbols              = true
  allow_users_to_change_password = true
  max_password_age            = 90
  password_reuse_prevention   = 24
  hard_expiry                 = false
}

# Config recording
resource "aws_config_configuration_recorder" "main" {
  name     = "${local.name}-config-recorder"
  role_arn = aws_iam_role.config.arn

  recording_group {
    all_supported                 = true
    include_global_resource_types = true
  }
}

resource "aws_config_delivery_channel" "main" {
  name           = "${local.name}-config-delivery"
  s3_bucket_name = var.config_bucket_name
  sns_topic_arn  = var.config_sns_topic_arn

  snapshot_delivery_properties {
    delivery_frequency = "One_Hour"
  }

  depends_on = [aws_config_configuration_recorder.main]
}

resource "aws_iam_role" "config" {
  name = "${local.name}-config-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "config.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "config" {
  role       = aws_iam_role.config.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSConfigRole"
}

# GuardDuty
resource "aws_guardduty_detector" "main" {
  enable = true
  datasources {
    s3_logs {
      enable = true
    }
    kubernetes {
      audit_logs {
        enable = true
      }
    }
    malware_protection {
      scan_ec2_instance_with_findings {
        ebs_volumes {
          enable = true
        }
      }
    }
  }

  tags = var.tags
}

# Security Hub
resource "aws_securityhub_account" "main" {
  enable_default_standards = true

  control_finding_generator = "SECURITY_CONTROL"
}

resource "aws_securityhub_standards_subscription" "cis" {
  standards_arn = "arn:aws:securityhub:${var.aws_region}::standards/cis-aws-foundations-benchmark/v/1.4.0"
}

resource "aws_securityhub_standards_subscription" "pci" {
  standards_arn = "arn:aws:securityhub:${var.aws_region}::standards/pci-dss/v/3.2.1"
}

resource "aws_securityhub_standards_subscription" "hipaa" {
  standards_arn = "arn:aws:securityhub:${data.aws_partition.current.partition}::standards/hipaa/v/1.0.0"
}

# Variables
variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "config_bucket_name" {
  description = "S3 bucket for AWS Config"
  type        = string
}

variable "config_sns_topic_arn" {
  description = "SNS topic for AWS Config notifications"
  type        = string
  default     = ""
}

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

# Outputs
output "kms_key_id" {
  value = aws_kms_key.main.key_id
}

output "kms_key_arn" {
  value = aws_kms_key.main.arn
}

output "guardduty_detector_id" {
  value = aws_guardduty_detector.main.id
}

output "securityhub_account_id" {
  value = aws_securityhub_account.main.id
}

output "bastion_security_group_id" {
  value = aws_security_group.bastion.id
}

output "internal_security_group_id" {
  value = aws_security_group.internal.id
}
