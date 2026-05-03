# Terraform: Cyber Analyzer on AWS (ECS Fargate + ALB)

Creates:

- **Security groups:** Internet → ALB `:80`; ALB → tasks `:8000`
- **Application Load Balancer** + **target group** (HTTP **8000**, health check **`/health`**)
- **ECS Fargate** cluster, task definition, service (container **`cyber-analyzer`**)
- **CloudWatch** log group `/ecs/<project_name>`
- **IAM** task execution role (ECR pull + logs)

Optionally creates **ECR repository** if `create_ecr_repository = true`. If you already use `cyber-analyzer` in ECR, keep `create_ecr_repository = false`.

## Prerequisites

- AWS CLI configured (`aws configure`)
- Terraform >= 1.3
- ECS service-linked role present (`AWSServiceRoleForECS`) — Terraform does not create it; create once per account if missing.

## Quick start

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars — set tokens and keys (never commit this file)

terraform init
terraform plan
terraform apply
```

Outputs include **`alb_url`** — open it in a browser after targets are **healthy** (may take a few minutes).

## Variables

See **`variables.tf`**. Secrets belong in **`terraform.tfvars`** (gitignored).

## Coexisting with manually created resources

If you already created **ECS**, **ALB**, or **target groups** with the same names in the same region, `terraform apply` will **conflict**. Options:

- Use a different **`project_name`** (e.g. `cyber-analyzer-tf`), or  
- **Import** existing resources into state (advanced), or  
- Remove old resources and let Terraform create fresh ones (destructive).

## Push a new image after apply

Build and push from repo root (see parent **`aws/README.md`**):

```powershell
cd ..
.\scripts\push-ecr.ps1 -AwsRegion us-east-1 -EcrRepository cyber-analyzer -ImageTag latest
```

Then either redeploy the ECS service or bump **`image_tag`** and **`terraform apply`** if the tag changed.
