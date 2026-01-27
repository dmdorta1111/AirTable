# Deploying PyBase to Amazon EKS

> Complete guide for deploying PyBase to Amazon Elastic Kubernetes Service (EKS)

[![AWS](https://img.shields.io/badge/AWS-EKS-FF9900.svg)](https://aws.amazon.com/eks/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.24+-326ce5.svg)](https://kubernetes.io/)
[![Terraform](https://img.shields.io/badge/Terraform-1.0+-7B42BC.svg)](https://www.terraform.io/)

## Overview

This guide provides step-by-step instructions for deploying PyBase to Amazon EKS, including cluster creation, VPC configuration, IAM roles setup, and application deployment. We cover both AWS CLI/eksctl and Terraform approaches.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                           Amazon AWS                             │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    VPC (10.0.0.0/16)                     │    │
│  │                                                          │    │
│  │  ┌──────────────────┐    ┌──────────────────┐          │    │
│  │  │ Public Subnets   │    │ Private Subnets  │          │    │
│  │  │ (10.0.1.0/24)    │    │ (10.0.2.0/24)    │          │    │
│  │  │                  │    │ (10.0.3.0/24)    │          │    │
│  │  │  ┌────────────┐  │    │                  │          │    │
│  │  │  │   NLB      │  │    │  ┌────────────┐ │          │    │
│  │  │  │ (Ingress)  │  │    │  │   EKS      │ │          │    │
│  │  │  └────────────┘  │    │  │   Nodes    │ │          │    │
│  │  │                  │    │  │            │ │          │    │
│  │  │  ┌────────────┐  │    │  │ PyBase    │ │          │    │
│  │  │  │  NAT GW    │  │    │  │ Pods      │ │          │    │
│  │  │  └────────────┘  │    │  └────────────┘ │          │    │
│  │  └──────────────────┘    │                  │          │    │
│  │                          │  ┌────────────┐ │          │    │
│  │                          │  │   RDS      │ │          │    │
│  │                          │  │ PostgreSQL │ │          │    │
│  │                          │  └────────────┘ │          │    │
│  │                          │                  │          │    │
│  │                          │  ┌────────────┐ │          │    │
│  │                          │  │ElastiCache │ │          │    │
│  │                          │  │   Redis    │ │          │    │
│  │                          │  └────────────┘ │          │    │
│  │                          └──────────────────┘          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  Internet Gateway ─────► Route 53 ─────► SSL Certificate (ACM)   │
└─────────────────────────────────────────────────────────────────┘

Components:
- EKS Cluster (control plane managed by AWS)
- EKS Node Groups (EC2 instances)
- VPC with public/private subnets
- NAT Gateway for private subnet egress
- Network Load Balancer (NLB) for ingress
- AWS RDS for PostgreSQL (optional)
- AWS ElastiCache for Redis (optional)
- S3 for object storage (optional)
- Route 53 for DNS (optional)
- AWS Certificate Manager (ACM) for TLS (optional)
```

## Prerequisites

Before deploying PyBase to EKS, ensure you have:

- **AWS Account** with appropriate permissions
- **AWS CLI** v2+ installed and configured
- **kubectl** v1.24+ installed
- **eksctl** v0.150+ (if using eksctl method)
- **Terraform** v1.0+ (if using Terraform method)
- **Helm** v3.0+ (if using Helm deployment)
- **Domain name** (for production deployment with custom domain)
- **Existing SSH key pair** (for EC2 node access)

**Installation:**

```bash
# AWS CLI v2
# macOS
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /

# Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# eksctl
# macOS
brew tap weaveworks/tap
brew install weaveworks/tap/eksctl

# Linux
curl --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin

# Terraform (optional)
# Download from: https://www.terraform.io/downloads

# Verify installations
aws --version
kubectl version --client
eksctl version
terraform version  # if using Terraform
```

## Option A: EKS Cluster with eksctl (Recommended for Quick Start)

### Step 1: Create VPC and EKS Cluster

Create an EKS cluster with a properly configured VPC:

```bash
# Create cluster configuration
cat > pybase-eks-cluster.yaml <<EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: pybase-production
  region: us-east-1
  version: "1.28"

vpc:
  # CIDR of the VPC
  cidr: 10.0.0.0/16
  # NAT Gateway (highly available - one per AZ)
  nat:
    gateway: HighlyAvailable

  # Cluster endpoint access
  clusterEndpoints:
    publicAccess: true
    privateAccess: true

# Managed node groups
managedNodeGroups:
  - name: pybase-nodes
    # Instance types for PyBase
    instanceType: mixedInstancesPolicy
    # Use mixed instances for cost optimization
    mixedInstancesPolicy:
      instanceTypes: ["t3.large", "t3a.large", "t3.xlarge"]
      # On-Demand base capacity, then spot instances
      onDemandBaseCapacity: 2
      onDemandPercentageAboveBaseCapacity: 50
      spotInstancePools: 3

    # Desired capacity
    desiredCapacity: 3
    minSize: 2
    maxSize: 10

    # Node configuration
    volumeSize: 100
    volumeType: gp3

    # SSH access
    ssh:
      allow: true
      publicKeyPath: ~/.ssh/id_rsa.pub

    # Labels for Kubernetes
    labels:
      role: worker
      app: pybase

    # Taints to dedicate nodes to PyBase
    taints:
      - key: dedicated
        value: pybase
        effect: NO_SCHEDULE

    # Tags for AWS resource organization
    tags:
      Environment: production
      Application: pybase
      CostCenter: engineering

# IAM roles
iam:
  withOIDC: true
  serviceAccounts:
    - metadata:
        name: pybase-sa
        namespace: pybase
      roleName: pybase-irsa
      attachPolicyARNs:
        - arn:aws:iam::aws:policy/AmazonS3FullAccess
        - arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly

# CloudWatch logging
cloudWatch:
  clusterLogging:
    enableTypes: ["*"]
EOF

# Create the cluster (takes 15-20 minutes)
eksctl create cluster -f pybase-eks-cluster.yaml
```

### Step 2: Verify Cluster

```bash
# Verify cluster creation
kubectl get nodes
kubectl cluster-info

# Check AWS resources
aws eks describe-cluster --name pybase-production --region us-east-1
aws ec2 describe-vpcs --filters "Name=cidr,Values=10.0.0.0/16"
```

### Step 3: Install AWS Load Balancer Controller

Required for ingress with AWS Network Load Balancer:

```bash
# Install Helm (if not installed)
# Verify: helm version

# Add the eks-charts repository
helm repo add eks https://aws.github.io/eks-charts
helm repo update

# Create IAM policy for Load Balancer Controller
curl -o iam-policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/main/docs/install/iam_policy.json

aws iam create-policy \
  --policy-name AWSLoadBalancerControllerIAMPolicy \
  --policy-document file://iam-policy.json

# Create IAM role for service account (IRSA)
eksctl create iamserviceaccount \
  --cluster=pybase-production \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --attach-policy-arn=arn:aws:iam::<ACCOUNT_ID>:policy/AWSLoadBalancerControllerIAMPolicy \
  --approve \
  --override-existing-serviceaccounts

# Install the Load Balancer Controller
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=pybase-production \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller

# Verify installation
kubectl get deployment -n kube-system aws-load-balancer-controller
```

### Step 4: Install EBS CSI Driver (for persistent storage)

```bash
# Create IAM policy for CSI driver
aws iam create-policy \
  --policy-name AmazonEBSCSIDriverPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "ec2:CreateSnapshot",
          "ec2:AttachVolume",
          "ec2:DetachVolume",
          "ec2:ModifyVolume",
          "ec2:DescribeAvailabilityZones",
          "ec2:DescribeInstances",
          "ec2:DescribeSnapshots",
          "ec2:DescribeTags",
          "ec2:DescribeVolumes",
          "ec2:DescribeVolumesModifications",
          "ec2:DeleteSnapshot"
        ],
        "Resource": "*"
      },
      {
        "Effect": "Allow",
        "Action": ["ec2:CreateTags"],
        "Resource": ["arn:aws:ec2:*:*:volume/*", "arn:aws:ec2:*:*:snapshot/*"]
      }
    ]
  }'

