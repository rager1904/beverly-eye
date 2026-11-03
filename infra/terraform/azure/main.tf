terraform {
  required_version = ">= 1.6"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
  backend "azurerm" {
    resource_group_name  = "zambia-health-tfstate"
    storage_account_name = "zambiahealthtfstate"
    container_name       = "tfstate"
    key                  = "azure/terraform.tfstate"
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
    resource_group {
      prevent_deletion_if_contains_resources = true
    }
  }
}

locals {
  name        = "zambia-health"
  environment = var.environment
  location    = var.azure_location
  common_tags = {
    Project     = "UbuntuCare"
    Environment = var.environment
    Region      = "Zambia"
    ManagedBy   = "Terraform"
    Compliance  = "HIPAA"
    DataClass   = "PHI"
  }
}

resource "azurerm_resource_group" "main" {
  name     = "${local.name}-${local.environment}"
  location = local.location
  tags     = local.common_tags
}

# AKS Cluster
resource "azurerm_kubernetes_cluster" "main" {
  name                = "${local.name}-${local.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  dns_prefix          = local.name
  kubernetes_version  = var.kubernetes_version
  sku_tier            = "Standard"

  default_node_pool {
    name                = "system"
    vm_size             = "Standard_D4s_v5"
    node_count          = var.system_node_count
    enable_auto_scaling = true
    min_count           = 2
    max_count           = 5
    vnet_subnet_id      = azurerm_subnet.aks.id
    zones               = [1, 2, 3]
    node_labels = {
      role = "system"
    }
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin     = "azure"
    network_policy     = "calico"
    dns_service_ip     = "10.0.0.10"
    service_cidr       = "10.0.0.0/16"
    load_balancer_sku  = "standard"
  }

  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  }

  azure_active_directory_role_based_access_control {
    managed            = true
    azure_rbac_enabled = true
  }

  storage_profile {
    blob_driver_enabled = true
    disk_driver_enabled = true
    file_driver_enabled = true
  }

  key_vault_secrets_provider {
    secret_rotation_enabled = true
    secret_rotation_interval = "5m"
  }

  microsoft_defender {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  }

  tags = local.common_tags
}

resource "azurerm_kubernetes_cluster_node_pool" "gpu" {
  name                  = "gpu"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.main.id
  vm_size               = "Standard_NC6s_v3"
  node_count            = var.gpu_node_count
  enable_auto_scaling   = true
  min_count             = 1
  max_count             = 6
  vnet_subnet_id        = azurerm_subnet.aks.id
  zones                 = [1, 2, 3]
  node_labels = {
    role    = "gpu"
    "nvidia.com/gpu" = "true"
  }
  node_taints = [
    "nvidia.com/gpu=true:NoSchedule"
  }

  tags = local.common_tags
}

resource "azurerm_kubernetes_cluster_node_pool" "inference" {
  name                  = "inference"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.main.id
  vm_size               = "Standard_D8s_v5"
  node_count            = var.inference_node_count
  enable_auto_scaling   = true
  min_count             = 1
  max_count             = 10
  vnet_subnet_id        = azurerm_subnet.aks.id
  zones                 = [1, 2, 3]
  node_labels = {
    role = "inference"
  }

  tags = local.common_tags
}

# Azure Database for PostgreSQL
resource "azurerm_postgresql_flexible_server" "main" {
  name                          = "${local.name}-${local.environment}-pg"
  resource_group_name           = azurerm_resource_group.main.name
  location                      = azurerm_resource_group.main.location
  version                       = "15"
  administrator_login           = var.db_username
  administrator_password        = var.db_password
  storage_mb                    = var.db_storage_mb
  sku_name                      = var.db_sku
  backup_retention_days         = 35
  geo_redundant_backup_enabled  = true
  auto_grow_enabled             = true
  delegated_subnet_id           = azurerm_subnet.database.id
  private_dns_zone_id           = azurerm_private_dns_zone.postgres.id

  high_availability {
    mode = "ZoneRedundant"
  }

  maintenance_window {
    day_of_week  = 0
    start_hour   = 3
    start_minute = 0
  }

  tags = local.common_tags
}

