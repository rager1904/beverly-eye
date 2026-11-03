terraform {
  required_version = ">= 1.6"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.30"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.30"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
  backend "gcs" {
    bucket = "zambia-health-tfstate"
    prefix = "gcp/terraform.tfstate"
  }
}

provider "google" {
  project = var.project_id
  region  = var.gcp_region
}

provider "google-beta" {
  project = var.project_id
  region  = var.gcp_region
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
}

# VPC
resource "google_compute_network" "main" {
  name                    = "${local.name}-${local.environment}-vpc"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"

  depends_on = [google_project_service.compute]
}

resource "google_compute_subnetwork" "gke" {
  name          = "${local.name}-${local.environment}-gke-subnet"
  network       = google_compute_network.main.id
  region        = var.gcp_region
  ip_cidr_range = var.gke_subnet_cidr

  private_ip_google_access = true

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = var.gke_pods_cidr
  }
  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = var.gke_services_cidr
  }
}

resource "google_compute_subnetwork" "database" {
  name          = "${local.name}-${local.environment}-db-subnet"
  network       = google_compute_network.main.id
  region        = var.gcp_region
  ip_cidr_range = var.database_subnet_cidr
}

# GKE Cluster
resource "google_container_cluster" "main" {
  name     = "${local.name}-${local.environment}"
  location = var.gcp_region
  network  = google_compute_network.main.id
  subnetwork = google_compute_subnetwork.gke.id

  min_master_version = var.gke_version
  deletion_protection = true

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "10.200.0.0/28"
  }

  master_authorized_networks_config {
    cidr_blocks {
      cidr_block   = "10.0.0.0/8"
      display_name = "VPC"
    }
  }

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  addons_config {
    http_load_balancing {
      disabled = false
    }
    horizontal_pod_autoscaling {
      disabled = false
    }
    network_policy_config {
      disabled = false
    }
    gcp_filestore_csi_driver_config {
      enabled = true
    }
    gcs_fuse_csi_driver_config {
      enabled = true
    }
    config_connector_config {
      enabled = false
    }
  }

  cluster_autoscaling {
    enabled = true
    resource_limits {
      resource_type = "cpu"
      minimum       = 4
      maximum       = 200
    }
    resource_limits {
      resource_type = "memory"
      minimum       = 16
      maximum       = 800
    }
  }

  network_policy {
    enabled = true
    provider = "CALICO"
  }

  maintenance_policy {
    daily_maintenance_window {
      start_time = "03:00"
    }
  }

  security_posture_config {
    mode = "BASIC"
  }

  release_channel {
    channel = "REGULAR"
  }

  monitoring_config {
    managed_prometheus {
      enabled = true
    }
    advanced_datapath_observability_config {
      enable_metrics = true
    }
    enable_observability_metrics = true
  }

  logging_config {
    enable_vpc_flow_logs = true
  }

  depends_on = [
    google_project_service.container,
    google_project_service.compute,
  ]
}

