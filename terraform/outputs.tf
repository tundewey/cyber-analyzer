output "alb_dns_name" {
  description = "Open http://<this>/ in a browser (listener on port 80)."
  value       = aws_lb.main.dns_name
}

output "alb_url" {
  description = "Full HTTP URL for the app."
  value       = "http://${aws_lb.main.dns_name}/"
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  value = aws_ecs_service.app.name
}

output "ecr_repository_url" {
  description = "Push images here (same tag as image_tag variable)."
  value       = local.ecr_repository_url
}

output "target_group_arn" {
  value = aws_lb_target_group.app.arn
}
