# Azure SLO Dashboard with AI Anomaly Explainer

A production-grade Site Reliability Engineering (SRE) project built on Azure, Python, and Terraform. This service tracks real-time SLO (Service Level Objective) compliance, calculates error budget burn rates, and uses AI to generate plain-English incident analysis and recommended actions — the same pattern used by modern AIOps platforms like PagerDuty and Datadog.

---

## What This Project Does

This project deploys a fully instrumented FastAPI service to Azure Container Apps that:

- **Tracks live SLIs (Service Level Indicators)** — availability and latency — from real HTTP traffic
- **Calculates error budgets** — how much failure your SLO allows and how fast you're consuming it
- **Detects SLO violations** — flags when availability drops below target and computes burn rate
- **Generates AI-powered incident analysis** — calls Claude via OpenRouter to produce structured incident reports with severity, plain-English explanation, recommended actions, and deployment policy

---

## Live Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Azure (East US)                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Container App Environment                  │   │
│  │                                                     │   │
│  │   ┌─────────────────────────────────────────────┐  │   │
│  │   │         ca-slo-dashboard                     │  │   │
│  │   │         FastAPI + Python 3.11                │  │   │
│  │   │                                             │  │   │
│  │   │  /api/data    → Simulated service traffic   │  │   │
│  │   │  /slo/status  → Error budget dashboard      │  │   │
│  │   │  /slo/explain → AI incident analysis        │  │   │
│  │   └─────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────────┐  ┌──────────────────────────────┐   │
│  │  Log Analytics   │  │    Application Insights       │   │
│  │  Workspace       │  │    (APM + Telemetry)          │   │
│  └──────────────────┘  └──────────────────────────────┘   │
│                                                             │
│  ┌──────────────────┐                                      │
│  │  Azure Container │                                      │
│  │  Registry (ACR)  │                                      │
│  └──────────────────┘                                      │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   OpenRouter API   │
                    │  (Claude Haiku)    │
                    └───────────────────┘
```

All infrastructure is managed as code via Terraform.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Cloud | Microsoft Azure |
| Compute | Azure Container Apps (serverless) |
| IaC | Terraform |
| Language | Python 3.11 |
| Framework | FastAPI |
| Observability | Azure Monitor, Application Insights, OpenTelemetry |
| AI | Claude Haiku via OpenRouter API |
| Containers | Docker, Azure Container Registry |
| CI/CD | GitHub Actions |
| Testing | pytest |

---

## SRE Skills Demonstrated

### 1. SLI/SLO/Error Budget Design
Defined and implemented the three core SRE reliability metrics from scratch:

- **SLI (Service Level Indicator)** — the raw measurement (request success rate, latency)
- **SLO (Service Level Objective)** — the target (99.9% availability, <200ms latency)
- **Error Budget** — the allowed failure tolerance (0.1% of requests can fail)

The `SLOCalculator` class computes error budget consumption and burn rate in real time, which is the mathematical foundation every SRE team uses to make deployment decisions.

### 2. Observability Instrumentation
Instrumented a production service with:

- **Structured logging** — JSON-formatted logs parseable by Log Analytics
- **Custom metrics** — request counters, error counters, latency histograms via OpenTelemetry
- **Distributed tracing** — trace context propagated through FastAPI middleware
- **Application Performance Monitoring** — Azure Application Insights integration

### 3. Infrastructure as Code
Provisioned all Azure infrastructure via Terraform with proper separation of concerns:

- `providers.tf` — provider version pinning
- `variables.tf` — parameterized, reusable configuration
- `main.tf` — resource definitions with inline documentation
- `outputs.tf` — structured output for downstream consumption

Resources managed: Resource Group, Log Analytics Workspace, Application Insights, Container App Environment, Container App, Azure Container Registry.

### 4. Containerization & Cloud-Native Deployment
Containerized the FastAPI application with a production-grade Dockerfile and deployed to Azure Container Apps — a serverless Kubernetes-based platform. Configured auto-scaling (0-3 replicas) and external ingress.

### 5. AIOps — AI-Augmented Incident Response
Built an AI-powered SLO explainer that mirrors how modern SRE teams are integrating LLMs into their operations workflows. Given raw SLO metrics, the system generates:

- Plain-English incident summaries for non-technical stakeholders
- Risk level classification (Low / Medium / High / Critical)
- Specific, actionable remediation steps for the on-call engineer
- Deployment policy recommendation (Allow / Freeze / Rollback required)

### 6. Security Practices
- Service Principal authentication with least-privilege Contributor role
- Secrets managed via environment variables and Terraform sensitive variables — never hardcoded
- `.gitignore` and `.dockerignore` configured to exclude sensitive files
- GitHub secret scanning enforcement for credential leak prevention

---

## Project Build Log

### Week 1 — Environment Setup
Configured the complete local development environment: Azure CLI authentication, Terraform service principal, Python virtual environment, project structure, and GitHub repository. Established the `terraform destroy` / `terraform apply` workflow for cost-controlled infrastructure management.

**SRE relevance:** Environment parity between local and production is a foundational SRE practice. Infrastructure-as-code means any environment can be recreated from scratch in minutes.

### Week 2 — Terraform Infrastructure
Wrote and deployed all Azure infrastructure as Terraform code. Navigated real-world Azure quota restrictions, subscription upgrade requirements, and resource provider registration — debugging each issue methodically using Azure CLI diagnostics.

**SRE relevance:** Infrastructure engineers regularly troubleshoot cloud provider quota limits, IAM permission errors, and resource provisioning failures. This week simulated exactly that experience, including documenting every issue and resolution in `TROUBLESHOOTING.md`.

### Week 3 — Application, SLO Engine & AI Explainer
Built the full application stack:

- **`app/config.py`** — environment-driven configuration with no hardcoded values
- **`app/main.py`** — FastAPI service with realistic error rate and latency simulation, custom OTel middleware, and all API endpoints
- **`slo/calculator.py`** — SLO math engine computing availability, error budget, and burn rate
- **`ai/explainer.py`** — OpenRouter integration generating structured AI incident analysis
- **`tests/test_slo_calculator.py`** — pytest test suite with 5 passing tests covering happy path, violations, edge cases, and math correctness

Containerized with Docker, pushed to Azure Container Registry, and deployed to Azure Container Apps via Terraform.

**SRE relevance:** This week covers the full SRE daily workflow — instrument the service, define reliability targets, calculate error budgets, respond to violations with AI-assisted triage.

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Liveness probe — returns service health status |
| `/api/data` | GET | Simulated service endpoint (5% error rate, variable latency) |
| `/api/slow` | GET | Always violates latency SLO — for budget burn testing |
| `/api/error` | GET | Always returns 500 — for availability budget burn testing |
| `/slo/status` | GET | Current SLO status, error budget, and burn rate |
| `/slo/explain` | GET | AI-generated incident analysis of current SLO state |
| `/slo/reset` | POST | Reset request counters for a clean measurement window |
| `/docs` | GET | Interactive Swagger UI — test all endpoints from the browser |

---

## Sample AI Output

Given a violated SLO with 18% error rate and 5500x burn rate, the AI explainer produced:

> **Summary:** Service availability has collapsed to 81.4% with error budget completely exhausted and a 5571x burn rate, indicating a severe ongoing incident.
>
> **Risk Level:** Critical
>
> **What This Means:** The service is failing roughly 1 in 5 requests instead of the expected 1 in 1000. At this burn rate, the entire month's error budget was consumed in minutes.
>
> **Recommended Actions:**
> - Declare SEV-1 incident and engage on-call team lead. Investigate error logs from the last 30 minutes.
> - Implement emergency mitigation — rollback last deployment, scale resources, or route traffic away from affected component.
> - Once stabilized, review failed requests for patterns and ensure monitoring alerts trigger before 50% error rate.
>
> **Deployment Policy:** Rollback required

---

## Local Development

```bash
# Clone the repo
git clone https://github.com/CMaselli23/azure-slo-dashboard.git
cd azure-slo-dashboard

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your values

