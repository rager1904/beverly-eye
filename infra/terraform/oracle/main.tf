terraform {
  required_version = ">= 1.6"
  required_providers {
    oci = {
      source  = "hashicorp/oci"
      version = "~> 5.40"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
  backend "s3" {
    bucket = "zambia-health-tfstate"
    key    = "oracle/terraform.tfstate"
    region = "af-johannesburg-1"
    endpoints = {
      s3 = "https://${var.bucket_namespace}.compat.objectstorage.af-johannesburg-1.oraclecloud.com"
    }
    skip_region_validation      = true
    skip_credentials_validation = true
    skip_metadata_api_check     = true
    force_path_style            = true
  }
}

provider "oci" {
  region = var.oci_region
}

locals {
  name        = "zambia-health"
  environment = var.environment
  common_tags = {
    Project     = "UbuntuCare"
    Environment = var.environment
    Region      = "Zambia"
    ManagedBy   = "Terraform"
    Compliance  = "HIPAA"
    DataClass   = "PHI"
  }
  ssh_public_key_path = var.ssh_public_key_path
}

# VCN
resource "oci_core_virtual_network" "main" {
  cidr_block     = var.vcn_cidr
  compartment_id = var.compartment_ocid
  display_name   = "${local.name}-${local.environment}-vcn"
  dns_label      = "${local.name}${local.environment}"

  defined_tags = local.common_tags
}

resource "oci_core_subnet" "oke" {
  cidr_block        = var.oke_subnet_cidr
  compartment_id    = var.compartment_ocid
  vcn_id            = oci_core_virtual_network.main.id
  display_name      = "${local.name}-${local.environment}-oke-subnet"
  dns_label         = "oke"
  security_list_ids = [oci_core_security_list.oke.id]
  route_table_id    = oci_core_route_table.oke.id
  dhcp_options_id   = oci_core_virtual_network.main.dhcp_options_id

  prohibit_public_ip_on_vnic = true
}

resource "oci_core_subnet" "public" {
  cidr_block        = var.public_subnet_cidr
  compartment_id    = var.compartment_ocid
  vcn_id            = oci_core_virtual_network.main.id
  display_name      = "${local.name}-${local.environment}-public-subnet"
  dns_label         = "public"
  security_list_ids = [oci_core_security_list.public.id]
  route_table_id    = oci_core_route_table.public.id
  dhcp_options_id   = oci_core_virtual_network.main.dhcp_options_id
}

resource "oci_core_subnet" "database" {
  cidr_block        = var.database_subnet_cidr
  compartment_id    = var.compartment_ocid
  vcn_id            = oci_core_virtual_network.main.id
  display_name      = "${local.name}-${local.environment}-db-subnet"
  dns_label         = "database"
  security_list_ids = [oci_core_security_list.database.id]
  route_table_id    = oci_core_route_table.oke.id
  dhcp_options_id   = oci_core_virtual_network.main.dhcp_options_id

  prohibit_public_ip_on_vnic = true
}

# Internet Gateway
resource "oci_core_internet_gateway" "main" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_virtual_network.main.id
  display_name   = "${local.name}-${local.environment}-igw"
  enabled        = true
}

# NAT Gateway
resource "oci_core_nat_gateway" "main" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_virtual_network.main.id
  display_name   = "${local.name}-${local.environment}-nat"
}

# Route Tables
resource "oci_core_route_table" "public" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_virtual_network.main.id
  display_name   = "${local.name}-${local.environment}-public-rt"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.main.id
  }
}

resource "oci_core_route_table" "oke" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_virtual_network.main.id
  display_name   = "${local.name}-${local.environment}-oke-rt"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_nat_gateway.main.id
  }
}

# Security Lists
resource "oci_core_security_list" "oke" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_virtual_network.main.id
  display_name   = "${local.name}-${local.environment}-oke-sl"

  egress_security_rules {
    destination = "0.0.0.0/0"
    protocol    = "all"
  }

  ingress_security_rules {
    protocol = "6"
    source   = var.vcn_cidr
  }

  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    tcp_options {
      destination_port_range {
        min = 443
        max = 443
      }
    }
  }
}

