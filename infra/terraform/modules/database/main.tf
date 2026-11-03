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
  description = "Base name for the database"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "engine" {
  description = "Database engine (postgres, mysql, etc.)"
  type        = string
  default     = "postgres"
}

variable "engine_version" {
  description = "Database engine version"
  type        = string
  default     = "15.7"
}

variable "instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.r6g.large"
}

variable "allocated_storage" {
  description = "Allocated storage in GB"
  type        = number
  default     = 200
}

variable "max_allocated_storage" {
  description = "Maximum allocated storage in GB"
  type        = number
  default     = 1000
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "appdb"
}

variable "db_username" {
  description = "Database master username"
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "Database master password"
  type        = string
  sensitive   = true
}

variable "subnet_ids" {
  description = "Subnet IDs for the DB subnet group"
  type        = list(string)
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "publicly_accessible" {
  description = "Whether the DB is publicly accessible"
  type        = bool
  default     = false
}

variable "storage_encrypted" {
  description = "Enable storage encryption"
  type        = bool
  default     = true
}

variable "deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = true
}

variable "backup_retention_period" {
  description = "Backup retention period in days"
  type        = number
  default     = 35
}

variable "backup_window" {
  description = "Daily backup window"
  type        = string
  default     = "03:00-04:00"
}

variable "maintenance_window" {
  description = "Weekly maintenance window"
  type        = string
  default     = "sun:05:00-sun:06:00"
}

variable "parameters" {
  description = "List of DB parameter overrides"
  type = list(object({
    name  = string
    value = string
  }))
  default = []
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}

variable "kms_key_id" {
  description = "KMS key ID for encryption"
  type        = string
  default     = null
}

variable "multi_az" {
  description = "Enable Multi-AZ deployment"
  type        = bool
  default     = true
}

locals {
  identifier = "${var.name}-${var.environment}"
  db_name = var.db_name
}

# DB Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "${local.identifier}-subnet-group"
  subnet_ids = var.subnet_ids

  tags = merge(var.tags, {
    Name = "${local.identifier}-subnet-group"
  })
}

# DB Parameter Group
resource "aws_db_parameter_group" "main" {
  name        = "${local.identifier}-pg"
  family      = "postgres15"
  description = "Parameter group for ${local.identifier}"

  dynamic "parameter" {
    for_each = var.parameters
    content {
      name         = parameter.value.name
      value        = parameter.value.value
      apply_method = "immediate"
    }
  }

  tags = merge(var.tags, {
    Name = "${local.identifier}-pg"
  })
}

# Option Group
resource "aws_db_option_group" "main" {
  name                     = "${local.identifier}-og"
  engine_name              = var.engine
  major_engine_version     = regex("^\\d+", var.engine_version)[0]
  option_group_description = "Option group for ${local.identifier}"

  tags = merge(var.tags, {
    Name = "${local.identifier}-og"
  })
}

# RDS Instance
resource "aws_db_instance" "main" {
  identifier = local.identifier

  engine                     = var.engine
  engine_version             = var.engine_version
  instance_class             = var.instance_class
  allocated_storage          = var.allocated_storage
  max_allocated_storage      = var.max_allocated_storage
  storage_type              = "gp3"
  storage_encrypted         = var.storage_encrypted
  kms_key_id                = var.kms_key_id

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password
  port     = 5432

  db_subnet_group_name   = aws_db_subnet_group.main.name
  parameter_group_name   = aws_db_parameter_group.main.name
  option_group_name      = aws_db_option_group.main.name
  vpc_security_group_ids = [aws_security_group.main.id]

  publicly_accessible    = var.publicly_accessible
  multi_az              = var.multi_az

  backup_retention_period = var.backup_retention_period
  backup_window           = var.backup_window
  maintenance_window      = var.maintenance_window
  copy_tags_to_snapshot   = true

  deletion_protection = var.deletion_protection
  skip_final_snapshot = false
  final_snapshot_identifier = "${local.identifier}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"

  auto_minor_version_upgrade = true
  monitoring_interval        = 60
  monitoring_role_arn        = aws_iam_role.monitoring.arn

  enabled_cloudwatch_logs_exports = [
    "postgresql",
    "upgrade",
  ]

  performance_insights_enabled          = true
  performance_insights_retention_period = 7
  performance_insights_kms_key_id       = var.kms_key_id

  tags = merge(var.tags, {
    Name = local.identifier
  })

  lifecycle {
    ignore_changes = [
      password,
    ]
  }
}

# Read Replica
resource "aws_db_instance" "read_replica" {
  count = var.multi_az ? 1 : 0

  identifier = "${local.identifier}-read"

  engine                     = var.engine
  engine_version             = var.engine_version
  instance_class             = var.instance_class
  allocated_storage          = var.allocated_storage
  storage_type              = "gp3"
  storage_encrypted         = var.storage_encrypted
  kms_key_id                = var.kms_key_id

  port            = 5432
  replicate_source_db = aws_db_instance.main.identifier

  vpc_security_group_ids = [aws_security_group.main.id]

  publicly_accessible = var.publicly_accessible

  backup_retention_period = 0
  backup_window           = var.backup_window
  maintenance_window      = var.maintenance_window
  copy_tags_to_snapshot   = true

  auto_minor_version_upgrade = true
  monitoring_interval        = 60
  monitoring_role_arn        = aws_iam_role.monitoring.arn

  performance_insights_enabled          = true
  performance_insights_retention_period = 7
  performance_insights_kms_key_id       = var.kms_key_id

  tags = merge(var.tags, {
    Name = "${local.identifier}-read"
  })
}

# Security Group
resource "aws_security_group" "main" {
  name        = "${local.identifier}-db-sg"
  description = "Security group for ${local.identifier} RDS"
  vpc_id      = var.vpc_id

  ingress {
    description = "PostgreSQL from VPC"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.main.cidr_block]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${local.identifier}-db-sg"
  })
}

data "aws_vpc" "main" {
  id = var.vpc_id
}

# IAM Role for Enhanced Monitoring
resource "aws_iam_role" "monitoring" {
  name = "${local.identifier}-monitoring-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "monitoring" {
  role       = aws_iam_role.monitoring.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

data "aws_partition" "current" {}

# Outputs
output "identifier" {
  value = aws_db_instance.main.identifier
}

output "arn" {
  value = aws_db_instance.main.arn
}

output "endpoint" {
  value = aws_db_instance.main.endpoint
}

output "reader_endpoint" {
  value = var.multi_az ? aws_db_instance.read_replica[0].endpoint : aws_db_instance.main.endpoint
}

output "port" {
  value = 5432
}

output "db_name" {
  value = var.db_name
}

output "db_username" {
  value = var.db_username
  sensitive = true
}

output "security_group_id" {
  value = aws_security_group.main.id
}

output "subnet_group_name" {
  value = aws_db_subnet_group.main.name
}

output "parameter_group_name" {
  value = aws_db_parameter_group.main.name
}