resource "google_container_node_pool" "general" {
  name       = "general"
  location   = var.gcp_region
  cluster    = google_container_cluster.main.name
  node_count = var.system_node_count

  node_config {
    machine_type = "e2-standard-4"
    disk_size_gb = 100
    disk_type    = "pd-ssd"
    image_type   = "COS_CONTAINERD"
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }
    labels = {
      role = "general"
    }
  }

  autoscaling {
    min_node_count = 2
    max_node_count = 7
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

resource "google_container_node_pool" "gpu" {
  name       = "gpu"
  location   = var.gcp_region
  cluster    = google_container_cluster.main.name
  node_count = var.gpu_node_count

  node_config {
    machine_type = var.gpu_machine_type
    disk_size_gb = 500
    disk_type    = "pd-ssd"
    image_type   = "COS_CONTAINERD"
    guest_accelerator {
      type  = var.gpu_type
      count = var.gpu_count_per_node
    }
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }
    labels = {
      role = "gpu"
    }
    taint {
      key    = "nvidia.com/gpu"
      value  = "true"
      effect = "NO_SCHEDULE"
    }
  }

  autoscaling {
    min_node_count = 1
    max_node_count = 6
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

resource "google_container_node_pool" "inference" {
  name       = "inference"
  location   = var.gcp_region
  cluster    = google_container_cluster.main.name
  node_count = var.inference_node_count

  node_config {
    machine_type = "n2-standard-8"
    disk_size_gb = 200
    disk_type    = "pd-ssd"
    image_type   = "COS_CONTAINERD"
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }
    labels = {
      role = "inference"
    }
    reservation_affinity {
      consume_reservation_type = "ANY_RESERVATION"
    }
  }

  autoscaling {
    min_node_count = 1
    max_node_count = 10
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

# Cloud SQL PostgreSQL
resource "google_sql_database_instance" "main" {
  name             = "${local.name}-${local.environment}-pg"
  database_version = var.db_version
  region           = var.gcp_region

  settings {
    tier              = var.db_tier
    edition           = "ENTERPRISE_PLUS"
    disk_size         = var.db_disk_size
    disk_type         = "PD_SSD"
    disk_autoresize   = true
    disk_autoresize_limit = 1000

    availability_type = "REGIONAL"

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "03:00"
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 35
      }
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.main.id
      ssl_mode        = "TRUSTED_CLIENT_CERTIFICATE_REQUIRED"
    }

    maintenance_window {
      day          = 7
      hour         = 3
      update_track = "stable"
    }

    insights_config {
      query_string_length   = 1024
      record_application_tags = true
      record_client_address   = true
    }

    sql_server_audit_config {
      retention_interval = "30d"
    }

    user_password_validation_policy {
      enable_password_policy = true
      min_length            = 12
      complexity            = "COMPLEXITY_DEFAULT"
    }

    database_flags {
      name  = "shared_preload_libraries"
      value = "pgvector,pg_stat_statements"
    }
    database_flags {
      name  = "log_min_duration_statement"
      value = "1000"
    }
    database_flags {
      name  = "random_page_cost"
      value = "1.1"
    }
    database_flags {
      name  = "pgvector.enable_prefilter"
      value = "1"
    }
  }

  deletion_protection = true

  depends_on = [google_project_service.sqladmin]
}

resource "google_sql_database" "main" {
  name     = "zambia_health"
  instance = google_sql_database_instance.main.name
  charset  = "UTF8"
}

resource "google_sql_user" "admin" {
  name     = var.db_username
  instance = google_sql_database_instance.main.name
  password = var.db_password
}

# Memorystore Redis
resource "google_redis_instance" "main" {
  name           = "${local.name}-${local.environment}-redis"
  tier           = "STANDARD_HA"
  memory_size_gb = var.redis_memory_size_gb
  region         = var.gcp_region
  redis_version  = "REDIS_7"
  display_name   = "${local.name} ${local.environment} Redis"

  connect_mode            = "PRIVATE_SERVICE_ACCESS"
  authorized_network      = google_compute_network.main.id
  transit_encryption_mode = "SERVER_AUTHENTICATION"
  replica_count           = 2
  read_replicas_mode      = "READ_REPLICAS_ENABLED"
  persistence_config {
    persistence_mode = "RDB"
    rdb_snapshot_period = "ONE_HOUR"
  }

  maintenance_policy {
    weekly_maintenance_window {
      day        = "SUNDAY"
      start_time {
        hours   = 3
        minutes = 0
      }
    }
  }

  depends_on = [google_project_service.redis]
}

# Cloud Storage
resource "google_storage_bucket" "models" {
  name                        = "${local.name}-${local.environment}-models"
  location                    = var.gcp_region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  versioning {
    enabled = true
  }
  encryption {
    default_kms_key_name = google_kms_crypto_key.storage.id
  }
  public_access_prevention = "enforced"

  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_storage_bucket" "medical_images" {
  name                        = "${local.name}-${local.environment}-medical-images"
  location                    = var.gcp_region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  versioning {
    enabled = true
  }
  encryption {
    default_kms_key_name = google_kms_crypto_key.storage.id
  }
  public_access_prevention = "enforced"

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_storage_bucket" "backups" {
  name                        = "${local.name}-${local.environment}-backups"
  location                    = var.gcp_region
  storage_class               = "NEARLINE"
  uniform_bucket_level_access = true
  versioning {
    enabled = true
  }
  encryption {
    default_kms_key_name = google_kms_crypto_key.storage.id
  }
  public_access_prevention = "enforced"

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }
  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_storage_bucket" "audit_logs" {
  name                        = "${local.name}-${local.environment}-audit-logs"
  location                    = var.gcp_region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  versioning {
    enabled = true
  }
  encryption {
    default_kms_key_name = google_kms_crypto_key.storage.id
  }
  public_access_prevention = "enforced"

  lifecycle_rule {
    condition {
      age = 2555
    }
    action {
      type = "Delete"
    }
  }
}

# KMS
resource "google_kms_key_ring" "main" {
  name     = "${local.name}-${local.environment}"
  location = var.gcp_region
}