resource "oci_core_security_list" "public" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_virtual_network.main.id
  display_name   = "${local.name}-${local.environment}-public-sl"

  egress_security_rules {
    destination = "0.0.0.0/0"
    protocol    = "all"
  }

  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    tcp_options {
      destination_port_range {
        min = 443
        max = 443
      }
    }
  }

  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    tcp_options {
      destination_port_range {
        min = 80
        max = 80
      }
    }
  }
}

resource "oci_core_security_list" "database" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_virtual_network.main.id
  display_name   = "${local.name}-${local.environment}-db-sl"

  egress_security_rules {
    destination = "0.0.0.0/0"
    protocol    = "all"
  }

  ingress_security_rules {
    protocol = "6"
    source   = var.vcn_cidr
    tcp_options {
      destination_port_range {
        min = 5432
        max = 5432
      }
    }
  }
}

# OKE Cluster
resource "oci_containerengine_cluster" "main" {
  name             = "${local.name}-${local.environment}"
  compartment_id   = var.compartment_ocid
  vcn_id           = oci_core_virtual_network.main.id
  kubernetes_version = var.oke_version
  type             = "CLUSTER"
  endpoint_subnet_id = oci_core_subnet.public.id

  options {
    service_lb_subnet_ids = [oci_core_subnet.public.id]
    kubernetes_network_config {
      pods_cidr     = var.pods_cidr
      services_cidr = var.services_cidr
    }
    add_ons {
      kubernetes_dashboard = false
      tiller               = false
    }
    admission_controller_options {
      pod_security_policy_enabled = false
    }
  }

  image_policy_config {
    is_policy_enabled = true
  }

  defined_tags = local.common_tags
}

resource "oci_containerengine_node_pool" "general" {
  name             = "general"
  compartment_id   = var.compartment_ocid
  cluster_id       = oci_containerengine_cluster.main.id
  kubernetes_version = var.oke_version
  node_source_details {
    source_type = "IMAGE"
    image_id    = data.oci_core_images.oke.images[0].id
  }
  node_shape = var.general_node_shape
  node_config_details {
    size = var.system_node_count
    placement_configs {
      availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
      subnet_id           = oci_core_subnet.oke.id
    }
    placement_configs {
      availability_domain = data.oci_identity_availability_domains.ads.availability_domains[1].name
      subnet_id           = oci_core_subnet.oke.id
    }
  }
  node_metadata = {
    user_data = base64encode(templatefile("${path.module}/templates/node_bootstrap.sh", {
      role = "general"
    }))
  }
  node_source_details {
    source_type = "IMAGE"
    image_id    = data.oci_core_images.oke.images[0].id
  }
  ssh_public_key = file(local.ssh_public_key_path)

  defined_tags = local.common_tags
}

resource "oci_containerengine_node_pool" "gpu" {
  name             = "gpu"
  compartment_id   = var.compartment_ocid
  cluster_id       = oci_containerengine_cluster.main.id
  kubernetes_version = var.oke_version
  node_shape = var.gpu_node_shape

  node_config_details {
    size = var.gpu_node_count
    placement_configs {
      availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
      subnet_id           = oci_core_subnet.oke.id
    }
  }

  node_shape_config {
    ocpus         = var.gpu_ocpus
    memory_in_gbs = var.gpu_memory_gb
  }

  node_metadata = {
    user_data = base64encode(templatefile("${path.module}/templates/gpu_bootstrap.sh", {
      nvidia_driver_version = "550"
    }))
  }

  node_source_details {
    source_type = "IMAGE"
    image_id    = data.oci_core_images.gpu.images[0].id
  }
  ssh_public_key = file(local.ssh_public_key_path)

  node_labels = {
    "nvidia.com/gpu" = "true"
  }

  defined_tags = local.common_tags
}