# Create IAM role for CSI driver
eksctl create iamserviceaccount \
  --cluster=pybase-production \
  --namespace=kube-system \
  --name=ebs-csi-controller-sa \
  --attach-policy-arn=arn:aws:iam::<ACCOUNT_ID>:policy/AmazonEBSCSIDriverPolicy \
  --approve \
  --override-existing-serviceaccounts

# Install CSI driver
kubectl apply -k "github.com/kubernetes-sigs/aws-ebs-csi-driver/deploy/kubernetes/overlays/stable/?ref=master"

# Verify
kubectl get pods -n kube-system -l app=ebs-csi-controller
```

### Step 5: Create Storage Class

```bash
# Create gp3 StorageClass for better performance/cost
cat > pybase-storage-class.yaml <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: pybase-gp3
provisioner: ebs.csi.aws.com
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: gp3
  encrypted: "true"
  iops: "3000"
  throughput: "125"
allowVolumeExpansion: true
EOF

kubectl apply -f pybase-storage-class.yaml

# Verify
kubectl get storageclass pybase-gp3
```

### Step 6: Deploy PyBase

Now deploy PyBase using Kustomize or Helm:

```bash
# Create namespace
kubectl create namespace pybase

# Create secrets (REQUIRED)
kubectl create secret generic pybase-api-secret \
  --from-literal=secret-key=$(openssl rand -hex 32) \
  --from-literal=database-url="postgresql+asyncpg://pybase:CHANGE_ME@pybase-postgres:5432/pybase" \
  --from-literal=redis-url="redis://:CHANGE_ME@pybase-redis:6379/0" \
  --from-literal=s3-endpoint-url="https://s3.amazonaws.com" \
  --from-literal=s3-access-key="YOUR_AWS_ACCESS_KEY" \
  --from-literal=s3-secret-key="YOUR_AWS_SECRET_KEY" \
  -n pybase