resource "google_kms_crypto_key" "storage" {
  name            = "storage-key"
  key_ring        = google_kms_key_ring.main.id
  rotation_period = "7776000s"

  version_template {
    algorithm = "GOOGLE_SYMMETRIC_ENCRYPTION"
  }
}

resource "google_kms_crypto_key" "database" {
  name            = "database-key"
  key_ring        = google_kms_key_ring.main.id
  rotation_period = "7776000s"

  version_template {
    algorithm = "GOOGLE_SYMMETRIC_ENCRYPTION"
  }
}

resource "google_kms_crypto_key" "redis" {
  name            = "redis-key"
  key_ring        = google_kms_key_ring.main.id
  rotation_period = "7776000s"

  version_template {
    algorithm = "GOOGLE_SYMMETRIC_ENCRYPTION"
  }
}

# Cloud CDN
resource "google_compute_backend_bucket" "cdn" {
  name        = "${local.name}-${local.environment}-cdn"
  description = "CDN backend for ${local.name}"
  bucket_name = google_storage_bucket.cdn_origin.name
  enable_cdn  = true

  cdn_policy {
    cache_mode          = "CACHE_ALL_STATIC"
    default_ttl         = 3600
    max_ttl             = 86400
    client_ttl          = 3600
    negative_caching    = true
    serve_while_stale   = 86400
  }
}

resource "google_storage_bucket" "cdn_origin" {
  name                        = "${local.name}-${local.environment}-cdn-origin"
  location                    = var.gcp_region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
}

resource "google_compute_url_map" "cdn" {
  name            = "${local.name}-${local.environment}-cdn-url-map"
  default_service = google_compute_backend_bucket.cdn.id

  host_rule {
    hosts        = [var.domain_name]
    path_matcher = "allpaths"
  }

  path_matcher {
    name            = "allpaths"
    default_service = google_compute_backend_bucket.cdn.id
  }
}

resource "google_compute_target_https_proxy" "cdn" {
  name    = "${local.name}-${local.environment}-https-proxy"
  url_map = google_compute_url_map.cdn.id
  ssl_certificates = [google_compute_ssl_certificate.cdn.id]
}

resource "google_compute_ssl_certificate" "cdn" {
  name        = "${local.name}-${local.environment}-ssl"
  description = "SSL certificate for CDN"
  managed {
    domains = [var.domain_name, "*.${var.domain_name}"]
  }
}

resource "google_compute_global_forwarding_rule" "cdn_https" {
  name       = "${local.name}-${local.environment}-cdn-https"
  target     = google_compute_target_https_proxy.cdn.id
  port_range = "443"
  ip_address = google_compute_global_address.cdn.address
}

resource "google_compute_global_address" "cdn" {
  name = "${local.name}-${local.environment}-cdn-ip"
}

# Cloud Logging
resource "google_logging_project_sink" "main" {
  name        = "${local.name}-${local.environment}-log-sink"
  description = "Log sink for ${local.name}"
  destination = "storage.googleapis.com/${google_storage_bucket.audit_logs.name}"
  filter      = "severity >= WARNING"

  unique_writer_identity = true

  bigquery_options {
    use_partitioned_tables = true
  }
}

resource "google_monitoring_notification_channel" "email" {
  display_name = "Email Notifications"
  type         = "email"
  labels = {
    email_address = var.alert_email
  }
}

resource "google_monitoring_alert_policy" "gke_cpu" {
  display_name = "${local.name}-${local.environment}-gke-cpu-high"
  combiner     = "OR"
  notification_channels = [google_monitoring_notification_channel.email.name]

  conditions {
    display_name = "GKE CPU utilization > 80%"
    condition_threshold {
      filter     = "metric.type=\"kubernetes.io/node/cpu/utilization\""
      duration   = "300s"
      comparison = "COMPARISON_GT"
      threshold_value = 0.8
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  alert_strategy {
    auto_close = "1800s"
  }
}

# Service enablement
resource "google_project_service" "compute" {
  service = "compute.googleapis.com"
}

resource "google_project_service" "container" {
  service = "container.googleapis.com"
}

resource "google_project_service" "sqladmin" {
  service = "sqladmin.googleapis.com"
}

resource "google_project_service" "redis" {
  service = "redis.googleapis.com"
}

resource "google_project_service" "storage_component" {
  service = "storage-component.googleapis.com"
}

resource "google_project_service" "monitoring" {
  service = "monitoring.googleapis.com"
}

resource "google_project_service" "logging" {
  service = "logging.googleapis.com"
}

resource "google_project_service" "cloudkms" {
  service = "cloudkms.googleapis.com"
}
