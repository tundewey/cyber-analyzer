variable "aws_region" {
  type        = string
  description = "AWS region (must match ECR and ECS)."
  default     = "us-east-1"
}

variable "project_name" {
  type        = string
  description = "Prefix for resource names."
  default     = "cyber-analyzer"
}

variable "vpc_id" {
  type        = string
  description = "VPC ID. Leave empty to use the default VPC in the region."
  default     = ""
}

variable "public_subnet_ids" {
  type        = list(string)
  description = "Public subnets for ALB and Fargate tasks (need route to IGW for ECR pulls unless using VPC endpoints). Leave empty to use all subnets in the chosen VPC."
  default     = []
}

variable "create_ecr_repository" {
  type        = bool
  description = "Set true to create the ECR repo. Set false if it already exists (recommended if you already push images there)."
  default     = false
}

variable "ecr_repository_name" {
  type        = string
  description = "ECR repository name for the container image."
  default     = "cyber-analyzer"
}

variable "image_tag" {
  type        = string
  description = "Image tag deployed by ECS (e.g. latest)."
  default     = "latest"
}

variable "task_cpu" {
  type        = number
  description = "Fargate task CPU units (1024 = 1 vCPU)."
  default     = 1024
}

variable "task_memory" {
  type        = number
  description = "Fargate task memory (MiB). Use at least 2048 for Semgrep."
  default     = 2048
}

variable "desired_count" {
  type        = number
  description = "Number of ECS tasks to run."
  default     = 1
}

variable "assign_public_ip" {
  type        = bool
  description = "Assign public IP to Fargate tasks (needed for default VPC + ECR without NAT/endpoints)."
  default     = true
}

variable "environment" {
  type        = string
  description = "Passed to the container as ENVIRONMENT (use production for deployed app)."
  default     = "production"
}

variable "semgrep_app_token" {
  type        = string
  description = "SEMGREP_APP_TOKEN for the container (required for Analyze to work)."
  default     = ""
  sensitive   = true
}

variable "openrouter_api_key" {
  type        = string
  description = "OPENROUTER_API_KEY (leave empty if using OpenAI instead)."
  default     = ""
  sensitive   = true
}

variable "openai_api_key" {
  type        = string
  description = "OPENAI_API_KEY (leave empty if using OpenRouter instead)."
  default     = ""
  sensitive   = true
}

variable "openrouter_max_tokens" {
  type        = string
  description = "Optional OPENROUTER_MAX_TOKENS (e.g. 3500)."
  default     = "4096"
}

variable "health_check_path" {
  type        = string
  description = "ALB target group health check path."
  default     = "/health"
}