# Deploy with Kustomize
kubectl apply -k k8s/base

# OR deploy with Helm
helm install pybase helm/pybase -n pybase \
  --set storageClass=pybase-gp3 \
  --set ingress.annotations."alb\.ingress\.kubernetes\.io/scheme"=internet-facing
```

### Step 7: Configure Ingress with AWS ALB

```bash
# Create Ingress with AWS Load Balancer annotations
cat > pybase-ingress.yaml <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: pybase-ingress
  namespace: pybase
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account:certificate/xxxxxx
    alb.ingress.kubernetes.io/ssl-redirect: '443'
    alb.ingress.kubernetes.io/healthcheck-path: /api/v1/health
    alb.ingress.kubernetes.io/healthcheck-protocol: HTTP
    alb.ingress.kubernetes.io/healthcheck-interval-seconds: '15'
    alb.ingress.kubernetes.io/healthcheck-timeout-seconds: '5'
    alb.ingress.kubernetes.io/healthy-threshold-count: '2'
    alb.ingress.kubernetes.io/unhealthy-threshold-count: '3'
spec:
  rules:
  - host: pybase.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: pybase-frontend
            port:
              number: 8080
EOF

kubectl apply -f pybase-ingress.yaml

# Get the ALB URL
kubectl get ingress pybase-ingress -n pybase
```

## Option B: EKS Cluster with Terraform (Recommended for Production)

### Step 1: Create Terraform Configuration

```bash
# Create project directory
mkdir -p terraform-eks-pybase
cd terraform-eks-pybase

# Create main.tf
cat > main.tf <<EOF
terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.20"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.10"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

