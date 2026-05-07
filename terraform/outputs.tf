output "app_url" {
  description = "URL of the deployed Container App"
  value       = "https://${azurerm_container_app.slo.latest_revision_fqdn}"
}

output "container_app_name" {
  description = "Name of the Container App"
  value       = azurerm_container_app.slo.name
}

output "resource_group_name" {
  description = "Resource Group name"
  value       = azurerm_resource_group.slo.name
}

output "app_insights_connection_string" {
  description = "Application Insights connection string"
  value       = azurerm_application_insights.slo.connection_string
  sensitive   = true
}

output "app_insights_instrumentation_key" {
  description = "App Insights instrumentation key"
  value       = azurerm_application_insights.slo.instrumentation_key
  sensitive   = true
}

output "log_analytics_workspace_id" {
  description = "Log Analytics Workspace ID"
  value       = azurerm_log_analytics_workspace.slo.id
}