resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["ab9d0263244dd0326eb67015705a667e79cfe998"] # GitHub's current root CA (Let's Encrypt), computed from the live chain
}

resource "aws_iam_role" "github_actions" {
  name = "investor-intelligence-github-actions"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          # GitHub's sub claim embeds immutable user/repo IDs (not just names)
          # to stop a renamed/transferred repo from inheriting trust: confirmed
          # via CloudTrail as repo:space-cowman@289791280/investor-intelligence-rag@1410160102:...
          "token.actions.githubusercontent.com:sub" = "repo:space-cowman@289791280/investor-intelligence-rag@1410160102:*"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "github_actions_permissions" {
  name = "investor-intelligence-github-actions-permissions"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ECRAuth"
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken"
        Resource = "*"
      },
      {
        Sid    = "ECRPush"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability", "ecr:PutImage", "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart", "ecr:CompleteLayerUpload", "ecr:BatchGetImage",
          "ecr:DescribeRepositories", "ecr:ListTagsForResource",
        ]
        Resource = aws_ecr_repository.app.arn
      },
      {
        Sid      = "TFStateS3"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
        Resource = ["arn:aws:s3:::${local.state_bucket}", "arn:aws:s3:::${local.state_bucket}/*"]
      },
      {
        Sid      = "TFStateLock"
        Effect   = "Allow"
        Action   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem"]
        Resource = "arn:aws:dynamodb:${var.region}:${data.aws_caller_identity.current.account_id}:table/investor-intelligence-tfstate-lock"
      },
      {
        Sid      = "EC2Manage" # ec2:* on * — AWS doesn't support resource-level scoping for most EC2 actions
        Effect   = "Allow"
        Action   = "ec2:*"
        Resource = "*"
      },
      {
        Sid    = "EKSManage"
        Effect = "Allow"
        Action = "eks:*"
        Resource = [
          aws_eks_cluster.main.arn,
          "arn:aws:eks:${var.region}:${data.aws_caller_identity.current.account_id}:nodegroup/${var.cluster_name}/*/*",
          "arn:aws:eks:${var.region}:${data.aws_caller_identity.current.account_id}:addon/${var.cluster_name}/*/*",
          "arn:aws:eks:${var.region}:${data.aws_caller_identity.current.account_id}:access-entry/${var.cluster_name}/*/*/*",
        ]
      },
      {
        Sid      = "IAMManageProjectRoles"
        Effect   = "Allow"
        Action   = "iam:*"
        Resource = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/eksctl-investor-intelligence-*", "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/investor-intelligence-*"]
      },
      {
        Sid      = "IAMOIDCProviders"
        Effect   = "Allow"
        Action   = "iam:*OpenIDConnectProvider*"
        Resource = [aws_iam_openid_connect_provider.github.arn, "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/oidc.eks.${var.region}.amazonaws.com/*"]
      },
      {
        Sid      = "OpenSearchManage"
        Effect   = "Allow"
        Action   = "es:*"
        Resource = [aws_opensearch_domain.main.arn, "${aws_opensearch_domain.main.arn}/*"]
      },
      {
        # global-cluster ARNs have no region segment; the provider checks
        # this automatically on every refresh even though none is used here
        Sid      = "RDSDescribeGlobal"
        Effect   = "Allow"
        Action   = "rds:DescribeGlobalClusters"
        Resource = "arn:aws:rds::${data.aws_caller_identity.current.account_id}:global-cluster:*"
      },
      {
        Sid      = "RDSManage"
        Effect   = "Allow"
        Action   = "rds:*"
        Resource = [aws_rds_cluster.main.arn, aws_rds_cluster_instance.main.arn]
      },
    ]
  })
}

# identity mapping only; RBAC lives in k8s/github-actions-rbac.yaml
resource "aws_eks_access_entry" "github_actions" {
  cluster_name      = aws_eks_cluster.main.name
  principal_arn     = aws_iam_role.github_actions.arn
  kubernetes_groups = ["github-actions-deployer"]
}