# VPC Module
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.cluster_name}-vpc"
  cidr = var.vpc_cidr

  azs             = var.availability_zones
  private_subnets = var.private_subnet_cidrs
  public_subnets  = var.public_subnet_cidrs

  enable_nat_gateway   = true
  single_nat_gateway   = false
  one_nat_gateway_per_az = true

  enable_dns_hostnames = true
  enable_dns_support   = true

  # Kubernetes tags
  public_subnet_tags = {
    "kubernetes.io/role/elb"                    = "1"
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb"           = "1"
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
  }

  tags = var.tags
}

# EKS Module
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  # Cluster endpoint access
  cluster_endpoint_public_access  = true
  cluster_endpoint_private_access = true

  # Cluster addons
  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent = true
    }
    aws-ebs-csi-driver = {
      most_recent = true
    }
  }

  # EKS Managed Node Groups
  eks_managed_node_groups = {
    pybase_nodes = {
      name = "pybase-nodes"

      instance_types = ["t3.large", "t3a.large"]
      capacity_type  = "ON_DEMAND"

      min_size     = 2
      max_size     = 10
      desired_size = 3

      disk_size = 100

      # Taints to dedicate nodes to PyBase
      taints = []
      labels = {
        role = "worker"
        app  = "pybase"
      }

      # IAM role addon policies
      iam_role_additional_policies = {
        AmazonEBSCSIDriverPolicy = aws_iam_policy.ebs_csi_driver.arn
      }

      tags = var.tags
    }

    # Spot instance node group for cost optimization
    pybase_spot_nodes = {
      name = "pybase-spot-nodes"

      instance_types = ["t3.large", "t3a.large", "t3.xlarge"]
      capacity_type  = "SPOT"

      min_size     = 0
      max_size     = 5
      desired_size = 2

      disk_size = 100

      labels = {
        role = "spot-worker"
        app  = "pybase"
      }

      taints = [{
        key    = "spot"
        value  = "true"
        effect = "NO_SCHEDULE"
      }]

      tags = merge(var.tags, { InstanceType = "Spot" })
    }
  }

  # OIDC provider for IRSA
  enable_irsa = true

  tags = var.tags
}

# EBS CSI Driver IAM Policy
resource "aws_iam_policy" "ebs_csi_driver" {
  name        = "${var.cluster_name}-ebs-csi-driver"
  description = "Policy for EBS CSI Driver"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateSnapshot",
          "ec2:AttachVolume",
          "ec2:DetachVolume",
          "ec2:ModifyVolume",
          "ec2:DescribeAvailabilityZones",
          "ec2:DescribeInstances",
          "ec2:DescribeSnapshots",
          "ec2:DescribeTags",
          "ec2:DescribeVolumes",
          "ec2:DescribeVolumesModifications",
          "ec2:DeleteSnapshot"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = ["ec2:CreateTags"]
        Resource = ["arn:aws:ec2:*:*:volume/*", "arn:aws:ec2:*:*:snapshot/*"]
      }
    ]
  })
}

# AWS Load Balancer Controller
module "lb_controller" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.0"

  role_name_prefix = "${var.cluster_name}-lb-controller"

  attach_load_balancer_controller_policy = true

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:aws-load-balancer-controller"]
    }
  }

  tags = var.tags
}

# Kubernetes provider configuration
data "aws_eks_cluster_auth" "cluster" {
  name = module.eks.cluster_id
}

provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)

  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
  }
}

provider "helm" {
  kubernetes {
    host                   = module.eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)

    exec {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
    }
  }
}

# Install AWS Load Balancer Controller
resource "helm_release" "aws_lb_controller" {
  name       = "aws-load-balancer-controller"
  repository = "https://aws.github.io/eks-charts"
  chart      = "aws-load-balancer-controller"
  namespace  = "kube-system"
  version    = "1.5.4"

  set {
    name  = "clusterName"
    value = module.eks.cluster_name
  }

  set {
    name  = "serviceAccount.create"
    value = "false"
  }

  set {
    name  = "serviceAccount.name"
    value = "aws-load-balancer-controller"
  }

  depends_on = [module.lb_controller]
}