# Run tests
pytest tests/ -v

# Start locally
uvicorn app.main:app --reload --port 8000
```

---

## Infrastructure Deployment

```bash
# Authenticate
az login
az account set --subscription "Your Subscription"

# Set Terraform credentials
export ARM_CLIENT_ID="..."
export ARM_CLIENT_SECRET="..."
export ARM_SUBSCRIPTION_ID="..."
export ARM_TENANT_ID="..."

# Deploy
cd terraform
terraform init
terraform apply -var="openrouter_api_key=your-key-here"

# Destroy when done (cost control)
terraform destroy -var="openrouter_api_key=your-key-here"
```

---

## Cost Profile

| Resource | Tier | Monthly Cost |
|---|---|---|
| Azure Container Apps | Consumption (serverless) | ~$0–2 |
| Log Analytics Workspace | Pay-per-GB (5 GB free) | $0 |
| Application Insights | Pay-per-GB (5 GB free) | $0 |
| Azure Container Registry | Basic | ~$5 |
| OpenRouter API (Claude Haiku) | Pay-per-token | ~$0–1 |
| **Total** | | **~$5–8/month** |

Running `terraform destroy` between sessions reduces cost to effectively $0.

---

## Troubleshooting

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for a full post-mortem style log of issues encountered during the initial deployment, including Azure quota restrictions, service principal authentication, and resource provider registration.

---

## Part of the Maselli Technologies SRE Training Curriculum

This project is Month 1 of a 6-month hands-on SRE training program covering:

| Month | Project | Focus |
|---|---|---|
| ✅ 1 | Azure SLO Dashboard + AI Explainer | SLIs, SLOs, Error Budgets, AIOps |
| 2 | AI-Powered Incident Response Bot | Incident Management, Runbooks |
| 3 | AKS Observability Stack | Kubernetes, Prometheus, Grafana |
| 4 | Internal Developer Platform API | Platform Engineering, GitOps |
| 5 | Chaos Engineering Suite | Chaos Engineering, Resilience |
| 6 | Full SRE Platform + AI Ops Chatbot | Capstone Integration |
