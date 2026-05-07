# ─── RESOURCE GROUP ───────────────────────────────────────
# A Resource Group is a logical container for Azure resources.
# Everything in this project lives inside this one group —
# makes it easy to see costs and delete everything at once.
resource "azurerm_resource_group" "slo" {
  name     = var.resource_group_name
  location = var.location

  tags = {
    environment = var.environment
    project     = "sre-training"
    managed_by  = "terraform"
  }
}

# ─── LOG ANALYTICS WORKSPACE ──────────────────────────────
# This is Azure's log storage and query engine.
# Your app will ship logs and metrics here.
# First 5 GB/month is free — dev traffic won't exceed this.
resource "azurerm_log_analytics_workspace" "slo" {
  name                = "law-slo-dashboard"
  resource_group_name = azurerm_resource_group.slo.name
  location            = azurerm_resource_group.slo.location
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = {
    environment = var.environment
  }
}
# ─── CONTAINER APPS ENVIRONMENT ───────────────────────────
# This replaces the App Service Plan + App Service.
# Container Apps runs serverless — no VM quota needed.
resource "azurerm_container_app_environment" "slo" {
  name                       = "cae-slo-dashboard"
  resource_group_name        = azurerm_resource_group.slo.name
  location                   = azurerm_resource_group.slo.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.slo.id

  tags = {
    environment = var.environment
  }
}

# ─── CONTAINER APP ────────────────────────────────────────
# The actual app — runs your FastAPI container.
# We start with a public hello-world image to verify
# deployment works, then swap to our own image in Week 3.
resource "azurerm_container_app" "slo" {
  name                         = "ca-slo-dashboard"
  resource_group_name          = azurerm_resource_group.slo.name
  container_app_environment_id = azurerm_container_app_environment.slo.id
  revision_mode                = "Single"

  template {
    container {
      name   = "slo-app"
      image  = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 80

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  tags = {
    environment = var.environment
  }
}

# ─── APPLICATION INSIGHTS ─────────────────────────────────
# Application Insights sits on top of Log Analytics and gives
# you request tracing, performance monitoring, and live metrics.
# This is what OpenTelemetry will ship data to from your app.
resource "azurerm_application_insights" "slo" {
  name                = "appi-slo-dashboard"
  resource_group_name = azurerm_resource_group.slo.name
  location            = azurerm_resource_group.slo.location
  workspace_id        = azurerm_log_analytics_workspace.slo.id
  application_type    = "web"

  tags = {
    environment = var.environment
  }
}