resource "azurerm_postgresql_flexible_server_database" "main" {
  name      = "zambia_health"
  server_id = azurerm_postgresql_flexible_server.main.id
  collation = "en_US.UTF8"
  charset   = "UTF8"
}

resource "azurerm_postgresql_flexible_server_configuration" "pgvector" {
  name      = "shared_preload_libraries"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = "pgvector,pg_stat_statements"
}

# Azure Cache for Redis
resource "azurerm_redis_cache" "main" {
  name                          = "${local.name}-${local.environment}-redis"
  resource_group_name           = azurerm_resource_group.main.name
  location                      = azurerm_resource_group.main.location
  capacity                      = 3
  family                        = "P"
  sku_name                      = "Premium"
  enable_non_ssl_port           = false
  minimum_tls_version           = "1.2"
  redis_version                 = "7"
  shard_count                   = 3
  replicas_per_master           = 2
  subnet_id                     = azurerm_subnet.redis.id
  private_static_ip_address     = null

  redis_configuration {
    enable_authentication = true
    maxmemory_policy      = "allkeys-lru"
    maxmemory_reserved    = 200
    maxfragmentationmemory_reserved = 200
  }

  patch_schedule {
    day_of_week    = "Sunday"
    start_hour_utc = 2
  }

  tags = local.common_tags
}

# Blob Storage
resource "azurerm_storage_account" "main" {
  name                          = "${local.name}${local.environment}sa"
  resource_group_name           = azurerm_resource_group.main.name
  location                      = azurerm_resource_group.main.location
  account_tier                  = "Standard"
  account_replication_type      = "GRS"
  account_kind                  = "StorageV2"
  enable_https_traffic_only     = true
  min_tls_version               = "TLS1_2"
  infrastructure_encryption_enabled = true

  blob_properties {
    versioning_enabled      = true
    delete_retention_policy {
      days = 7
    }
    container_delete_retention_policy {
      days = 7
    }
  }

  tags = local.common_tags
}

