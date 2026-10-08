resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = aws_iam_role.cluster_service_role.arn
  version  = "1.31"

  bootstrap_self_managed_addons = false # provider default (true) forces replacement if unset

  vpc_config {
    subnet_ids = [
      aws_subnet.public_1a.id,
      aws_subnet.public_1d.id,
      aws_subnet.private_1a.id,
      aws_subnet.private_1d.id,
    ]
    security_group_ids      = [aws_security_group.control_plane.id]
    endpoint_public_access  = true
    endpoint_private_access = false
    public_access_cidrs     = ["0.0.0.0/0"]
  }

  kubernetes_network_config {
    service_ipv4_cidr = "10.100.0.0/16"
  }

  access_config {
    authentication_mode                         = "API_AND_CONFIG_MAP"
    bootstrap_cluster_creator_admin_permissions = true
  }

  enabled_cluster_log_types = []

  tags = {
    Name                           = "eksctl-investor-intelligence-cluster/ControlPlane"
    "alpha.eksctl.io/cluster-name" = var.cluster_name
  }
}

resource "aws_iam_openid_connect_provider" "eks" {
  url             = aws_eks_cluster.main.identity[0].oidc[0].issuer
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["06b25927c42a721631c1efd9431e648fa62e1e39"]

  tags = {
    "alpha.eksctl.io/cluster-name" = var.cluster_name
  }
}

resource "aws_eks_node_group" "app_nodes" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "app-nodes"
  node_role_arn   = aws_iam_role.node_instance_role.arn
  subnet_ids      = [aws_subnet.public_1a.id, aws_subnet.public_1d.id]

  instance_types = ["t3.micro"]
  ami_type       = "AL2023_x86_64_STANDARD"
  capacity_type  = "ON_DEMAND"

  # must stay referenced or Terraform detaches it on apply
  launch_template {
    id      = "lt-0adbab877bf2b9b59"
    version = "1"
  }

  # Option A (active): 2 nodes, paired with Recreate in k8s/deployment.yaml.
  scaling_config {
    min_size     = 2
    max_size     = 2
    desired_size = 2
  }
  # Option B (alternative): 3rd node for spare pod-slot headroom, enabling
  # zero-downtime RollingUpdate in k8s/deployment.yaml instead.
  # scaling_config {
  #   min_size     = 3
  #   max_size     = 3
  #   desired_size = 3
  # }

  update_config {
    max_unavailable = 1
  }

  labels = {
    "alpha.eksctl.io/cluster-name"   = var.cluster_name
    "alpha.eksctl.io/nodegroup-name" = "app-nodes"
  }

  tags = {
    "alpha.eksctl.io/cluster-name"   = var.cluster_name
    "alpha.eksctl.io/nodegroup-name" = "app-nodes"
  }

  lifecycle {
    ignore_changes = [scaling_config[0].desired_size]
  }
}

resource "aws_eks_addon" "coredns" {
  cluster_name  = aws_eks_cluster.main.name
  addon_name    = "coredns"
  addon_version = "v1.11.4-eksbuild.60"

  depends_on = [aws_eks_node_group.app_nodes]
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name  = aws_eks_cluster.main.name
  addon_name    = "kube-proxy"
  addon_version = "v1.31.14-eksbuild.36"
}

resource "aws_eks_addon" "vpc_cni" {
  cluster_name             = aws_eks_cluster.main.name
  addon_name               = "vpc-cni"
  addon_version            = "v1.22.4-eksbuild.3"
  service_account_role_arn = aws_iam_role.vpc_cni_role.arn
}
