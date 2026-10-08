output "eks_cluster_endpoint" {
  value = aws_eks_cluster.main.endpoint
}

output "ecr_repository_url" {
  value = aws_ecr_repository.app.repository_url
}

output "opensearch_endpoint" {
  value = aws_opensearch_domain.main.endpoint
}

output "aurora_cluster_endpoint" {
  value = aws_rds_cluster.main.endpoint
}

output "irsa_role_arn" {
  value = aws_iam_role.app_irsa_role.arn
}
