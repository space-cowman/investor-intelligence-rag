# Originally created by eksctl's CloudFormation stack; imported here to match exactly.
# NOT managed: sg-0e2de168141675815 (EKS-auto cluster SG), sg-0f86301a844999f33
# (k8s-managed ELB SG), sg-0024423b742b5697e (default, unused) — owned by AWS/K8s, not us.

resource "aws_vpc" "main" {
  cidr_block = "192.168.0.0/16"

  tags = {
    Name                                          = "eksctl-investor-intelligence-cluster/VPC"
    "alpha.eksctl.io/cluster-name"                = var.cluster_name
    "alpha.eksctl.io/cluster-oidc-enabled"        = "true"
    "eksctl.cluster.k8s.io/v1alpha1/cluster-name" = var.cluster_name
  }
}

resource "aws_subnet" "public_1a" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "192.168.0.0/19"
  availability_zone       = "us-east-1a"
  map_public_ip_on_launch = true

  tags = {
    Name                                          = "eksctl-investor-intelligence-cluster/SubnetPublicUSEAST1A"
    "kubernetes.io/role/elb"                      = "1"
    "alpha.eksctl.io/cluster-name"                = var.cluster_name
    "eksctl.cluster.k8s.io/v1alpha1/cluster-name" = var.cluster_name
  }
}

resource "aws_subnet" "public_1d" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "192.168.32.0/19"
  availability_zone       = "us-east-1d"
  map_public_ip_on_launch = true

  tags = {
    Name                                          = "eksctl-investor-intelligence-cluster/SubnetPublicUSEAST1D"
    "kubernetes.io/role/elb"                      = "1"
    "alpha.eksctl.io/cluster-name"                = var.cluster_name
    "eksctl.cluster.k8s.io/v1alpha1/cluster-name" = var.cluster_name
  }
}

resource "aws_subnet" "private_1a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "192.168.64.0/19"
  availability_zone = "us-east-1a"

  tags = {
    Name                                          = "eksctl-investor-intelligence-cluster/SubnetPrivateUSEAST1A"
    "kubernetes.io/role/internal-elb"             = "1"
    "alpha.eksctl.io/cluster-name"                = var.cluster_name
    "eksctl.cluster.k8s.io/v1alpha1/cluster-name" = var.cluster_name
  }
}

resource "aws_subnet" "private_1d" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "192.168.96.0/19"
  availability_zone = "us-east-1d"

  tags = {
    Name                                          = "eksctl-investor-intelligence-cluster/SubnetPrivateUSEAST1D"
    "kubernetes.io/role/internal-elb"             = "1"
    "alpha.eksctl.io/cluster-name"                = var.cluster_name
    "eksctl.cluster.k8s.io/v1alpha1/cluster-name" = var.cluster_name
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name                           = "eksctl-investor-intelligence-cluster/InternetGateway"
    "alpha.eksctl.io/cluster-name" = var.cluster_name
  }
}

resource "aws_eip" "nat" {
  domain = "vpc"
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public_1a.id

  depends_on = [aws_internet_gateway.main]
}

# rtb-09354eeff237591a0 (VPC main route table) left unmanaged: unused, zero
# associations, and aws_default_route_table import hit a provider bug.

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name                           = "eksctl-investor-intelligence-cluster/PublicRouteTable"
    "alpha.eksctl.io/cluster-name" = var.cluster_name
  }
}

resource "aws_route_table" "private_1a" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }

  tags = {
    Name                           = "eksctl-investor-intelligence-cluster/PrivateRouteTableUSEAST1A"
    "alpha.eksctl.io/cluster-name" = var.cluster_name
  }
}

resource "aws_route_table" "private_1d" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }

  tags = {
    Name                           = "eksctl-investor-intelligence-cluster/PrivateRouteTableUSEAST1D"
    "alpha.eksctl.io/cluster-name" = var.cluster_name
  }
}

resource "aws_route_table_association" "public_1a" {
  subnet_id      = aws_subnet.public_1a.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "public_1d" {
  subnet_id      = aws_subnet.public_1d.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private_1a" {
  subnet_id      = aws_subnet.private_1a.id
  route_table_id = aws_route_table.private_1a.id
}

resource "aws_route_table_association" "private_1d" {
  subnet_id      = aws_subnet.private_1d.id
  route_table_id = aws_route_table.private_1d.id
}

resource "aws_security_group" "control_plane" {
  name        = "eksctl-investor-intelligence-cluster-ControlPlaneSecurityGroup-u7sWOYLi3vuf"
  description = "Communication between the control plane and worker nodegroups"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name                           = "eksctl-investor-intelligence-cluster/ControlPlaneSecurityGroup"
    "alpha.eksctl.io/cluster-name" = var.cluster_name
  }
}

resource "aws_security_group" "shared_node" {
  name        = "eksctl-investor-intelligence-cluster-ClusterSharedNodeSecurityGroup-roQFQFmJIqLm"
  description = "Communication between all nodes in the cluster"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name                           = "eksctl-investor-intelligence-cluster/ClusterSharedNodeSecurityGroup"
    "alpha.eksctl.io/cluster-name" = var.cluster_name
  }
}

resource "aws_security_group_rule" "shared_node_self_ingress" {
  type              = "ingress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  security_group_id = aws_security_group.shared_node.id
  self              = true
  description       = "Allow nodes to communicate with each other (all ports)"
}

resource "aws_security_group_rule" "shared_node_eks_cluster_sg_ingress" {
  type                     = "ingress"
  from_port                = 0
  to_port                  = 0
  protocol                 = "-1"
  security_group_id        = aws_security_group.shared_node.id
  source_security_group_id = "sg-0e2de168141675815" # EKS-auto SG, not Terraform-managed
  description              = "Allow managed and unmanaged nodes to communicate with each other (all ports)"
}