# Autonomous Database
resource "oci_database_autonomous_database" "main" {
  compartment_id           = var.compartment_ocid
  db_name                  = "ZAMBIAHEALTH"
  display_name             = "${local.name}-${local.environment}"
  db_workload              = "OLTP"
  is_free_tier             = false
  db_version               = var.adb_version
  license_model            = "LICENSE_INCLUDED"
  compute_model            = "ECPU"
  compute_count            = var.adb_compute_count
  storage_management       = "AUTOMATIC"
  data_storage_size_in_tbs = var.adb_storage_tb
  is_auto_scaling_enabled  = true
  is_auto_scaling_for_storage_enabled = true
  is_dedicated             = false
  subnet_id                = oci_core_subnet.database.id
  nsg_ids                  = [oci_core_network_security_group.database.id]
  private_endpoint_label   = "${local.name}-${local.environment}-adb"
  kms_key_id               = oci_kms_key.adb.id
  vault_id                 = oci_kms_vault.main.id

  admin_password = var.db_password

  license_model = "LICENSE_INCLUDED"

  customer_contacts {
    email = var.alert_email
  }

  defined_tags = local.common_tags

  lifecycle {
    prevent_destroy = true
  }
}

# Object Storage
resource "oci_objectstorage_bucket" "models" {
  compartment_id = var.compartment_ocid
  name           = "${local.name}-${local.environment}-models"
  namespace      = var.object_storage_namespace
  access_type    = "NoPublicAccess"
  storage_tier   = "Standard"
  versioning     = "Enabled"
  kms_key_id     = oci_kms_key.object_storage.id
  object_events_enabled = true

  defined_tags = local.common_tags
}

resource "oci_objectstorage_bucket" "medical_images" {
  compartment_id = var.compartment_ocid
  name           = "${local.name}-${local.environment}-medical-images"
  namespace      = var.object_storage_namespace
  access_type    = "NoPublicAccess"
  storage_tier   = "Standard"
  versioning     = "Enabled"
  kms_key_id     = oci_kms_key.object_storage.id
  object_events_enabled = true

  defined_tags = local.common_tags
}

resource "oci_objectstorage_bucket" "backups" {
  compartment_id = var.compartment_ocid
  name           = "${local.name}-${local.environment}-backups"
  namespace      = var.object_storage_namespace
  access_type    = "NoPublicAccess"
  storage_tier   = "Archive"
  versioning     = "Enabled"
  kms_key_id     = oci_kms_key.object_storage.id

  defined_tags = local.common_tags
}

resource "oci_objectstorage_bucket" "audit_logs" {
  compartment_id = var.compartment_ocid
  name           = "${local.name}-${local.environment}-audit-logs"
  namespace      = var.object_storage_namespace
  access_type    = "NoPublicAccess"
  storage_tier   = "Standard"
  versioning     = "Enabled"
  kms_key_id     = oci_kms_key.object_storage.id
  object_events_enabled = true

  defined_tags = local.common_tags
}

# KMS
resource "oci_kms_vault" "main" {
  compartment_id = var.compartment_ocid
  display_name   = "${local.name}-${local.environment}-vault"
  vault_type     = "DEFAULT"
  is_primary     = true

  defined_tags = local.common_tags
}

resource "oci_kms_key" "adb" {
  compartment_id = var.compartment_ocid
  display_name   = "${local.name}-${local.environment}-adb-key"
  key_shape {
    algorithm = "AES"
    length    = 32
  }
  management_endpoint = oci_kms_vault.main.management_endpoint
}

resource "oci_kms_key" "object_storage" {
  compartment_id = var.compartment_ocid
  display_name   = "${local.name}-${local.environment}-os-key"
  key_shape {
    algorithm = "AES"
    length    = 32
  }
  management_endpoint = oci_kms_vault.main.management_endpoint
}

