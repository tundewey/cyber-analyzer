resource "aws_ecr_repository" "app" {
  count = var.create_ecr_repository ? 1 : 0
  name  = var.ecr_repository_name
}

data "aws_ecr_repository" "app" {
  count = var.create_ecr_repository ? 0 : 1
  name  = var.ecr_repository_name
}

locals {
  ecr_repository_url = var.create_ecr_repository ? aws_ecr_repository.app[0].repository_url : data.aws_ecr_repository.app[0].repository_url
  container_image    = "${local.ecr_repository_url}:${var.image_tag}"
}