# StorageClass for gp3
resource "kubernetes_storage_class" "pybase_gp3" {
  metadata {
    name = "pybase-gp3"
  }

  storage_provisioner    = "ebs.csi.aws.com"
  allow_volume_expansion = true
  volume_binding_mode    = "WaitForFirstConsumer"

  parameters = {
    type       = "gp3"
    iops       = "3000"
    throughput = "125"
    encrypted  = "true"
  }
}
EOF

# Create variables.tf
cat > variables.tf <<EOF
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "pybase-production"
}

variable "cluster_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.28"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "private_subnet_cidrs" {
  description = "Private subnet CIDRs"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDRs"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Environment = "production"
    Application = "pybase"
    ManagedBy   = "terraform"
  }
}
EOF

# Create outputs.tf
cat > outputs.tf <<EOF
output "cluster_id" {
  description = "EKS cluster ID"
  value       = module.eks.cluster_id
}

output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "cluster_security_group_id" {
  description = "Security group ID attached to the EKS cluster"
  value       = module.eks.cluster_security_group_id
}

output "cluster_iam_role_arn" {
  description = "IAM role ARN of the EKS cluster"
  value       = module.eks.cluster_iam_role_arn
}

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "configure_kubectl" {
  description = "Configure kubectl: make sure you're logged in with the correct AWS profile and run the following command to update your kubeconfig"
  value       = "aws eks update-kubeconfig --name ${module.eks.cluster_name} --region ${var.aws_region}"
}
EOF
```

### Step 2: Deploy Infrastructure with Terraform

```bash
# Initialize Terraform
terraform init

# Plan the deployment
terraform plan -out=tfplan

# Apply the deployment (takes 15-20 minutes)
terraform apply tfplan

# Configure kubectl
aws eks update-kubeconfig --name pybase-production --region us-east-1

# Verify cluster
kubectl get nodes
kubectl cluster-info
```

### Step 3: Deploy PyBase Application

```bash
# Create namespace
kubectl create namespace pybase

# Create secrets for AWS services
kubectl create secret generic pybase-api-secret \
  --from-literal=secret-key=$(openssl rand -hex 32) \
  --from-literal=database-url="postgresql+asyncpg://pybase:CHANGE_ME@pybase-postgres:5432/pybase" \
  --from-literal=redis-url="redis://:CHANGE_ME@pybase-redis:6379/0" \
  --from-literal=s3-endpoint-url="https://s3.amazonaws.com" \
  --from-literal=s3-access-key="${AWS_ACCESS_KEY_ID}" \
  --from-literal=s3-secret-key="${AWS_SECRET_ACCESS_KEY}" \
  -n pybase

# Deploy PyBase with Kustomize
kubectl apply -k k8s/base

# OR deploy with Helm
helm install pybase helm/pybase -n pybase \
  --set storageClass=pybase-gp3
```

## Using AWS Managed Services

### Amazon RDS for PostgreSQL

```bash
# Create RDS instance (using AWS CLI or Console)
aws rds create-db-instance \
  --db-instance-identifier pybase-postgres \
  --db-instance-class db.t3.large \
  --engine postgres \
  --engine-version 15.4 \
  --master-username pybase \
  --master-user-password CHANGE_ME \
  --allocated-storage 100 \
  --storage-type gp3 \
  --storage-encrypted \
  --vpc-security-group-ids sg-xxxxx \
  --db-subnet-group-name pybase-subnet-group \
  --backup-retention-period 7 \
  --multi-az

# Get RDS endpoint
aws rds describe-db-instances --db-instance-identifier pybase-postgres \
  --query "DBInstances[0].Endpoint.Address"

# Update PyBase deployment to use external RDS
kubectl patch secret pybase-api-secret -n pybase \
  --type=json \
  -p='[{"op": "replace", "path": "/data/database-url", "value": "'"$(echo -n "postgresql+asyncpg://pybase:CHANGE_ME@pybase-postgres.xxxxx.us-east-1.rds.amazonaws.com:5432/pybase?sslmode=require" | base64)"'"}]'