# Network Security Group
resource "oci_core_network_security_group" "database" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_virtual_network.main.id
  display_name   = "${local.name}-${local.environment}-db-nsg"
}

resource "oci_core_network_security_group_security_rule" "database_ingress" {
  network_security_group_id = oci_core_network_security_group.database.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = var.vcn_cidr
  source_type               = "CIDR_BLOCK"
  tcp_options {
    destination_port_range {
      min = 5432
      max = 5432
    }
  }
}

# WAF (Web Application Firewall)
resource "oci_waa_web_app_acceleration_policy" "main" {
  compartment_id = var.compartment_ocid
  display_name   = "${local.name}-${local.environment}-waa-policy"

  origin_groups {
    name = "oke-origin"
    origins {
      uri    = "http://${oci_load_balancer.main.ip_address}:80"
      weight = 1
    }
  }

  response_caching_policy {
    is_response_header_based_caching_enabled = true
  }

  compression_policy {
    gzip_compression {
      is_enabled = true
    }
  }

  defined_tags = local.common_tags
}

resource "oci_waf_web_app_firewall" "main" {
  backend_type              = "LOAD_BALANCER"
  compartment_id            = var.compartment_ocid
  load_balancer_id          = oci_load_balancer.main.id
  web_app_firewall_policy_id = oci_waf_web_app_firewall_policy.main.id
}

resource "oci_waf_web_app_firewall_policy" "main" {
  compartment_id = var.compartment_ocid
  display_name   = "${local.name}-${local.environment}-waf-policy"

  actions {
    type = "CHECK"
    name = "DefaultAction"
    code = 403
    body {
      template = "{\"error\":\"Forbidden\"}"
    }
    headers {
      name  = "Content-Type"
      value = "application/json"
    }
  }

  request_access_control {
    default_action_name = "DefaultAction"
    rules {
      action_name = "DefaultAction"
      condition   = "not contains(request.headers['authorization'], 'Bearer')"
      name        = "RequireAuth"
      type        = "ACCESS_CONTROL"
    }
  }

  request_protection {
    rules {
      action_name = "DefaultAction"
      name        = "BlockSQLi"
      type        = "PROTECTION"
      protection_capabilities {
        key                  = "942100"
        version              = 2
        exclusion_tag        = "OWASP_CRS"
        action_name          = "DefaultAction"
        collaborative_action_threshold = 3
      }
      protection_capabilities {
        key                  = "933210"
        version              = 2
        exclusion_tag        = "OWASP_CRS"
        action_name          = "DefaultAction"
      }
    }
  }

  rate_limiting {
    rules {
      name              = "RateLimitAPI"
      type              = "RATE_LIMIT"
      action_name       = "DefaultAction"
      condition         = "starts_with(request.url.path, '/api/')"
      config {
        period_in_seconds = 60
        requests_limit    = 1000
      }
    }
  }

  defined_tags = local.common_tags
}

# Load Balancer
resource "oci_load_balancer" "main" {
  compartment_id             = var.compartment_ocid
  display_name               = "${local.name}-${local.environment}-lb"
  shape                      = "flexible"
  shape_details {
    minimum_bandwidth_in_mbps = 10
    maximum_bandwidth_in_mbps = 1000
  }
  subnet_ids                 = [oci_core_subnet.public.id]
  is_private                 = false

  defined_tags = local.common_tags
}

resource "oci_load_balancer_backend_set" "api" {
  name             = "api"
  load_balancer_id = oci_load_balancer.main.id
  policy           = "ROUND_ROBIN"
  health_checker {
    protocol          = "HTTP"
    port              = 3000
    url_path          = "/health"
    interval_ms       = 30000
    timeout_in_millis = 10000
    retries           = 3
  }
}

