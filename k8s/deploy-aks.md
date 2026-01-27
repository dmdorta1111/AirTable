# Deploying PyBase to Azure AKS

> Complete guide for deploying PyBase to Azure Kubernetes Service (AKS)

[![Azure](https://img.shields.io/badge/Azure-AKS-0089D6.svg)](https://azure.microsoft.com/en-us/services/kubernetes-service/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.24+-326ce5.svg)](https://kubernetes.io/)
[![Terraform](https://img.shields.io/badge/Terraform-1.0+-7B42BC.svg)](https://www.terraform.io/)

## Overview

This guide provides step-by-step instructions for deploying PyBase to Azure Kubernetes Service (AKS), including cluster creation, VNet configuration, Azure Active Directory (AAD) integration, and application deployment. We cover both Azure CLI and Terraform approaches.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Microsoft Azure                          │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   Virtual Network (VNet)                 │    │
│  │                      (10.0.0.0/16)                       │    │
│  │                                                          │    │
│  │  ┌──────────────────┐    ┌──────────────────┐          │    │
│  │  │ Public Subnets   │    │ Private Subnets  │          │    │
│  │  │ (10.0.1.0/24)    │    │ (10.0.2.0/24)    │          │    │
│  │  │                  │    │ (10.0.3.0/24)    │          │    │
│  │  │  ┌────────────┐  │    │                  │          │    │
│  │  │  │    Azure   │  │    │  ┌────────────┐ │          │    │
│  │  │  │    Load    │  │    │  │    AKS     │ │          │    │
│  │  │  │ Balancer   │  │    │  │   Cluster  │ │          │    │
│  │  │  │  (Ingress) │  │    │  │            │ │          │    │
│  │  │  └────────────┘  │    │  │            │ │          │    │
│  │  │                  │    │  │  PyBase    │ │          │    │
│  │  │  ┌────────────┐  │    │  │   Pods     │ │          │    │
│  │  │  │Azure Firewall│  │    │  │            │ │          │    │
│  │  │  │  (Optional)│  │    │  └────────────┘ │          │    │
│  │  │  └────────────┘  │    │                  │          │    │
│  │  └──────────────────┘    │  ┌────────────┐ │          │    │
│  │                          │  │    Azure   │ │          │    │
│  │                          │  │ Database   │ │          │    │
│  │                          │  │ PostgreSQL │ │          │    │
│  │                          │  └────────────┘ │          │    │
│  │                          │                  │          │    │
│  │                          │  ┌────────────┐ │          │    │
│  │                          │  │   Azure    │ │          │    │
│  │                          │  │   Cache    │ │          │    │
│  │                          │  │   Redis    │ │          │    │
│  │                          │  └────────────┘ │          │    │
│  │                          │                  │          │    │
│  │                          │  ┌────────────┐ │          │    │
│  │                          │  │   Azure    │ │          │    │
│  │                          │  │   Storage  │ │          │    │
│  │                          │  │   (Blob)   │ │          │    │
│  │                          │  └────────────┘ │          │    │
│  │                          └──────────────────┘          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  Application Gateway ─────► Azure DNS ─────► SSL Certificate     │
└─────────────────────────────────────────────────────────────────┘

Components:
- AKS Cluster (control plane managed by Azure)
- AKS Node Pools (virtual machine scale sets)
- VNet with subnets
- Azure Load Balancer for ingress
- Azure Firewall (optional, for network security)
- Azure Database for PostgreSQL (flexible server) - optional
- Azure Cache for Redis - optional
- Azure Blob Storage for object storage - optional
- Azure DNS for DNS management - optional
- Azure Key Vault for secrets management - optional
- Azure Container Registry (ACR) for container images - optional
- Azure Active Directory (AAD) / Microsoft Entra ID for authentication
```

## Prerequisites

Before deploying PyBase to AKS, ensure you have:

- **Azure Account** with appropriate permissions
- **Azure CLI** installed and configured
- **kubectl** v1.24+ installed
- **Helm** v3.0+ (if using Helm deployment)
- **Terraform** v1.0+ (if using Terraform method)
- **Domain name** (for production deployment with custom domain)
- **Resource Group** created in Azure subscription
- **Service Principal** or **Managed Identity** with appropriate permissions

**Installation:**

```bash
# Azure CLI
# macOS
brew update && brew install azure-cli

# Linux (Ubuntu/Debian)
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Windows (PowerShell)
Invoke-WebRequest -Uri https://aka.ms/installazurecliwindows -OutFile .\AzureCLI.msi
Start-Process msiexec.exe -Wait -ArgumentList '/I AzureCLI.msi /quiet'

# kubectl
# Azure CLI will automatically install compatible kubectl when you run:
az aks install-cli

# Or install manually:
# Linux
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# macOS
brew install kubectl

# Helm (Linux/macOS)
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Terraform (optional)
# Download from: https://www.terraform.io/downloads

# Verify installations
az --version
kubectl version --client
helm version
terraform version  # if using Terraform
```

**Authentication:**

```bash
# Login to Azure
az login

# Set your default subscription
az account set --subscription "YOUR_SUBSCRIPTION_ID"

# Verify subscription
az account show
```

## Option A: AKS Cluster with Azure CLI (Recommended for Quick Start)

### Step 1: Create Resource Group and VNet

```bash
# Set environment variables
export RESOURCE_GROUP="pybase-rg"
export LOCATION="eastus"
export CLUSTER_NAME="pybase-production"
export VNET_NAME="pybase-vnet"
export AKS_SUBNET_NAME="aks-subnet"

# Create resource group
az group create \
  --name ${RESOURCE_GROUP} \
  --location ${LOCATION}

# Create virtual network
az network vnet create \
  --resource-group ${RESOURCE_GROUP} \
  --name ${VNET_NAME} \
  --address-prefixes 10.0.0.0/16 \
  --location ${LOCATION}

# Create subnet for AKS
az network vnet subnet create \
  --resource-group ${RESOURCE_GROUP} \
  --vnet-name ${VNET_NAME} \
  --name ${AKS_SUBNET_NAME} \
  --address-prefixes 10.0.2.0/24

# Get subnet ID for AKS creation
export SUBNET_ID=$(az network vnet subnet show \
  --resource-group ${RESOURCE_GROUP} \
  --vnet-name ${VNET_NAME} \
  --name ${AKS_SUBNET_NAME} \
  --query id -o tsv)

echo "Subnet ID: ${SUBNET_ID}"
```

### Step 2: Create Azure Container Registry (Optional)

```bash
# Create ACR for storing container images
export ACR_NAME="pybaseacr$(openssl rand -hex 3 | head -c 6)"

az acr create \
  --resource-group ${RESOURCE_GROUP} \
  --name ${ACR_NAME} \
  --sku Standard \
  --location ${LOCATION}

# Get ACR login server
export ACR_LOGIN_SERVER=$(az acr show \
  --resource-group ${RESOURCE_GROUP} \
  --name ${ACR_NAME} \
  --query loginServer -o tsv)

echo "ACR Login Server: ${ACR_LOGIN_SERVER}"

# Enable admin account (for testing, use managed identity for production)
az acr update --name ${ACR_NAME} --admin-enabled true

# Get ACR credentials
export ACR_USERNAME=$(az acr credential show \
  --name ${ACR_NAME} \
  --query username -o tsv)

export ACR_PASSWORD=$(az acr credential show \
  --name ${ACR_NAME} \
  --query passwords[0].value -o tsv)

# Login to ACR
az acr login --name ${ACR_NAME}

# Tag and push image (if building locally)
# docker tag pybase:latest ${ACR_LOGIN_SERVER}/pybase:latest
# docker push ${ACR_LOGIN_SERVER}/pybase:latest
```

### Step 3: Create AKS Cluster

```bash
# Create AKS cluster with Azure AD integration
export AKS_VERSION=$(az aks get-versions \
  --location ${LOCATION} \
  --query "max(orchestrators[].orchestratorVersion)" -o tsv)

az aks create \
  --resource-group ${RESOURCE_GROUP} \
  --name ${CLUSTER_NAME} \
  --location ${LOCATION} \
  --kubernetes-version ${AKS_VERSION} \
  --node-count 3 \
  --node-vm-size Standard_DS4_v2 \
  --enable-cluster-autoscaler \
  --min-count 2 \
  --max-count 10 \
  --max-pods 110 \
  --network-plugin azure \
  --network-policy azure \
  --vnet-subnet-id ${SUBNET_ID} \
  --docker-bridge-address 172.17.0.1/16 \
  --dns-service-ip 10.0.0.10 \
  --service-cidr 10.0.0.0/24 \
  --enable-managed-identity \
  --enable-aad \
  --aad-admin-group-object-ids <YOUR_AAD_ADMIN_GROUP_ID> \
  --enable-azure-rbac \
  --enable-secret-rotation \
  --enable-private-cluster false \
  --enable-public-sku true \
  --load-balancer-sku Standard \
  --outbound-type loadBalancer \
  --tags Environment=Production Application=PyBase

# Note: Replace <YOUR_AAD_ADMIN_GROUP_ID> with your Azure AD admin group object ID
# To get your AAD admin group ID:
# az ad group show --group "YourAdminGroupName" --query objectId -o tsv

# Alternative: Create AKS without AAD (not recommended for production)
# az aks create \
#   --resource-group ${RESOURCE_GROUP} \
#   --name ${CLUSTER_NAME} \
#   --location ${LOCATION} \
#   --kubernetes-version ${AKS_VERSION} \
#   --node-count 3 \
#   --node-vm-size Standard_DS4_v2 \
#   --enable-cluster-autoscaler \
#   --min-count 2 \
#   --max-count 10 \
#   --network-plugin azure \
#   --vnet-subnet-id ${SUBNET_ID} \
#   --enable-managed-identity
```

### Step 4: Configure ACR Integration (If Using ACR)

```bash
# Grant AKS managed identity access to ACR
# Get the AKS node resource group
export AKS_NODE_RESOURCE_GROUP=$(az aks show \
  --resource-group ${RESOURCE_GROUP} \
  --name ${CLUSTER_NAME} \
  --query nodeResourceGroup -o tsv)

# Get the AKS managed identity ID
export MANAGED_IDENTITY_ID=$(az aks show \
  --resource-group ${RESOURCE_GROUP} \
  --name ${CLUSTER_NAME} \
  --query identityProfile.kubeletidentity.objectId -o tsv)

# Assign ACRPull role to the managed identity
az role assignment create \
  --assignee ${MANAGED_IDENTITY_ID} \
  --role acrpull \
  --scope $(az acr show --resource-group ${RESOURCE_GROUP} --name ${ACR_NAME} --query id -o tsv)

# Attach ACR to AKS
az aks update \
  --resource-group ${RESOURCE_GROUP} \
  --name ${CLUSTER_NAME} \
  --attach-acr ${ACR_NAME}
```

### Step 5: Get Cluster Credentials and Verify

```bash
# Get cluster credentials
az aks get-credentials \
  --resource-group ${RESOURCE_GROUP} \
  --name ${CLUSTER_NAME}

# Verify cluster connection
kubectl get nodes

# View cluster details
kubectl cluster-info

# View Azure AD pod identity (if enabled)
kubectl get azureidentities
```

### Step 6: Configure Azure AD Integration

Azure Kubernetes Service with Azure AD integration provides:

- **Single sign-on (SSO)** with Azure AD credentials
- **Role-based access control (RBAC)** using Azure AD groups and users
- **Audit logging** of administrative actions

**Verify Azure AD Integration:**

```bash
# Check AAD integration status
az aks show \
  --resource-group ${RESOURCE_GROUP} \
  --name ${CLUSTER_NAME} \
  --query aadProfile -o json

# View current user context
kubectl auth whoami

# Create Azure AD group for cluster admins (if not exists)
export CLUSTER_ADMIN_GROUP_ID=$(az ad group create \
  --display-name "PyBase-K8s-Cluster-Admins" \
  --mail-nickname "pybase-k8s-admins" \
  --query objectId -o tsv)

# Update AKS with the admin group
az aks update \
  --resource-group ${RESOURCE_GROUP} \
  --name ${CLUSTER_NAME} \
  --aad-admin-group-object-ids ${CLUSTER_ADMIN_GROUP_ID}

# Create Azure AD group for cluster developers
export CLUSTER_DEV_GROUP_ID=$(az ad group create \
  --display-name "PyBase-K8s-Developers" \
  --mail-nickname "pybase-k8s-devs" \
  --query objectId -o tsv)

# Assign developer role
# Create a ClusterRole for developers
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: developer
rules:
- apiGroups: ["", "apps", "batch"]
  resources: ["*"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["pods/exec", "pods/log"]
  verbs: ["create"]
EOF

# Create RoleBinding for developer group
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: developer-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: developer
subjects:
- kind: Group
  name: "${CLUSTER_DEV_GROUP_ID}"
  apiGroup: rbac.authorization.k8s.io
EOF
```

**Adding Users to Azure AD Groups:**

```bash
# Add user to cluster admins group
export USER_OBJECT_ID=$(az ad user show \
  --id "user@example.com" \
  --query objectId -o tsv)

az ad group member add \
  --group ${CLUSTER_ADMIN_GROUP_ID} \
  --member-id ${USER_OBJECT_ID}
```

## Option B: AKS Cluster with Terraform (Recommended for Production)

### Step 1: Create Terraform Configuration

```hcl
# main.tf
terraform {
  required_version = ">= 1.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# Resource Group
resource "azurerm_resource_group" "pybase" {
  name     = var.resource_group_name
  location = var.location

  tags = var.tags
}

# Virtual Network
resource "azurerm_virtual_network" "pybase" {
  name                = "${var.prefix}-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.pybase.location
  resource_group_name = azurerm_resource_group.pybase.name

  tags = var.tags
}

# Subnet for AKS
resource "azurerm_subnet" "aks" {
  name                 = "${var.prefix}-aks-subnet"
  resource_group_name  = azurerm_resource_group.pybase.name
  virtual_network_name = azurerm_virtual_network.pybase.name
  address_prefixes     = ["10.0.2.0/24"]
}

# Azure Container Registry (optional)
resource "azurerm_container_registry" "pybase" {
  name                = "${var.prefix}acr${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.pybase.name
  location            = azurerm_resource_group.pybase.location
  sku                 = "Standard"
  admin_enabled       = true

  tags = var.tags
}

# Random string for unique naming
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "pybase" {
  name                = "${var.prefix}-logs"
  location            = azurerm_resource_group.pybase.location
  resource_group_name = azurerm_resource_group.pybase.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = var.tags
}

# AKS Cluster
resource "azurerm_kubernetes_cluster" "pybase" {
  name                = "${var.prefix}-aks"
  location            = azurerm_resource_group.pybase.location
  resource_group_name = azurerm_resource_group.pybase.name
  dns_prefix          = "${var.prefix}-k8s"
  kubernetes_version  = var.kubernetes_version

  # Network configuration
  network_profile {
    network_plugin     = "azure"
    network_policy     = "azure"
    dns_service_ip     = "10.0.0.10"
    docker_bridge_cidr = "172.17.0.1/16"
    service_cidr       = "10.0.0.0/24"
  }

  # Azure AD integration
  identity {
    type = "SystemAssigned"
  }

  azure_active_directory_role_based_access_control {
    managed            = true
    azure_rbac_enabled = true
    admin_group_object_ids = var.aad_admin_group_object_ids
  }

  # Default node pool
  default_node_pool {
    name                = "system"
    vm_size             = var.node_vm_size
    node_count          = var.node_count
    min_count           = var.min_count
    max_count           = var.max_count
    enable_auto_scaling = true
    max_pods            = 110
    os_disk_size_gb     = 100
    os_disk_type        = "Ephemeral"
    vnet_subnet_id      = azurerm_subnet.aks.id

    # Only critical system pods on system node pool
    node_taints = ["CriticalAddonsOnly=true:NoSchedule"]
  }

  # User node pool for PyBase workloads
  node_pool {
    name                = "pybase"
    vm_size             = var.node_vm_size
    node_count          = var.node_count
    min_count           = var.min_count
    max_count           = var.max_count
    enable_auto_scaling = true
    max_pods            = 110
    os_disk_size_gb     = 100
    os_disk_type        = "Managed"
    vnet_subnet_id      = azurerm_subnet.aks.id
  }

  # Monitoring integration
  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.pybase.id
  }

  # Secrets rotation
  key_vault_secrets_provider {
    secret_rotation_enabled = true
  }

  # Outbound traffic
  outbound_type = "loadBalancer"

  tags = var.tags
}

# ACR role assignment for AKS managed identity
resource "azurerm_role_assignment" "aks_acr_pull" {
  scope                = azurerm_container_registry.pybase.id
  role_definition_name = "acrpull"
  principal_id         = azurerm_kubernetes_cluster.pybase.identity[0].principal_id

  depends_on = [azurerm_kubernetes_cluster.pybase]
}
```

```hcl
# variables.tf
variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
  default     = "pybase-rg"
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "eastus"
}

variable "prefix" {
  description = "Prefix for resource names"
  type        = string
  default     = "pybase"
}

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.28.3"
}

variable "node_vm_size" {
  description = "VM size for AKS nodes"
  type        = string
  default     = "Standard_DS4_v2"
}

variable "node_count" {
  description = "Initial number of nodes"
  type        = number
  default     = 3
}

variable "min_count" {
  description = "Minimum number of nodes for autoscaling"
  type        = number
  default     = 2
}

variable "max_count" {
  description = "Maximum number of nodes for autoscaling"
  type        = number
  default     = 10
}

variable "aad_admin_group_object_ids" {
  description = "Azure AD admin group object IDs"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default = {
    Environment = "Production"
    Application = "PyBase"
  }
}
```

```hcl
# outputs.tf
output "resource_group_name" {
  value = azurerm_resource_group.pybase.name
}

output "aks_cluster_name" {
  value = azurerm_kubernetes_cluster.pybase.name
}

output "aks_kube_config" {
  value     = azurerm_kubernetes_cluster.pybase.kube_config_raw
  sensitive = true
}

output "aks_host" {
  value = azurerm_kubernetes_cluster.pybase.kube_config[0].host
}

output "acr_login_server" {
  value = azurerm_container_registry.pybase.login_server
}

output "acr_admin_username" {
  value = azurerm_container_registry.pybase.admin_username
}

output "acr_admin_password" {
  value     = azurerm_container_registry.pybase.admin_password
  sensitive = true
}
```

### Step 2: Deploy with Terraform

```bash
# Initialize Terraform
terraform init

# Validate configuration
terraform validate

# Plan deployment
terraform plan -out=tfplan

# Apply configuration
terraform apply tfplan

# Get AKS credentials
az aks get-credentials \
  --resource-group $(terraform output -raw resource_group_name) \
  --name $(terraform output -raw aks_cluster_name)

# Verify cluster
kubectl get nodes
```

## Optional: Use Azure Managed Services

### Azure Database for PostgreSQL

```bash
# Create Azure Database for PostgreSQL (Flexible Server)
export POSTGRES_SERVER_NAME="pybase-postgres-$(openssl rand -hex 3 | head -c 6)"
export POSTGRES_ADMIN_USER="pybaseadmin"
export POSTGRES_ADMIN_PASSWORD=$(openssl rand -base64 32)

az postgres flexible-server create \
  --resource-group ${RESOURCE_GROUP} \
  --name ${POSTGRES_SERVER_NAME} \
  --location ${LOCATION} \
  --admin-user ${POSTGRES_ADMIN_USER} \
  --admin-password ${POSTGRES_ADMIN_PASSWORD} \
  --sku-name Standard_D4ds_v4 \
  --tier Burstable \
  --storage-size 128 \
  --version 15 \
  --high-availability Disabled

# Create database
az postgres flexible-server db create \
  --resource-group ${RESOURCE_GROUP} \
  --server-name ${POSTGRES_SERVER_NAME} \
  --database-name pybase

# Configure firewall rules (allow AKS subnet)
az postgres flexible-server firewall-rule create \
  --resource-group ${RESOURCE_GROUP} \
  --server-name ${POSTGRES_SERVER_NAME} \
  --name AllowAKSSubnet \
  --start-ip-address 10.0.2.0 \
  --end-ip-address 10.0.2.255

# Get PostgreSQL connection details
export POSTGRES_HOST=$(az postgres flexible-server show \
  --resource-group ${RESOURCE_GROUP} \
  --name ${POSTGRES_SERVER_NAME} \
  --query fullyQualifiedDomainName -o tsv)

export DATABASE_URL="postgresql+asyncpg://${POSTGRES_ADMIN_USER}:${POSTGRES_ADMIN_PASSWORD}@${POSTGRES_HOST}:5432/pybase?sslmode=require"

echo "Database URL: ${DATABASE_URL}"
```

### Azure Cache for Redis

```bash
# Create Azure Cache for Redis
export REDIS_NAME="pybase-redis-$(openssl rand -hex 3 | head -c 6)"

az redis create \
  --resource-group ${RESOURCE_GROUP} \
  --name ${REDIS_NAME} \
  --location ${LOCATION} \
  --sku Basic \
  --vm-size c0 \
  --redis-version 6 \
  --enable-non-ssl-port false

# Get Redis connection details
export REDIS_HOST=$(az redis show \
  --resource-group ${RESOURCE_GROUP} \
  --name ${REDIS_NAME} \
  --query hostName -o tsv)

export REDIS_PORT=6380
export REDIS_PASSWORD=$(az redis list-keys \
  --resource-group ${RESOURCE_GROUP} \
  --name ${REDIS_NAME} \
  --query primaryKey -o tsv)

export REDIS_URL="rediss://:${REDIS_PASSWORD}@${REDIS_HOST}:${REDIS_PORT}/0"

echo "Redis URL: ${REDIS_URL}"
```

### Azure Blob Storage

```bash
# Create Storage Account
export STORAGE_ACCOUNT_NAME="pybasestorage$(openssl rand -hex 3 | head -c 6)"

az storage account create \
  --resource-group ${RESOURCE_GROUP} \
  --name ${STORAGE_ACCOUNT_NAME} \
  --location ${LOCATION} \
  --sku Standard_RAGRS \
  --kind StorageV2 \
  --access-tier Hot \
  --allow-blob-public-access false

# Create container
az storage container create \
  --account-name ${STORAGE_ACCOUNT_NAME} \
  --name pybase \
  --auth-mode login

# Get storage account key
export STORAGE_KEY=$(az storage account keys list \
  --resource-group ${RESOURCE_GROUP} \
  --account-name ${STORAGE_ACCOUNT_NAME} \
  --query '[0].value' -o tsv)

# Set S3-compatible endpoint URL
export S3_ENDPOINT_URL="https://${STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
export S3_ACCESS_KEY=${STORAGE_ACCOUNT_NAME}
export S3_SECRET_KEY=${STORAGE_KEY}

echo "S3 Endpoint: ${S3_ENDPOINT_URL}"
```

### Azure Key Vault for Secrets Management

```bash
# Create Key Vault
export KEY_VAULT_NAME="pybase-kv-$(openssl rand -hex 3 | head -c 6)"

az keyvault create \
  --resource-group ${RESOURCE_GROUP} \
  --name ${KEY_VAULT_NAME} \
  --location ${LOCATION} \
  --enable-purge-protection \
  --enable-soft-delete true

# Grant AKS managed identity access to Key Vault
export KEY_VAULT_ID=$(az keyvault show \
  --resource-group ${RESOURCE_GROUP} \
  --name ${KEY_VAULT_NAME} \
  --query id -o tsv)

az role assignment create \
  --assignee ${MANAGED_IDENTITY_ID} \
  --role "Key Vault Secrets User" \
  --scope ${KEY_VAULT_ID}

# Store secrets in Key Vault
az keyvault secret set \
  --vault-name ${KEY_VAULT_NAME} \
  --name database-url \
  --value "${DATABASE_URL}"

az keyvault secret set \
  --vault-name ${KEY_VAULT_NAME} \
  --name redis-url \
  --value "${REDIS_URL}"

az keyvault secret set \
  --vault-name ${KEY_VAULT_NAME} \
  --name s3-endpoint-url \
  --value "${S3_ENDPOINT_URL}"

az keyvault secret set \
  --vault-name ${KEY_VAULT_NAME} \
  --name s3-access-key \
  --value "${S3_ACCESS_KEY}"

az keyvault secret set \
  --vault-name ${KEY_VAULT_NAME} \
  --name s3-secret-key \
  --value "${S3_SECRET_KEY}"

az keyvault secret set \
  --vault-name ${KEY_VAULT_NAME} \
  --name secret-key \
  --value "$(openssl rand -hex 32)"

# Install Secrets Store CSI Driver
kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/secrets-store-csi-driver/v1.3.2/deploy/rbac-secretproviderclass.yaml

# Install Azure Key Vault provider
kubectl apply -f https://raw.githubusercontent.com/Azure/secrets-store-csi-driver-provider-azure/master/deployment/provider-azure-installer.yaml

# Create SecretProviderClass
cat <<EOF | kubectl apply -f -
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: pybase-keyvault
spec:
  provider: azure
  parameters:
    usePodIdentity: "true"
    keyvaultName: "${KEY_VAULT_NAME}"
    objects:  |
      array:
        - |
          objectName: database-url
          objectType: secret
        - |
          objectName: redis-url
          objectType: secret
        - |
          objectName: s3-endpoint-url
          objectType: secret
        - |
          objectName: s3-access-key
          objectType: secret
        - |
          objectName: s3-secret-key
          objectType: secret
        - |
          objectName: secret-key
          objectType: secret
    tenantId: "$(az account show --query tenantId -o tsv)"
EOF
```

## Deploy PyBase to AKS

### Step 1: Create Namespace and Secrets

```bash
# Create namespace
kubectl create namespace pybase

# Option A: Use Kubernetes secrets (simpler)
kubectl create secret generic pybase-api-secret \
  --from-literal=secret-key="$(openssl rand -hex 32)" \
  --from-literal=database-url="${DATABASE_URL:-postgresql+asyncpg://pybase:CHANGE_ME@pybase-postgres:5432/pybase}" \
  --from-literal=redis-url="${REDIS_URL:-redis://:CHANGE_ME@pybase-redis:6379/0}" \
  --from-literal=s3-endpoint-url="${S3_ENDPOINT_URL:-http://pybase-minio:9000}" \
  --from-literal=s3-access-key="${S3_ACCESS_KEY:-minioadmin}" \
  --from-literal=s3-secret-key="${S3_SECRET_KEY:-CHANGE_ME}" \
  -n pybase

# Option B: Use Azure Key Vault with CSI Driver (recommended for production)
# Define SecretProviderClass in your deployment manifest and reference it
```

### Step 2: Deploy with Kustomize

```bash
# Deploy all resources
kubectl apply -k k8s/base

# Wait for pods to be ready
kubectl wait --for=condition=ready pod \
  -l app.kubernetes.io/name=pybase \
  -n pybase \
  --timeout=300s

# Check deployment status
kubectl get pods -n pybase
kubectl get services -n pybase
kubectl get ingress -n pybase
```

### Step 3: Deploy with Helm (Recommended)

```bash
# Create custom values file for Azure
cat > pybase-azure-values.yaml <<EOF
# Domain configuration
pybase:
  domain: pybase.example.com

# API configuration
api:
  replicas: 3
  image:
    repository: ${ACR_LOGIN_SERVER}/pybase
    tag: latest
  resources:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: 2000m
      memory: 2Gi

# Use external Azure services
postgresql:
  enabled: false

redis:
  enabled: false

minio:
  enabled: false

# External Azure services
externalServices:
  databaseUrl: "${DATABASE_URL}"
  redisUrl: "${REDIS_URL}"
  s3:
    enabled: true
    endpointUrl: "${S3_ENDPOINT_URL}"
    accessKey: "${S3_ACCESS_KEY}"
    secretKey: "${S3_SECRET_KEY}"
    bucketName: "pybase"
    region: "${LOCATION}"

# Ingress configuration
ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
  hosts:
    - host: pybase.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: pybase-tls-cert
      hosts:
        - pybase.example.com

# Azure-specific configuration
azure:
  keyVault:
    enabled: true
    name: "${KEY_VAULT_NAME}"
    tenantId: "$(az account show --query tenantId -o tsv)"
EOF

# Install Helm chart
helm install pybase helm/pybase \
  -n pybase \
  -f pybase-azure-values.yaml \
  --create-namespace

# Wait for deployment
kubectl wait --for=condition=ready pod \
  -l app.kubernetes.io/name=pybase \
  -n pybase \
  --timeout=300s
```

### Step 4: Configure Ingress with Application Gateway (Optional)

```bash
# Enable Application Gateway ingress controller
az aks enable-addons \
  --resource-group ${RESOURCE_GROUP} \
  --name ${CLUSTER_NAME} \
  --addon ingress-appgw \
  --appgw-name pybase-appgw \
  --appgw-subnet-cidr 10.0.1.0/24

# Get Application Gateway public IP
export APPGW_PUB_IP=$(az network application-gateway show \
  --resource-group ${AKS_NODE_RESOURCE_GROUP} \
  --name pybase-appgw \
  --query frontendIPConfigurations[0].publicIPAddress -o tsv)

# Create A record in Azure DNS
az network dns record-set a add-record \
  --resource-group ${RESOURCE_GROUP} \
  --zone-name example.com \
  --record-set-name pybase \
  --ipv4-address ${APPGW_PUB_IP}
```

## Monitoring and Management

### Azure Monitor Integration

```bash
# Enable Azure Monitor for containers
az aks enable-addons \
  --resource-group ${RESOURCE_GROUP} \
  --name ${CLUSTER_NAME} \
  --addon monitoring \
  --workspace-resource-id $(az monitor log-analytics workspace show \
    --resource-group ${RESOURCE_GROUP} \
    --name pybase-logs \
    --query id -o tsv)

# View metrics in Azure Portal
# https://ms.portal.azure.com/#resource/${CLUSTER_ID}/monitor
```

### View Logs and Metrics

```bash
# Container logs
kubectl logs -f -n pybase deployment/pybase-api

# Logs from Azure Monitor
az monitor log-analytics query \
  --workspace $(az monitor log-analytics workspace show \
    --resource-group ${RESOURCE_GROUP} \
    --name pybase-logs \
    --query customerId -o tsv) \
  --analytics-query 'ContainerLog | where ContainerName == "pybase-api" | project TimeGenerated, LogEntry | take 20'
```

### Scale Cluster

```bash
# Manually scale node pool
az aks scale \
  --resource-group ${RESOURCE_GROUP} \
  --name ${CLUSTER_NAME} \
  --node-count 5 \
  --nodepool-name pybase

# Update autoscaling settings
az aks nodepool update \
  --resource-group ${RESOURCE_GROUP} \
  --cluster-name ${CLUSTER_NAME} \
  --name pybase \
  --min-count 3 \
  --max-count 15
```

## Backup and Disaster Recovery

### Azure Backup for AKS

```bash
# Install Velero for AKS backups
curl -LO https://github.com/vmware-tanzu/velero/releases/download/v1.12.0/velero-v1.12.0-linux-amd64.tar.gz
tar -xvf velero-v1.12.0-linux-amd64.tar.gz
sudo mv velero-v1.12.0-linux-amd64/velero /usr/local/bin/

# Create storage account for backups
export BACKUP_STORAGE_ACCOUNT="pybase-backups-$(openssl rand -hex 3 | head -c 6)"

az storage account create \
  --resource-group ${RESOURCE_GROUP} \
  --name ${BACKUP_STORAGE_ACCOUNT} \
  --location ${LOCATION} \
  --sku Standard_LRS \
  --kind StorageV2

# Create blob container
az storage container create \
  --account-name ${BACKUP_STORAGE_ACCOUNT} \
  --name velero \
  --auth-mode login

# Get storage account key
export BACKUP_STORAGE_KEY=$(az storage account keys list \
  --resource-group ${RESOURCE_GROUP} \
  --account-name ${BACKUP_STORAGE_ACCOUNT} \
  --query '[0].value' -o tsv)

# Install Velero
velero install \
  --provider azure \
  --plugins velero/velero-plugin-for-microsoft-azure:v1.12.0 \
  --bucket velero \
  --secret-file <(cat <<EOF
AZURE_SUBSCRIPTION_ID=$(az account show --query id -o tsv)
AZURE_TENANT_ID=$(az account show --query tenantId -o tsv)
AZURE_RESOURCE_GROUP=${RESOURCE_GROUP}
AZURE_CLOUD_NAME=AzurePublicCloud
EOF
) \
  --backup-location-config resourceGroup=${RESOURCE_GROUP},storageAccount=${BACKUP_STORAGE_ACCOUNT},subscriptionId=$(az account show --query id -o tsv) \
  --snapshot-location-config apiTimeout=5m \
  --velero-pod-cpu-request="500m" \
  --velero-pod-mem-request="512Mi" \
  --velero-pod-cpu-limit="2000m" \
  --velero-pod-mem-limit="2Gi"

# Schedule daily backups
velero schedule create daily-backup \
  --schedule="0 2 * * *" \
  --include-namespaces pybase \
  --ttl 720h
```

## Security Best Practices

### Network Security

```bash
# Create Azure Firewall (optional)
az network firewall create \
  --resource-group ${RESOURCE_GROUP} \
  --name pybase-firewall \
  --location ${LOCATION}

# Create network rules
az network firewall network-rule create \
  --resource-group ${RESOURCE_GROUP} \
  --firewall-name pybase-firewall \
  --name allow-aks \
  --collection-name network-rule-collection \
  --priority 100 \
  --action Allow \
  --source-addresses '*' \
  --dest-addresses '*' \
  --dest-ports '*' \
  --protocols Any

# Configure Azure Policy for AKS
az policy assignment create \
  --name "pybase-aks-security" \
  --policy "/providers/Microsoft.Authorization/policyDefinitions/1a5b4dca-0b6f-4cf5-903c-1cace8d11d1c" \
  --scope /subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP} \
  --params '{"effect": {"value": "AuditIfNotExists"}}'
```

### Private AKS Cluster

```bash
# Create private AKS cluster (recommended for production)
az aks create \
  --resource-group ${RESOURCE_GROUP} \
  --name ${CLUSTER_NAME}-private \
  --enable-private-cluster \
  --private-dns-zone /subscriptions/$(az account show --query id -o tsv)/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Network/privateDnsZones/privatelink.${LOCATION}.azmk8s.io \
  --load-balancer-sku Standard \
  --outbound-type userDefinedRouting
```

## Troubleshooting

### Cluster Connection Issues

```bash
# Verify AKS cluster status
az aks show \
  --resource-group ${RESOURCE_GROUP} \
  --name ${CLUSTER_NAME} \
  --query provisioningState -o tsv

# Get diagnostics
az aks diagnostics \
  --resource-group ${RESOURCE_GROUP} \
  --name ${CLUSTER_NAME}

# Reset credentials
az aks get-credentials \
  --resource-group ${RESOURCE_GROUP} \
  --name ${CLUSTER_NAME} \
  --overwrite-existing
```

### Node Pool Issues

```bash
# View node pool status
az aks nodepool list \
  --resource-group ${RESOURCE_GROUP} \
  --cluster-name ${CLUSTER_NAME}

# Get node pool details
az aks nodepool show \
  --resource-group ${RESOURCE_GROUP} \
  --cluster-name ${CLUSTER_NAME} \
  --name pybase

# Scale node pool
az aks nodepool scale \
  --resource-group ${RESOURCE_GROUP} \
  --cluster-name ${CLUSTER_NAME} \
  --name pybase \
  --node-count 5
```

### AAD Integration Issues

```bash
# Check AAD profile
az aks show \
  --resource-group ${RESOURCE_GROUP} \
  --name ${CLUSTER_NAME} \
  --query aadProfile -o json

# List AAD groups
az ad group list --display-name "PyBase*" -o table

# Test AAD login
kubectl auth whoami
```

## Upgrading

### Upgrade AKS Cluster

```bash
# Check available versions
az aks get-versions \
  --location ${LOCATION} \
  --output table

# Upgrade cluster
az aks upgrade \
  --resource-group ${RESOURCE_GROUP} \
  --name ${CLUSTER_NAME} \
  --kubernetes-version 1.29.0

# Monitor upgrade status
az aks show \
  --resource-group ${RESOURCE_GROUP} \
  --name ${CLUSTER_NAME} \
  --query provisioningState -o tsv
```

### Upgrade Node Pool

```bash
# Upgrade node pool OS
az aks nodepool upgrade \
  --resource-group ${RESOURCE_GROUP} \
  --cluster-name ${CLUSTER_NAME} \
  --name pybase \
  --kubernetes-version 1.29.0 \
  --node-image-only
```

## Cost Optimization

```bash
# Enable cluster autoscaler
az aks update \
  --resource-group ${RESOURCE_GROUP} \
  --name ${CLUSTER_NAME} \
  --enable-cluster-autoscaler \
  --min-count 2 \
  --max-count 10

# Use spot instances for non-critical workloads
az aks nodepool add \
  --resource-group ${RESOURCE_GROUP} \
  --cluster-name ${CLUSTER_NAME} \
  --name spot-nodepool \
  --priority Spot \
  --eviction-policy Delete \
  --spot-max-price -1 \
  --enable-cluster-autoscaler \
  --min-count 0 \
  --max-count 5 \
  --node-vm-size Standard_DS4_v2

# Right-size VMs based on actual usage
az aks nodepool update \
  --resource-group ${RESOURCE_GROUP} \
  --cluster-name ${CLUSTER_NAME} \
  --name pybase \
  --node-vm-size Standard_DS3_v2
```

## Uninstalling

### Remove PyBase from AKS

```bash
# Remove Helm deployment
helm uninstall pybase -n pybase

# Remove Kustomize deployment
kubectl delete -k k8s/base

# Remove PVCs (WARNING: This deletes all data)
kubectl delete pvc -n pybase --all

# Delete namespace
kubectl delete namespace pybase
```

### Delete AKS Cluster

```bash
# Delete AKS cluster
az aks delete \
  --resource-group ${RESOURCE_GROUP} \
  --name ${CLUSTER_NAME} \
  --yes

# Delete other resources
az group delete \
  --name ${RESOURCE_GROUP} \
  --yes
```

## Additional Resources

- **[Azure AKS Documentation](https://docs.microsoft.com/azure/aks/)** - Official AKS documentation
- **[Azure AD Integration](https://docs.microsoft.com/azure/aks/azure-ad-integration)** - Azure AD authentication
- **[Azure Policy for AKS](https://docs.microsoft.com/azure/aks/policy-reference)** - Policy enforcement
- **[Helm Chart Documentation](../helm/pybase/README.md)** - Helm chart reference
- **[Main Deployment Guide](../../docs/deployment-guide.md)** - General deployment options
- **[Project Documentation](../../docs/)** - Complete project documentation

## Support

- **Documentation**: https://pybase.dev/docs
- **Community**: https://github.com/pybase/pybase/discussions
- **Issues**: https://github.com/pybase/pybase/issues
- **Azure Support**: https://azure.microsoft.com/support/

## License

MIT License - see [LICENSE](../../LICENSE) for details.
