variable "resource_group_name" {
  description = "Name of the Azure Resource Group"
  type        = string
  default     = "rg-slo-dashboard"
}

variable "location" {
  description = "Azure region to deploy resources"
  type        = string
  default     = "East US"
}

variable "app_name" {
  description = "Name of the App Service (must be globally unique)"
  type        = string
  default     = "slo-dashboard-app"
}

variable "environment" {
  description = "Deployment environment tag"
  type        = string
  default     = "dev"
}