resource "oci_load_balancer_listener" "api_https" {
  load_balancer_id         = oci_load_balancer.main.id
  name                     = "https"
  default_backend_set_name = oci_load_balancer_backend_set.api.name
  port                     = 443
  protocol                 = "HTTP"
  ssl_configuration {
    certificate_name        = oci_load_balancer_certificate.main.certificate_name
    protocols               = ["TLSv1.2"]
    cipher_suite_name       = "OCI-DEFAULT-COMPATIBLE-CIPHER-SUITE"
    server_order_preference = "ENABLED"
  }
}

resource "oci_load_balancer_certificate" "main" {
  load_balancer_id   = oci_load_balancer.main.id
  certificate_name   = "${local.name}-${local.environment}-cert"
  ca_certificate     = var.lb_certificate_ca
  public_certificate = var.lb_certificate
  private_key        = var.lb_certificate_key
}

# Logging
resource "oci_logging_log_group" "main" {
  compartment_id = var.compartment_ocid
  display_name   = "${local.name}-${local.environment}-log-group"

  defined_tags = local.common_tags
}

resource "oci_logging_log" "oke" {
  display_name   = "${local.name}-${local.environment}-oke-logs"
  log_group_id   = oci_logging_log_group.main.id
  log_type       = "SERVICE"
  source_type    = "OKE"
  source_resource = oci_containerengine_cluster.main.id

  configuration {
    source {
      category    = "all"
      resource    = oci_containerengine_cluster.main.id
      service     = "oke"
      source_type = "OCISERVICE"
    }
    compartment_id = var.compartment_ocid
  }

  is_enabled = true
  retention_duration = "30"

  defined_tags = local.common tags
}

# Monitoring / Alarms
resource "oci_monitoring_alarm" "oke_cpu" {
  compartment_id    = var.compartment_ocid
  display_name      = "${local.name}-${local.environment}-oke-cpu-high"
  metric_compartment_id = var.compartment_ocid
  namespace         = "oke"
  metric            = "cpu_utilization"
  query             = "cpu_utilization[1m].mean() > 80"
  severity          = "CRITICAL"
  body              = "OKE CPU utilization exceeded 80%"
  destinations      = [oci_ons_topic.alerts.id]
  is_enabled        = true
  repeat_duration   = "00:05:00"
  suppression {
    time_suppress_from = "2024-01-01T00:00:00.000Z"
    time_suppress_until = "2024-12-31T23:59:59.000Z"
  }
}

# Notifications
resource "oci_ons_topic" "alerts" {
  compartment_id = var.compartment_ocid
  name           = "${local.name}-${local.environment}-alerts"
  description    = "Alerts for ${local.name} ${local.environment}"
}

resource "oci_ons_subscription" "alerts_email" {
  compartment_id = var.compartment_ocid
  topic_id       = oci_ons_topic.alerts.id
  protocol       = "EMAIL"
  endpoint       = var.alert_email
}

# Data Sources
data "oci_identity_availability_domains" "ads" {
  compartment_id = var.compartment_ocid
}

data "oci_core_images" "oke" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Oracle Linux"
  operating_system_version = "8"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"

  filter {
    name   = "display_name"
    values = ["^.*OKE.*$"]
    regex  = true
  }
}

data "oci_core_images" "gpu" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Oracle Linux"
  operating_system_version = "8"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"

  filter {
    name   = "display_name"
    values = ["^.*GPU.*$"]
    regex  = true
  }
}

variable "object_storage_namespace" {
  description = "OCI Object Storage namespace"
  type        = string
}

variable "lb_certificate" {
  description = "Load balancer SSL certificate"
  type        = string
  sensitive   = true
}

variable "lb_certificate_key" {
  description = "Load balancer SSL certificate private key"
  type        = string
  sensitive   = true
}

variable "lb_certificate_ca" {
  description = "Load balancer SSL certificate CA"
  type        = string
  default     = ""
}

variable "ssh_public_key_path" {
  description = "Path to SSH public key for node access"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "alert_email" {
  description = "Email for monitoring alerts"
  type        = string
  default     = "ops@zambia-health.example.com"
}
