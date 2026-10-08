terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # backend blocks can't reference variables or data sources — Terraform
  # evaluates them before anything else runs, so this one bucket name is the
  # single unavoidable literal in the whole stack.
  backend "s3" {
    bucket         = "investor-intelligence-tfstate-022444447221"
    key            = "investor-intelligence/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "investor-intelligence-tfstate-lock"
    encrypt        = true
  }
}

provider "aws" {
  region = var.region
}

data "aws_caller_identity" "current" {}

locals {
  state_bucket = "investor-intelligence-tfstate-${data.aws_caller_identity.current.account_id}"
}