# Disable bundled PostgreSQL
# In Helm values.yaml:
# postgresql:
#   enabled: false
```

### Amazon ElastiCache for Redis

```bash
# Create ElastiCache Redis cluster
aws elasticache create-cache-cluster \
  --cache-cluster-id pybase-redis \
  --cache-node-type cache.t3.medium \
  --engine redis \
  --engine-version 7.0 \
  --num-cache-nodes 1 \
  --cache-parameter-group-name default.redis7 \
  --security-group-ids sg-xxxxx \
  --cache-subnet-group-name pybase-redis-subnet-group

# Get Redis endpoint
aws elasticache describe-cache-clusters \
  --cache-cluster-id pybase-redis \
  --query "CacheClusters[0].CacheNodes[0].Endpoint.Address"

# Update PyBase deployment
kubectl patch secret pybase-api-secret -n pybase \
  --type=json \
  -p='[{"op": "replace", "path": "/data/redis-url", "value": "'"$(echo -n "redis://:CHANGE_ME@pybase-redis.xxxxx.use1.cache.amazonaws.com:6379/0" | base64)"'"}]'

# Disable bundled Redis
# In Helm values.yaml:
# redis:
#   enabled: false
```

### Amazon S3 for Object Storage

```bash
# Create S3 bucket
aws s3api create-bucket \
  --bucket pybase-production \
  --region us-east-1 \
  --create-bucket-configuration LocationConstraint=us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket pybase-production \
  --versioning-configuration Status=Enabled

# Create IAM policy for S3 access
cat > s3-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::pybase-production",
        "arn:aws:s3:::pybase-production/*"
      ]
    }
  ]
}
EOF

# Attach policy to EKS node role or IAM role for service account
aws iam put-role-policy \
  --role-name pybase-irsa \
  --policy-name PyBaseS3Access \
  --policy-document file://s3-policy.json

# Update PyBase deployment to use S3
kubectl patch secret pybase-api-secret -n pybase \
  --type=json \
  -p='[{"op": "replace", "path": "/data/s3-endpoint-url", "value": "'"$(echo -n "https://s3.amazonaws.com" | base64)"'"}]'

# Disable bundled MinIO
# In Helm values.yaml:
# minio:
#   enabled: false
```

## Security Hardening

### Enable Pod Security Standards

```bash
# Create Pod Security Admission labels
kubectl label namespace pybase \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/warn=restricted
```

### Enable Encryption

```bash
# Enable EBS encryption by default
aws ec2 enable-ebs-encryption-by-default --region us-east-1

# Use KMS for secret encryption
kubectl create secret generic pybase-api-secret \
  --from-literal=secret-key=$(openssl rand -hex 32) \
  --encryption-context="key=value"
```

### Network Policies

```bash
# Enable network policies (already included in base manifests)
kubectl apply -f k8s/base/network-policy.yaml
```

## Monitoring and Observability

### CloudWatch Container Insights

```bash
# Install CloudWatch agent
# See: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-setup-EKS.html

# Enable CloudWatch logging for EKS
aws eks update-cluster-config \
  --name pybase-production \
  --region us-east-1 \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controller","scheduler"],"enabled":true}]}'
```

### AWS X-Ray for Tracing

```bash
# Install X-Ray daemon
kubectl create namespace xray

helm repo add aws-xray https://aws.github.io/eks-charts

helm install aws-xray-daemon aws-xray/aws-xray-daemon \
  -n xray \
  --set xray.region=us-east-1
```

## Scaling and Cost Optimization

### Cluster Autoscaler

```bash
# Install Cluster Autoscaler
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm repo update

helm install cluster-autoscaler autoscaler/cluster-autoscaler \
  -n kube-system \
  --set autoDiscovery.clusterName=pybase-production \
  --set awsRegion=us-east-1 \
  --set rbac.create=true \
  --set cloudProvider=aws \
  --set image.tag=v9.29.0

