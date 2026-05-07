# Troubleshooting Log

This document captures real infrastructure issues encountered during the initial Terraform deployment of the `azure-slo-dashboard` project, along with their root causes and resolutions. Written in the spirit of a blameless post-mortem.

---

## Issue 1: Azure CLI Multi-Line Commands Failing in PowerShell

**Date:** May 2026  
**Severity:** Low  
**Time to Resolve:** ~10 minutes

### Symptom
Running Azure CLI commands with bash-style line continuation (`\`) in Windows PowerShell produced `ParserError` and `MissingExpressionAfterOperator` errors.

```
Missing expression after unary operator '--'.
Unexpected token 'name' in expression or statement.
```

### Root Cause
The commands were written for a bash/Linux shell. PowerShell uses a backtick (`` ` ``) for line continuation, not a backslash (`\`). Additionally, bash subshell syntax (`$(command)`) behaves differently in PowerShell when used inline.

### Resolution
Split commands into separate steps using PowerShell variables, and keep long commands on a single line to avoid continuation character issues entirely.

```powershell
# Step 1 — capture value into a variable first
$subscriptionId = az account show --query id -o tsv

# Step 2 — use the variable in the next command (single line)
az ad sp create-for-rbac --name "sp-terraform-sre-lab" --role Contributor --scopes /subscriptions/$subscriptionId
```

### Lesson Learned
Always verify which shell you are running in before executing commands from documentation. Most Azure and Terraform documentation assumes bash. When working on Windows without WSL, translate syntax accordingly. PowerShell equivalents: use `` ` `` for line continuation, `$var = command` for variable assignment, and avoid inline subshells.

---

## Issue 2: Azure App Service Plan Failing with Quota Error (Free and Basic Tiers)

**Date:** May 2026  
**Severity:** High  
**Time to Resolve:** ~2 hours

### Symptom
`terraform apply` succeeded for all resources except the App Service Plan and App Service, which failed with a `401 Unauthorized` quota error across F1 (Free), B1 (Basic), and S1 (Standard) SKUs.

```
Error: creating App Service Plan
unexpected status 401 (401 Unauthorized)
Current Limit (Free VMs): 0 / Current Limit (Basic VMs): 0 / Current Limit (Standard VMs): 0
```

### Root Cause
The Azure subscription was initially provisioned as a **Training Subscription** type, which Microsoft locks to zero VM quota by default as a fraud prevention measure. This restriction applies globally across all regions (East US, West US, Central US) and all VM-based App Service tiers simultaneously.

Additionally, the Azure Quotas portal showed limits of 10 for Standard BS Family vCPUs after upgrading to Pay-As-You-Go, but the underlying enforcement layer had not yet propagated the change. This caused a mismatch between what the portal displayed and what the API enforced.

The error message itself was misleading — it reported `Amount required for this deployment: 0` and `Minimum New Limit: 0`, which incorrectly suggested no quota was needed at all rather than clarifying that the quota system was not yet active.

### Resolution Attempts (in order)

| Attempt | Action | Result |
|---|---|---|
| 1 | Changed region from East US → West US | Same quota error |
| 2 | Changed region to Central US | Same quota error |
| 3 | Changed SKU from F1 → B1 | Same quota error (Basic VMs: 0) |
| 4 | Changed SKU from B1 → S1 | Same quota error (Standard VMs: 0) |
| 5 | Requested quota increase via Azure Portal | Quota portal showed 10 but API still enforced 0 |
| 6 | Upgraded subscription to Pay-As-You-Go | Quota propagation delayed 24-48hrs |
| 7 | Recreated Service Principal | Same quota error |
| **8** | **Switched to Azure Container Apps** | **✅ Deployed successfully** |

### Final Resolution
Replaced `azurerm_service_plan` and `azurerm_linux_web_app` resources entirely with `azurerm_container_app_environment` and `azurerm_container_app`. Container Apps uses a serverless consumption model that does not draw from VM quota pools, bypassing the restriction completely.

```hcl
# Replaced this:
resource "azurerm_service_plan" "slo" {
  sku_name = "B1"  # Blocked by VM quota
}

# With this:
resource "azurerm_container_app_environment" "slo" {
  name                       = "cae-slo-dashboard"
  log_analytics_workspace_id = azurerm_log_analytics_workspace.slo.id
  # No VM quota required
}
```

### Lesson Learned
Azure App Service Plans (all tiers) consume regional VM quota. New Azure subscriptions — especially those created as Trial or Training types — have this quota set to zero until the account matures or a quota increase is approved. Azure Container Apps, Azure Functions (Consumption Plan), and Azure Container Instances are quota-exempt alternatives that work on day one of any subscription type.

For future projects on new subscriptions, prefer serverless compute options until VM quota is confirmed available.

---

## Issue 3: Stale Client Secret on Service Principal After Patch

**Date:** May 2026  
**Severity:** Medium  
**Time to Resolve:** ~5 minutes

### Symptom
After recreating the Service Principal, `terraform apply` failed with an authentication error even though credentials appeared to be set correctly.

```
Error: building account: could not acquire access token to parse claims:
AADSTS7000215: Invalid client secret provided.
```

### Root Cause
When `az ad sp create-for-rbac` is run against an existing Service Principal name, Azure patches the existing SP rather than creating a new one. This generates a **new client secret** (password) while the `appId` and `tenant` remain the same. The old secret stored in the `ARM_CLIENT_SECRET` environment variable became invalid.

The output message `Found an existing application instance. We will patch it.` was the indicator that a new secret had been issued.

### Resolution
Updated the `ARM_CLIENT_SECRET` environment variable with the newly generated password from the patch output, then set it permanently.

```powershell
$env:ARM_CLIENT_SECRET = "new-password-from-output"
[System.Environment]::SetEnvironmentVariable("ARM_CLIENT_SECRET", $env:ARM_CLIENT_SECRET, "User")
```

### Lesson Learned
Any time `az ad sp create-for-rbac` runs against an existing SP name, treat the output password as a new credential that invalidates the previous one. Always update all stored references (environment variables, Key Vault, CI/CD secrets) immediately. In production, Service Principal secrets should be stored in Azure Key Vault and rotated on a schedule rather than managed manually.

---

## Issue 4: Microsoft.App Resource Provider Not Registered

**Date:** May 2026  
**Severity:** Low  
**Time to Resolve:** ~3 minutes

### Symptom
After switching to Container Apps, `terraform apply` failed with a `409 Conflict` error.

```
Error: creating Managed Environment
MissingSubscriptionRegistration: The subscription is not registered
to use namespace 'Microsoft.App'.
```

### Root Cause
Azure resource providers must be explicitly registered on a subscription before resources of that type can be created. New subscriptions do not have all providers registered by default. `Microsoft.App` (Container Apps) was not registered because it had never been used on this subscription before.

### Resolution
Registered the required providers using the Azure CLI and waited for registration to complete before re-running Terraform.

```powershell
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights

# Verify registration completed before applying
az provider show --namespace Microsoft.App --query registrationState -o tsv
# Wait for output: Registered
```

### Lesson Learned
When deploying a new Azure resource type for the first time on a subscription, always verify the resource provider is registered. This is a one-time operation per subscription per provider. In a production environment, resource provider registration is typically handled as part of subscription vending automation (Landing Zone setup) so individual teams never encounter this manually.

---

## Final Deployed Architecture

After resolving all issues, the following resources were successfully deployed via Terraform:

| Resource | Type | Notes |
|---|---|---|
| `rg-slo-dashboard` | Resource Group | Container for all project resources |
| `law-slo-dashboard` | Log Analytics Workspace | Log storage and query engine |
| `appi-slo-dashboard` | Application Insights | APM and telemetry |
| `cae-slo-dashboard` | Container App Environment | Serverless compute environment |
| `ca-slo-dashboard` | Container App | Runs the FastAPI application |

**Total deployment time after all issues resolved:** ~3 minutes  
**Estimated daily cost (S1 equivalent via Container Apps):** ~$0.00–$0.05 at dev traffic levels

---

## Key Takeaways for Future Deployments

1. **New Azure subscriptions have zero VM quota** — use serverless options (Container Apps, Functions Consumption) until quota is confirmed
2. **PowerShell ≠ Bash** — translate CLI commands when not using WSL
3. **Patching a Service Principal generates a new secret** — update all credential stores immediately
4. **Register resource providers before first use** — add `az provider register` to your subscription setup runbook
5. **The Azure Quota portal and API enforcement can be out of sync** — wait 24-48hrs after subscription changes or use quota-exempt compute
