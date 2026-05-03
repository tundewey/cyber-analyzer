# Deploy Cybersecurity Analyzer to AWS

The app ships as **one Docker image**: FastAPI on port **8000** serves the API and the static Next.js UI (see the root `Dockerfile`). This guide uses **Amazon ECR** + **AWS App Runner**.

**Semgrep** loads a large rule set; allocate **at least 2 GB memory** for the service (similar to other cloud deployments of this project).

---

## 1. Log in to AWS

1. Open [AWS Console](https://console.aws.amazon.com) and sign in (IAM user or admin for learning).
2. Choose a **Region** (e.g. **US East N. Virginia `us-east-1`**) from the top bar. Use the **same region** for ECR and App Runner.

---

## 2. Create an ECR repository

1. Go to **Elastic Container Registry (ECR)**.
2. **Repositories** → **Create repository**.
3. **Visibility**: Private. **Repository name**: e.g. `cyber-analyzer`.
4. **Create repository**.

---

## 3. Push the image from your computer

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) running.
- [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) installed.
- IAM permissions for ECR push (e.g. attach managed policies for ECR or use an admin user for the lab).

Configure credentials once:

```bash
aws configure
```

### Push (Windows)

From the **cyber** project root, run:

```powershell
.\scripts\push-ecr.ps1 -AwsRegion us-east-1 -EcrRepository cyber-analyzer -ImageTag latest
```

Optional: `-AwsAccountId 123456789012` if discovery fails.

### Push (macOS / Linux)

```bash
chmod +x scripts/push-ecr.sh
AWS_REGION=us-east-1 ECR_REPOSITORY=cyber-analyzer IMAGE_TAG=latest ./scripts/push-ecr.sh
```

Confirm the image appears under **ECR** → your repository → **Images**.

---

## 4. Create an App Runner service

1. Open **AWS App Runner**.
2. **Create service**.
3. **Source**: **Container registry** → **Amazon ECR**.
4. Select your **repository** and **image tag** (e.g. `latest`).
5. **Deployment trigger**: Automatic or manual (your choice).
6. **Configure service**:
   - **Port**: **8000**
   - **Health check** (if shown): HTTP path **`/health`**
7. **Environment variables** — add at least:

   | Name | Value / source |
   |------|----------------|
   | `ENVIRONMENT` | `production` |
   | `SEMGREP_APP_TOKEN` | Your Semgrep token (prefer **Secrets Manager** reference) |
   | `OPENAI_API_KEY` *or* `OPENROUTER_API_KEY` | Your LLM key |

   Optional (OpenRouter): `OPENROUTER_BASE_URL`, `OPENROUTER_MODEL`, `OPENROUTER_MAX_TOKENS`, `LLM_MAX_TOKENS`, `LLM_MODEL`.

   See **`.env.example`** in the repo root for the full list.

8. **CPU / memory**: Use **at least 2 GB** RAM so Semgrep is stable.

9. **Create service** and wait until status is **Running**.

---

## 5. Secrets Manager (recommended)

Do **not** paste production keys as plain text in the console if you can avoid it.

1. **Secrets Manager** → **Store a new secret** → **Other type of secret**.
2. Add key/value pairs (e.g. `OPENROUTER_API_KEY`, `SEMGREP_APP_TOKEN`).
3. Name the secret (e.g. `cyber/prod`).
4. In **App Runner** → service → **Configuration** → **Environment variables**, use **reference** to inject secrets from Secrets Manager.

---

## 6. Verify

1. Copy the **default domain** URL from App Runner (HTTPS).
2. Open it in a browser — the Cybersecurity Analyst UI should load.
3. Upload a small `.py` file and run **Analyze**.
4. If something fails, open **App Runner** → **Logs** (CloudWatch) and check for missing env vars or out-of-memory errors.

---

## Troubleshooting

| Issue | What to check |
|-------|----------------|
| 502 / unhealthy | `/health` reachable; container listens on **8000**; deployment finished. |
| 500 on analyze | LLM and `SEMGREP_APP_TOKEN` set in App Runner; restart after changing env. |
| OOM / Semgrep killed | Increase memory to **2 GB** or more. |
| OpenRouter credit errors | Lower `OPENROUTER_MAX_TOKENS` or add credits; see project `server.py` defaults. |
| **`docker build` fails on `uv tool install semgrep`** | Current `Dockerfile` uses **`uv sync` only** and sets **`PATH`** so `semgrep` comes from **`.venv/bin`**. Rebuild with an up-to-date repo; do not re-add `uv tool install semgrep` unless you need it. |
| **`docker push` … `connectex` / timeout to `*.dkr.ecr.*.amazonaws.com:443`** | Local network or firewall is blocking Docker to ECR. Try: different network (e.g. phone hotspot), disable VPN, restart Docker Desktop, check corporate proxy, or run push from a machine/network that allows **HTTPS to ECR**. |

---

## Terraform (optional)

Infrastructure as code for **ECS Fargate + ALB + security groups** lives in **`../terraform/`**. See **[terraform/README.md](../terraform/README.md)** for `init` / `apply` and `terraform.tfvars`.

---

## Scripts reference

| File | Purpose |
|------|---------|
| `scripts/push-ecr.ps1` | Build + push image (Windows). |
| `scripts/push-ecr.sh` | Build + push image (Unix). |
| `.env.example` | Variables to mirror in AWS (no secrets committed). |