# Verify
kubectl logs -n kube-system deployment/cluster-autoscaler
```

### Spot Instance Best Practices

- Use dedicated node group for spot instances
- Apply taints to spot nodes
- Configure appropriate Pod Disruption Budgets
- Use capacity-optimized allocation strategy

## Backup and Disaster Recovery

### ETL (EKS Snapshot)

```bash
# List EKS add-ons for backup
aws eks list-addons --cluster-name pybase-production --region us-east-1

# Backup RDS
aws rds create-db-snapshot \
  --db-instance-identifier pybase-postgres \
  --db-snapshot-identifier pybase-backup-$(date +%Y%m%d)

# Backup S3 with versioning (already enabled)
aws s3api put-bucket-versioning \
  --bucket pybase-production \
  --versioning-configuration Status=Enabled

# Cross-region replication for S3
aws s3api put-bucket-replication \
  --bucket pybase-production \
  --replication-configuration file://replication.json
```

## Troubleshooting

### Cluster Connection Issues

```bash
# Verify kubectl context
kubectl config current-context

# Update kubeconfig
aws eks update-kubeconfig --name pybase-production --region us-east-1

# Test cluster connectivity
kubectl cluster-info
kubectl get nodes
```

### IAM Permission Issues

```bash
# Check IAM role for service account
kubectl get sa -n pybase
kubectl describe sa pybase-sa -n pybase

# Test IAM policy
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::ACCOUNT_ID:role/pybase-irsa \
  --action-names s3:GetObject
```

### Load Balancer Issues

```bash
# Check Load Balancer Controller logs
kubectl logs -n kube-system deployment/aws-load-balancer-controller

# Describe ingress
kubectl describe ingress pybase-ingress -n pybase

# Check AWS Load Balancers
aws elbv2 describe-load-balancers | jq '.LoadBalancers[] | select(.DNSName | contains("pybase"))'
```

## Cost Estimation

**Estimated Monthly Costs (us-east-1):**

| Component | Configuration | Monthly Cost |
|-----------|--------------|--------------|
| EKS Control Plane | $72/month per cluster | $72 |
| EC2 Instances | 3x t3.large (On-Demand) | ~$150 |
| EC2 Instances | 2x t3.large (Spot) | ~$40 |
| EBS Volumes | 3x 100GB gp3 | ~$30 |
| NAT Gateway | 3x NAT Gateway | ~$90 |
| Data Transfer | 100GB outbound | ~$9 |
| **Total (Minimum)** | | **~$391/month** |

**With AWS Managed Services:**
| Component | Configuration | Monthly Cost |
|-----------|--------------|--------------|
| RDS PostgreSQL | db.t3.large Multi-AZ | ~$200 |
| ElastiCache Redis | cache.t3.medium | ~$50 |
| **Total (Managed)** | | **~$641/month** |

## Cleanup

```bash
# Delete PyBase deployment
kubectl delete namespace pybase

# Delete EKS cluster with eksctl
eksctl delete cluster -f pybase-eks-cluster.yaml

# OR delete with Terraform
terraform destroy

# Manual cleanup (if needed)
aws eks delete-cluster --name pybase-production --region us-east-1
aws cloudformation delete-stack --stack-name eksctl-pybase-production-cluster
```

## Additional Resources

- **[EKS Documentation](https://docs.aws.amazon.com/eks/)** - Official AWS EKS documentation
- **[eksctl Documentation](https://eksctl.io/)** - eksctl CLI tool documentation
- **[Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)** - Terraform AWS provider docs
- **[Kubernetes AWS Documentation](https://kubernetes.io/docs/concepts/cluster-administration/cloud-providers/aws/)** - Kubernetes on AWS

## Support

- **AWS Support**: https://console.aws.amazon.com/support/home
- **EKS Forums**: https://forums.aws.amazon.com/category.jspa?categoryID=324
- **PyBase Documentation**: https://pybase.dev/docs
- **GitHub Issues**: https://github.com/pybase/pybase/issues