resource "azurerm_storage_container" "models" {
  name                  = "models"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "medical_images" {
  name                  = "medical-images"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "backups" {
  name                  = "backups"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "audit_logs" {
  name                  = "audit-logs"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

# Key Vault
resource "azurerm_key_vault" "main" {
  name                        = "${local.name}-${local.environment}-kv"
  resource_group_name         = azurerm_resource_group.main.name
  location                    = azurerm_resource_group.main.location
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  sku_name                    = "standard"
  enabled_for_disk_encryption = true
  soft_delete_retention_days  = 90
  purge_protection_enabled    = true
  public_network_access_enabled = false
  rbac_authorization_enabled  = true

  network_acls {
    default_action = "Deny"
    bypass         = "AzureServices"
  }

  tags = local.common_tags
}

# Front Door CDN
resource "azurerm_frontdoor_profile" "main" {
  name                = "${local.name}-${local.environment}-fd"
  resource_group_name = azurerm_resource_group.main.name
  sku_name            = "Premium_AzureFrontDoor"

  tags = local.common_tags
}

resource "azurerm_frontdoor_endpoint" "main" {
  name                     = "${local.name}-${local.environment}-endpoint"
  frontdoor_profile_id     = azurerm_frontdoor_profile.main.id
  enabled                  = true
}

resource "azurerm_frontdoor_origin_group" "main" {
  name                     = "${local.name}-${local.environment}-origin-group"
  frontdoor_profile_id     = azurerm_frontdoor_profile.main.id

  load_balancing {
    sample_size                 = 4
    successful_samples_required = 3
  }

  health_probe {
    path                = "/health"
    request_type        = "HEAD"
    protocol            = "Https"
    interval_in_seconds = 30
  }
}

resource "azurerm_frontdoor_origin" "aks" {
  name                           = "${local.name}-${local.environment}-origin"
  frontdoor_origin_group_id      = azurerm_frontdoor_origin_group.main.id
  enabled                        = true
  host_name                      = azurerm_container_group.ingress.fqdn
  http_port                      = 80
  https_port                     = 443
  priority                       = 1
  weight                         = 1000
}

resource "azurerm_frontdoor_route" "main" {
  name                     = "${local.name}-${local.environment}-route"
  frontdoor_endpoint_id    = azurerm_frontdoor_endpoint.main.id
  frontdoor_origin_group_id = azurerm_frontdoor_origin_group.main.id
  frontdoor_origin_ids     = [azurerm_frontdoor_origin.aks.id]
  patterns_to_match        = ["/*"]
  supported_protocols      = ["Http", "Https"]
  forwarding_protocol      = "HttpsOnly"
  link_to_default_domain   = true

  cache {
    query_string_caching_behavior = "IgnoreSpecifiedQueryStrings"
    query_strings                 = []
    compression_enabled           = true
  }
}

resource "azurerm_frontdoor_firewall_policy" "main" {
  name                = "${local.name}-${local.environment}-waf"
  resource_group_name = azurerm_resource_group.main.name
  sku_name            = "Premium_AzureFrontDoor"
  enabled             = true
  mode                = "Prevention"

  managed_rule {
    type    = "Microsoft_DefaultRuleSet"
    version = "2.1"
    action  = "Block"
  }

  managed_rule {
    type    = "Microsoft_BotManagerRuleSet"
    version = "1.0"
    action  = "Block"
  }

  managed_rule {
    type    = "Microsoft_SQLRuleSet"
    version = "1.0"
    action  = "Block"
  }

  tags = local.common_tags
}

# Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "main" {
  name                       = "${local.name}-${local.environment}-law"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  sku                        = "PerGB2018"
  retention_in_days          = 90
  daily_quota_gb             = 10
  internet_ingestion_enabled = true
  internet_query_enabled     = true

  tags = local.common_tags
}

resource "azurerm_monitor_workspace" "main" {
  name                = "${local.name}-${local.environment}-amw"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  tags = local.common_tags
}

resource "azurerm_monitor_diagnostic_setting" "aks" {
  name                       = "aks-to-log-analytics"
  target_resource_id         = azurerm_kubernetes_cluster.main.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  enabled_log {
    category = "kube-apiserver"
  }
  enabled_log {
    category = "kube-controller-manager"
  }
  enabled_log {
    category = "kube-scheduler"
  }
  enabled_log {
    category = "kube-audit"
  }
  enabled_log {
    category = "cluster-autoscaler"
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}

# Networking
resource "azurerm_virtual_network" "main" {
  name                = "${local.name}-${local.environment}-vnet"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  address_space       = var.vnet_address_space

  tags = local.common_tags
}

resource "azurerm_subnet" "aks" {
  name                 = "aks"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = var.aks_subnet_prefixes
}

resource "azurerm_subnet" "database" {
  name                 = "database"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = var.database_subnet_prefixes

  delegation {
    name = "flexibleServerDelegation"
    service_delegation {
      name    = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

resource "azurerm_subnet" "redis" {
  name                 = "redis"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = var.redis_subnet_prefixes

  delegation {
    name = "redisCacheDelegation"
    service_delegation {
      name    = "Microsoft.Cache/redis"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

resource "azurerm_private_dns_zone" "postgres" {
  name                = "${local.name}-${local.environment}.postgres.database.azure.com"
  resource_group_name = azurerm_resource_group.main.name

  tags = local.common_tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "postgres" {
  name                  = "postgres-vnet-link"
  resource_group_name   = azurerm_resource_group.main.name
  private_dns_zone_name = azurerm_private_dns_zone.postgres.name
  virtual_network_id    = azurerm_virtual_network.main.id
  registration_enabled  = false
}

# Data Sources
data "azurerm_client_config" "current" {}
