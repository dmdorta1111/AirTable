# Deploying PyBase to Google GKE

> Complete guide for deploying PyBase to Google Kubernetes Engine (GKE)

[![GCP](https://img.shields.io/badge/GCP-GKE-4285F4.svg)](https://cloud.google.com/kubernetes-engine)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.24+-326ce5.svg)](https://kubernetes.io/)
[![Terraform](https://img.shields.io/badge/Terraform-1.0+-7B42BC.svg)](https://www.terraform.io/)

## Overview

This guide provides step-by-step instructions for deploying PyBase to Google Kubernetes Engine (GKE), including cluster creation, VPC configuration, Workload Identity setup, and application deployment. We cover both Google Cloud CLI (gcloud) and Terraform approaches.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       Google Cloud Platform                      │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                      VPC Network                         │    │
│  │                       (10.0.0.0/16)                      │    │
│  │                                                          │    │
│  │  ┌──────────────────┐    ┌──────────────────┐          │    │
│  │  │ Public Subnets   │    │ Private Subnets  │          │    │
│  │  │ (10.0.1.0/24)    │    │ (10.0.2.0/24)    │          │    │
│  │  │                  │    │ (10.0.3.0/24)    │          │    │
│  │  │  ┌────────────┐  │    │                  │          │    │
│  │  │  │    Cloud   │  │    │  ┌────────────┐ │          │    │
│  │  │  │   Router   │  │    │  │    GKE     │ │          │    │
│  │  │  │  (NAT)     │  │    │  │   Nodes    │ │          │    │
│  │  │  └────────────┘  │    │  │            │ │          │    │
│  │  │                  │    │  │ PyBase    │ │          │    │
│  │  │  ┌────────────┐  │    │  │ Pods      │ │          │    │
│  │  │  │  Cloud CDN │  │    │  └────────────┘ │          │    │
│  │  │  │ (Optional) │  │    │                  │          │    │
│  │  │  └────────────┘  │    │  ┌────────────┐ │          │    │
│  │  │                  │    │  │  Cloud SQL │ │          │    │
│  │  │  ┌────────────┐  │    │  │ PostgreSQL │ │          │    │
│  │  │  │   Cloud    │  │    │  └────────────┘ │          │    │
│  │  │  │   Armor    │  │    │                  │          │    │
│  │  │  └────────────┘  │    │  ┌────────────┐ │          │    │
│  │  └──────────────────┘    │  │ Memorystore│ │          │    │
│  │                          │  │   Redis    │ │          │    │
│  │                          │  └────────────┘ │          │    │
│  │                          │                  │          │    │
│  │                          │  ┌────────────┐ │          │    │
│  │                          │  │    GCS     │ │          │    │
│  │                          │  │  Buckets   │ │          │    │
│  │                          │  └────────────┘ │          │    │
│  │                          └──────────────────┘          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  Cloud Load Balancing ─────► Cloud DNS ─────► SSL Certificate    │
└─────────────────────────────────────────────────────────────────┘

Components:
- GKE Cluster (control plane managed by Google)
- GKE Node Pools (Compute Engine instances)
- VPC with subnetworks
- Cloud Router + Cloud NAT for private subnet egress
- Cloud Load Balancing (L7 ILB/GLB) for ingress
- Cloud SQL for PostgreSQL (optional)
- Memorystore for Redis (optional)
- Cloud Storage for object storage (optional)
- Cloud DNS for DNS management (optional)
- Cloud Certificate Manager for TLS (optional)
```

## Prerequisites

Before deploying PyBase to GKE, ensure you have:

- **Google Cloud Account** with appropriate permissions
- **Google Cloud CLI** (gcloud) installed and configured
- **kubectl** v1.24+ installed
- **Helm** v3.0+ (if using Helm deployment)
- **Terraform** v1.0+ (if using Terraform method)
- **Domain name** (for production deployment with custom domain)
- **Project** created in Google Cloud Console

**Installation:**

```bash
# Google Cloud CLI
# macOS
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init

# Linux (Debian/Ubuntu)
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init

# Windows (PowerShell)
(New-Object Net.WebClient).DownloadFile("https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe", "$env:Temp\GoogleCloudSDKInstaller.exe")
$env:Temp\GoogleCloudSDKInstaller.exe

# kubectl
gcloud components install kubectl

# Helm (Linux/macOS)
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Terraform (optional)
# Download from: https://www.terraform.io/downloads

# Verify installations
gcloud version
kubectl version --client
helm version
terraform version  # if using Terraform
```

## Option A: GKE Cluster with gcloud CLI (Recommended for Quick Start)

### Step 1: Create VPC Network

```bash
# Set your project ID and region
export PROJECT_ID=$(gcloud config get-value project)
export REGION=us-central1
export ZONE=${REGION}-a

# Create VPC network
gcloud compute networks create pybase-network \
  --subnet-mode=custom \
  --description="VPC for PyBase deployment"

# Create subnets
gcloud compute networks subnets create pybase-subnet-public \
  --network=pybase-network \
  --region=${REGION} \
  --range=10.0.1.0/24 \
  --description="Public subnet for PyBase"

gcloud compute networks subnets create pybase-subnet-private \
  --network=pybase-network \
  --region=${REGION} \
  --range=10.0.2.0/24 \
  --description="Private subnet for PyBase"

# Create Cloud Router (required for Cloud NAT)
gcloud compute routers create pybase-router \
  --network=pybase-network \
  --region=${REGION}

# Create Cloud NAT (for private subnet egress)
gcloud compute routers nats create pybase-nat \
  --router=pybase-router \
  --router-region=${REGION} \
  --nat-all-subnet-ip-ranges \
  --auto-allocate-nat-external-ips
```

### Step 2: Create GKE Cluster

```bash
# Create GKE cluster with Workload Identity
gcloud container clusters create pybase-production \
  --region=${REGION} \
  --network=pybase-network \
  --subnetwork=pybase-subnet-private \
  --cluster-ipv4-cidr=/20 \
  --services-ipv4-cidr=/20 \
  --num-nodes=3 \
  --machine-type=e2-standard-4 \
  --disk-type=pd-balanced \
  --disk-size=100GB \
  --enable-autoscaling \
  --min-nodes=2 \
  --max-nodes=10 \
  --enable-autorepair \
  --enable-autoupgrade \
  --enable-ip-alias \
  --enable-private-nodes \
  --master-ipv4-cidr=172.16.0.0/28 \
  --enable-master-authorized-networks \
  --master-authorized-networks=0.0.0.0/0 \
  --enable-shielded-nodes \
  --shielded-secure-boot \
  --workload-pool=${PROJECT_ID}.svc.id.goog \
  --logging=SYSTEM,WORKLOADS \
  --monitoring=SYSTEM

# Get cluster credentials
gcloud container clusters get-credentials pybase-production --region=${REGION}

# Verify cluster
kubectl get nodes
kubectl cluster-info
```

### Step 3: Configure Workload Identity

```bash
# Create Google Service Account for PyBase
gcloud iam service-accounts create pybase-sa \
  --description="Service account for PyBase GKE workloads" \
  --display-name="PyBase Service Account"

# Grant necessary permissions
# Cloud Storage (for object storage)
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:pybase-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

# Cloud SQL Viewer (if using Cloud SQL)
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:pybase-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"

# Secret Manager (for storing secrets)
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:pybase-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Create Kubernetes service account
kubectl create serviceaccount pybase-sa -n pybase

# Bind Kubernetes service account to Google service account
gcloud iam service-accounts add-iam-policy-binding pybase-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="serviceAccount:${PROJECT_ID}.svc.id.goog[pybase/pybase-sa]"

# Annotate Kubernetes service account
kubectl annotate serviceaccount pybase-sa \
  -n pybase \
  iam.gke.io/gcp-service-account=pybase-sa@${PROJECT_ID}.iam.gserviceaccount.com
```

### Step 4: Create Storage Class

```bash
# Create pd-balanced StorageClass for better performance/cost
cat > pybase-storage-class.yaml <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: pybase-pd-balanced
provisioner: pd.csi.storage.gke.io
volumeBindingMode: WaitForFirstConsumer
parameters:
  type: pd-balanced
  fstype: ext4
allowVolumeExpansion: true
EOF

kubectl apply -f pybase-storage-class.yaml

# Verify
kubectl get storageclass pybase-pd-balanced
```

### Step 5: Deploy PyBase

```bash
# Create namespace
kubectl create namespace pybase

# Create secrets (REQUIRED)
kubectl create secret generic pybase-api-secret \
  --from-literal=secret-key=$(openssl rand -hex 32) \
  --from-literal=database-url="postgresql+asyncpg://pybase:CHANGE_ME@pybase-postgres:5432/pybase" \
  --from-literal=redis-url="redis://:CHANGE_ME@pybase-redis:6379/0" \
  --from-literal=s3-endpoint-url="https://storage.googleapis.com" \
  --from-literal=s3-access-key="" \
  --from-literal=s3-secret-key="" \
  -n pybase

# Deploy with Kustomize
kubectl apply -k k8s/base

# OR deploy with Helm
helm install pybase helm/pybase -n pybase \
  --set storageClass=pybase-pd-balanced \
  --set serviceAccount.create=false \
  --set serviceAccount.name=pybase-sa
```

### Step 6: Configure Ingress with GKE Ingress

```bash
# Create Ingress with Google Cloud Load Balancing
cat > pybase-ingress.yaml <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: pybase-ingress
  namespace: pybase
  annotations:
    kubernetes.io/ingress.class: "gce"
    kubernetes.io/ingress.global-static-ip-name: "pybase-ip"
    networking.gke.io/managed-certificates: "pybase-cert"
    networking.gke.io/v1beta1.FrontendConfig: "pybase-frontend-config"
spec:
  rules:
  - host: pybase.example.com
    http:
      paths:
      - path: /*
        pathType: ImplementationSpecific
        backend:
          service:
            name: pybase-frontend
            port:
              number: 8080
EOF

kubectl apply -f pybase-ingress.yaml

# Create Managed Certificate
cat > pybase-certificate.yaml <<EOF
apiVersion: networking.gke.io/v1
kind: ManagedCertificate
metadata:
  name: pybase-cert
  namespace: pybase
spec:
  domains:
    - pybase.example.com
EOF

kubectl apply -f pybase-certificate.yaml

# Create FrontendConfig for HTTPS redirect
cat > pybase-frontend-config.yaml <<EOF
apiVersion: networking.gke.io/v1beta1
kind: FrontendConfig
metadata:
  name: pybase-frontend-config
  namespace: pybase
spec:
  redirectToHttps:
    enabled: true
    responseCodeName: MOVED_PERMANENTLY_DEFAULT
EOF

kubectl apply -f pybase-frontend-config.yaml

# Get the Ingress IP
kubectl get ingress pybase-ingress -n pybase
```

## Option B: GKE Cluster with Terraform (Recommended for Production)

### Step 1: Create Terraform Configuration

```bash
# Create project directory
mkdir -p terraform-gke-pybase
cd terraform-gke-pybase

# Create main.tf
cat > main.tf <<EOF
terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
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

provider "google" {
  project = var.project_id
  region  = var.region
}

data "google_client_config" "default" {}

# VPC Network
resource "google_compute_network" "pybase_network" {
  name                            = "${var.cluster_name}-network"
  description                     = "VPC for PyBase deployment"
  auto_create_subnetworks         = false
  mtu                             = 1460
  delete_default_routes_on_create = true
}

# Subnets
resource "google_compute_subnetwork" "pybase_public_subnet" {
  name          = "${var.cluster_name}-public-subnet"
  ip_cidr_range = var.public_subnet_cidr
  region        = var.region
  network       = google_compute_network.pybase_network.id

  log_config {
    aggregation_interval = "INTERVAL_10_MIN"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

resource "google_compute_subnetwork" "pybase_private_subnet" {
  name                     = "${var.cluster_name}-private-subnet"
  ip_cidr_range            = var.private_subnet_cidr
  region                   = var.region
  network                  = google_compute_network.pybase_network.id
  private_ip_google_access = true

  secondary_ip_range {
    range_name    = "${var.cluster_name}-pods"
    ip_cidr_range = var.pods_ip_cidr
  }

  secondary_ip_range {
    range_name    = "${var.cluster_name}-services"
    ip_cidr_range = var.services_ip_cidr
  }

  log_config {
    aggregation_interval = "INTERVAL_10_MIN"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# Cloud Router and NAT
resource "google_compute_router" "pybase_router" {
  name    = "${var.cluster_name}-router"
  region  = var.region
  network = google_compute_network.pybase_network.id
}

resource "google_compute_router_nat" "pybase_nat" {
  name                               = "${var.cluster_name}-nat"
  router                             = google_compute_router.pybase_router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# GKE Cluster
resource "google_container_cluster" "pybase" {
  name     = var.cluster_name
  location = var.region

  network    = google_compute_network.pybase_network.id
  subnetwork = google_compute_subnetwork.pybase_private_subnet.id

  # IPv4 settings
  ip_allocation_policy {
    cluster_secondary_ip_ranges {
      range_name = google_compute_subnetwork.pybase_private_subnet.secondary_ip_range[0].range_name
      ip_cidr_range = google_compute_subnetwork.pybase_private_subnet.secondary_ip_range[0].ip_cidr_range
    }
    cluster_secondary_ip_ranges {
      range_name = google_compute_subnetwork.pybase_private_subnet.secondary_ip_range[1].range_name
      ip_cidr_range = google_compute_subnetwork.pybase_private_subnet.secondary_ip_range[1].ip_cidr_range
    }
  }

  # Cluster configuration
  remove_default_node_pool = true
  initial_node_count       = 1

  # Master version
  min_master_version = var.kubernetes_version

  # Network configuration
  master_authorized_networks_config {
    cidr_blocks {
      cidr_block   = "0.0.0.0/0"
      display_name = "All networks"
    }
  }

  # Private cluster
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = var.master_ipv4_cidr
  }

  # Workload Identity
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  # Shielded nodes
  shielded_nodes {
    enable_secure_boot  = true
    enable_integrity_monitoring = true
  }

  # Logging and monitoring
  logging_config {
    enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
  }

  monitoring_config {
    enable_components = ["SYSTEM_COMPONENTS"]
  }

  # Addons
  addons_config {
    http_load_balancing {
      disabled = false
    }

    network_policy_config {
      disabled = false
    }
  }

  # Network policy
  network_policy {
    enabled  = true
    provider = "CALICO"
  }

  # Maintenance window
  maintenance_policy {
    recurring_window {
      start_time = "2024-01-01T03:00:00Z"
      end_time   = "2024-01-01T06:00:00Z"
      recurrence = "FREQ=WEEKLY;BYDAY=SU,SAT"
    }
  }

  # Release channel
  release_channel {
    channel = "STABLE"
  }

  # Resource labels
  resource_labels = var.labels

  # Timeout
  timeout = "30m"
}

# Node Pool
resource "google_container_node_pool" "pybase_nodes" {
  name     = "${var.cluster_name}-node-pool"
  location = var.region
  cluster  = google_container_cluster.pybase.name

  # Node count
  initial_node_count = var.node_count
  node_count         = var.node_count

  # Autoscaling
  autoscaling {
    min_node_count = var.min_node_count
    max_node_count = var.max_node_count
  }

  # Node configuration
  node_config {
    machine_type = var.machine_type
    disk_size_gb = var.disk_size_gb
    disk_type    = "pd-balanced"

    image_type   = "COS_CONTAINERDoptimized"
    spot         = false

    # OAuth scopes
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]

    # Labels
    labels = {
      role = "worker"
      app  = "pybase"
    }

    # Tags
    tags = ["pybase-node"]

    # Shielded nodes
    shielded_instance_config {
      enable_secure_boot  = true
      enable_integrity_monitoring = true
    }
  }

  # Management
  management {
    auto_repair  = true
    auto_upgrade = true
  }

  # Upgrade settings
  upgrade_settings {
    max_surge       = 1
    max_unavailable = 0
  }

  # Timeout
  timeout = "30m"
}

# Google Service Account for Workload Identity
resource "google_service_account" "pybase_workload_sa" {
  account_id   = "pybase-sa"
  display_name = "PyBase Service Account"
  description  = "Service account for PyBase GKE workloads"
}

# IAM bindings for service account
resource "google_project_iam_member" "pybase_sa_storage_admin" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.pybase_workload_sa.email}"
}

resource "google_project_iam_member" "pybase_sa_cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.pybase_workload_sa.email}"
}

resource "google_project_iam_member" "pybase_sa_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.pybase_workload_sa.email}"
}

# Workload Identity IAM binding
resource "google_service_account_iam_member" "workload_identity_binding" {
  service_account_id = google_service_account.pybase_workload_sa.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[pybase/pybase-sa]"
}

# Kubernetes provider configuration
provider "kubernetes" {
  host                   = "https://${google_container_cluster.pybase.endpoint}"
  cluster_ca_certificate = base64decode(google_container_cluster.pybase.master_auth[0].cluster_ca_certificate)
  token                  = data.google_client_config.default.access_token
}

provider "helm" {
  kubernetes {
    host                   = "https://${google_container_cluster.pybase.endpoint}"
    cluster_ca_certificate = base64decode(google_container_cluster.pybase.master_auth[0].cluster_ca_certificate)
    token                  = data.google_client_config.default.access_token
  }
}

# Kubernetes Service Account for Workload Identity
resource "kubernetes_service_account" "pybase_sa" {
  metadata {
    name      = "pybase-sa"
    namespace = "pybase"
    annotations = {
      "iam.gke.io/gcp-service-account" = google_service_account.pybase_workload_sa.email
    }
  }
}

# StorageClass
resource "kubernetes_storage_class" "pybase_pd_balanced" {
  metadata {
    name = "pybase-pd-balanced"
  }

  storage_provisioner    = "pd.csi.storage.gke.io"
  allow_volume_expansion = true
  volume_binding_mode    = "WaitForFirstConsumer"

  parameters = {
    type  = "pd-balanced"
    fstype = "ext4"
  }
}
EOF

# Create variables.tf
cat > variables.tf <<EOF
variable "project_id" {
  description = "Google Cloud project ID"
  type        = string
}

variable "region" {
  description = "Google Cloud region"
  type        = string
  default     = "us-central1"
}

variable "cluster_name" {
  description = "GKE cluster name"
  type        = string
  default     = "pybase-production"
}

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.28"
}

variable "public_subnet_cidr" {
  description = "Public subnet CIDR"
  type        = string
  default     = "10.0.1.0/24"
}

variable "private_subnet_cidr" {
  description = "Private subnet CIDR"
  type        = string
  default     = "10.0.2.0/24"
}

variable "pods_ip_cidr" {
  description = "Pods IP CIDR"
  type        = string
  default     = "10.1.0.0/16"
}

variable "services_ip_cidr" {
  description = "Services IP CIDR"
  type        = string
  default     = "10.2.0.0/16"
}

variable "master_ipv4_cidr" {
  description = "Master IPv4 CIDR"
  type        = string
  default     = "172.16.0.0/28"
}

variable "machine_type" {
  description = "Node machine type"
  type        = string
  default     = "e2-standard-4"
}

variable "node_count" {
  description = "Initial node count"
  type        = number
  default     = 3
}

variable "min_node_count" {
  description = "Minimum node count"
  type        = number
  default     = 2
}

variable "max_node_count" {
  description = "Maximum node count"
  type        = number
  default     = 10
}

variable "disk_size_gb" {
  description = "Node disk size in GB"
  type        = number
  default     = 100
}

variable "labels" {
  description = "Common labels for all resources"
  type        = map(string)
  default = {
    environment = "production"
    application = "pybase"
    managed_by  = "terraform"
  }
}
EOF

# Create outputs.tf
cat > outputs.tf <<EOF
output "cluster_name" {
  description = "GKE cluster name"
  value       = google_container_cluster.pybase.name
}

output "cluster_endpoint" {
  description = "GKE cluster endpoint"
  value       = google_container_cluster.pybase.endpoint
}

output "cluster_ca_certificate" {
  description     = "GKE cluster CA certificate"
  value           = google_container_cluster.pybase.master_auth[0].cluster_ca_certificate
  sensitive       = true
}

output "network_name" {
  description = "VPC network name"
  value       = google_compute_network.pybase_network.name
}

output "subnetwork_name" {
  description = "Subnetwork name"
  value       = google_compute_subnetwork.pybase_private_subnet.name
}

output "service_account_email" {
  description = "Google service account email"
  value       = google_service_account.pybase_workload_sa.email
}

output "configure_kubectl" {
  description = "Configure kubectl command"
  value       = "gcloud container clusters get-credentials ${google_container_cluster.pybase.name} --region ${var.region}"
}
EOF
```

### Step 2: Deploy Infrastructure with Terraform

```bash
# Initialize Terraform
terraform init

# Plan the deployment
terraform plan -out=tfplan

# Apply the deployment (takes 10-15 minutes)
terraform apply tfplan

# Configure kubectl
gcloud container clusters get-credentials pybase-production --region us-central1

# Verify cluster
kubectl get nodes
kubectl cluster-info
```

### Step 3: Deploy PyBase Application

```bash
# Create namespace
kubectl create namespace pybase

# Create secrets
kubectl create secret generic pybase-api-secret \
  --from-literal=secret-key=$(openssl rand -hex 32) \
  --from-literal=database-url="postgresql+asyncpg://pybase:CHANGE_ME@pybase-postgres:5432/pybase" \
  --from-literal=redis-url="redis://:CHANGE_ME@pybase-redis:6379/0" \
  --from-literal=s3-endpoint-url="https://storage.googleapis.com" \
  --from-literal=s3-access-key="" \
  --from-literal=s3-secret-key="" \
  -n pybase

# Deploy PyBase with Kustomize
kubectl apply -k k8s/base

# OR deploy with Helm
helm install pybase helm/pybase -n pybase \
  --set storageClass=pybase-pd-balanced \
  --set serviceAccount.create=false \
  --set serviceAccount.name=pybase-sa
```

## Using GCP Managed Services

### Cloud SQL for PostgreSQL

```bash
# Create Cloud SQL instance
gcloud sql instances create pybase-postgres \
  --tier=db-custom-2-7680 \
  --cpu=2 \
  --memory=7680MB \
  --region=us-central1 \
  --database-version=POSTGRES_15 \
  --root-password=CHANGE_ME \
  --storage-auto-increase \
  --storage-size=100GB \
  --storage-type=PD_SSD \
  --availability-type=zonal \
  --backup-start-time=03:00 \
  --enable-bin-log \
  --retained-backups=7 \
  --retention-unit=count

# Create database
gcloud sql databases create pybase --instance=pybase-postgres

# Create user
gcloud sql users create pybase \
  --instance=pybase-postgres \
  --password=CHANGE_ME

# Get connection name
gcloud sql instances describe pybase-postgres --format="value(connectionName)"

# Create Cloud SQL client certificate (for secure connections)
gcloud sql ssl client-certs create pybase-client \
  --instance=pybase-postgres

# Update PyBase deployment to use Cloud SQL
kubectl patch secret pybase-api-secret -n pybase \
  --type=json \
  -p='[{"op": "replace", "path": "/data/database-url", "value": "'"$(echo -n "postgresql+asyncpg://pybase:CHANGE_ME@/pybase?host=/cloudsql/pybase-postgres" | base64)"'"}]'

# Disable bundled PostgreSQL
# In Helm values.yaml:
# postgresql:
#   enabled: false
```

### Memorystore for Redis

```bash
# Create Memorystore Redis instance
gcloud redis instances create pybase-redis \
  --region=us-central1 \
  --zone=us-central1-a \
  --redis-version=redis_7_0 \
  --size=2 \
  --tier=STANDARD \
  --memory-size_gb=2 \
  --display-name="PyBase Redis" \
  --connect-mode=DIRECT_PEERING

# Get Redis IP address
gcloud redis instances describe pybase-redis \
  --region=us-central1 \
  --format="value(host)"

# Set up VPC peering (required for Memorystore)
gcloud services enable servicenetworking.googleapis.com

# Create connection for private IP access
gcloud compute addresses create pybase-redis-peering \
  --prefix-length=24 \
  --network=pybase-network \
  --purpose=VPC_PEERING \
  --region=us-central1

# Update PyBase deployment
kubectl patch secret pybase-api-secret -n pybase \
  --type=json \
  -p='[{"op": "replace", "path": "/data/redis-url", "value": "'"$(echo -n "redis://:CHANGE_ME@10.0.3.5:6379/0" | base64)"'"}]'

# Disable bundled Redis
# In Helm values.yaml:
# redis:
#   enabled: false
```

### Cloud Storage for Object Storage

```bash
# Create GCS bucket
gsutil mb -p ${PROJECT_ID} -l us-central1 gs://pybase-production

# Enable versioning
gsutil versioning set on gs://pybase-production

# Set lifecycle policy (optional)
cat > lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {
          "type": "Delete"
        },
        "condition": {
          "age": 90,
          "withState": "ARCHIVED"
        }
      }
    ]
  }
}
EOF

gsutil lifecycle set lifecycle.json gs://pybase-production

# Create service account key (if not using Workload Identity)
gcloud iam service-accounts keys create key.json \
  --iam-account=pybase-sa@${PROJECT_ID}.iam.gserviceaccount.com

# Update PyBase deployment to use GCS
kubectl patch secret pybase-api-secret -n pybase \
  --type=json \
  -p='[{"op": "replace", "path": "/data/s3-endpoint-url", "value": "'"$(echo -n "https://storage.googleapis.com" | base64)"'"}]'

# Disable bundled MinIO
# In Helm values.yaml:
# minio:
#   enabled: false
```

## Security Hardening

### Enable Binary Authorization

```bash
# Enable Binary Authorization
gcloud container clusters update pybase-production \
  --region=us-central1 \
  --binauthz-evaluation-mode=PROJECT_SINGLETON_POLICY_ENFORCE

# Create policy
gcloud container binauthz policy import policy.yaml
```

### Enable Network Policies

```bash
# Network policies are enabled in GKE cluster creation
# Apply PyBase network policies
kubectl apply -f k8s/base/network-policy.yaml
```

### Use Secret Manager

```bash
# Enable Secret Manager API
gcloud services enable secretmanager.googleapis.com

# Store secrets in Secret Manager
echo -n "$(openssl rand -hex 32)" | \
  gcloud secrets create pybase-secret-key --data-file=-

echo -n "postgresql+asyncpg://..." | \
  gcloud secrets create pybase-database-url --data-file=-

# Grant access to secrets
gcloud secrets add-iam-policy-binding pybase-secret-key \
  --member="serviceAccount:pybase-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Access secrets from Kubernetes (requires Secret Manager CSI driver)
# https://cloud.google.com/secret-manager/docs/integrating-with-csi-driver
```

## Monitoring and Observability

### Cloud Monitoring

```bash
# Install Cloud Monitoring agent
# Already enabled in cluster creation

# Create monitoring policies
# Use Google Cloud Console: Monitoring > Policies

# Create dashboards
# Use Google Cloud Console: Monitoring > Dashboards
```

### Cloud Logging

```bash
# View logs
gcloud logging read "resource.type=k8s_container" \
  --limit=50 \
  --format="table(timestamp,resource.labels.container_name,logName)"

# Create log sinks for export
gcloud logging sinks create pybase-logs-sink \
  storage.googleapis.com/pybase-logs \
  --log-filter="resource.type=k8s_container"
```

### Cloud Trace for Distributed Tracing

```bash
# Install Cloud Trace operator
kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/cloud-trace-operator/v0.7.0/config/bundle.yaml

# Configure application to send traces to Cloud Trace
```

## Scaling and Cost Optimization

### Cluster Autoscaler

```bash
# Cluster autoscaler is enabled in cluster creation
# Adjust autoscaling settings
gcloud container clusters update pybase-production \
  --region=us-central1 \
  --min-nodes=2 \
  --max-nodes=20 \
  --enable-autoscaling
```

### Spot Nodes (Preemptible VMs)

```bash
# Create spot node pool
gcloud container node-pools create pybase-spot-pool \
  --cluster=pybase-production \
  --region=us-central1 \
  --machine-type=e2-standard-4 \
  --num-nodes=0 \
  --enable-autoscaling \
  --min-nodes=0 \
  --max-nodes=5 \
  --preemptible \
  --disk-size=100 \
  --disk-type=pd-balanced
```

## Backup and Disaster Recovery

### Cloud SQL Automated Backups

```bash
# Automated backups are enabled (7-day retention)
# Create manual backup
gcloud sql backups create \
  --instance=pybase-postgres \
  --description="Manual backup $(date +%Y%m%d)"

# List backups
gcloud sql backups list --instance=pybase-postgres
```

### Cloud Storage Versioning

```bash
# Versioning is already enabled
# List object versions
gsutil ls -a gs://pybase-production/**
```

## Troubleshooting

### Cluster Connection Issues

```bash
# Verify kubectl context
kubectl config current-context

# Update kubeconfig
gcloud container clusters get-credentials pybase-production --region=us-central1

# Test cluster connectivity
kubectl cluster-info
kubectl get nodes
```

### Workload Identity Issues

```bash
# Check service account
kubectl get sa pybase-sa -n pybase
kubectl describe sa pybase-sa -n pybase

# Verify IAM binding
gcloud iam service-accounts get-iam-policy pybase-sa@${PROJECT_ID}.iam.gserviceaccount.com

# Test Workload Identity
kubectl run -it --rm workload-identity-test --image=google/cloud-sdk:latest \
  --restart=Never --serviceaccount=pybase-sa -n pybase \
  -- gcloud auth list
```

### Load Balancer Issues

```bash
# Check ingress status
kubectl get ingress pybase-ingress -n pybase
kubectl describe ingress pybase-ingress -n pybase

# Check backend services
gcloud compute backend-services list

# Check health checks
gcloud compute health-checks list
```

## Cost Estimation

**Estimated Monthly Costs (us-central1):**

| Component | Configuration | Monthly Cost |
|-----------|--------------|--------------|
| GKE Control Plane | $74/month per cluster | $74 |
| Nodes | 3x e2-standard-4 (On-Demand) | ~$180 |
| Spot Nodes | 2x e2-standard-4 (Preemptible) | ~$45 |
| PD Storage | 3x 100GB pd-balanced | ~$27 |
| Cloud NAT | NAT Gateway + NAT IPs | ~$30 |
| Network Load Balancing | L7 LB | ~$20 |
| Cloud Logging/Monitoring | Basic tier | ~$10 |
| **Total (Minimum)** | | **~$386/month** |

**With GCP Managed Services:**
| Component | Configuration | Monthly Cost |
|-----------|--------------|--------------|
| Cloud SQL | 2 vCPU, 7.5GB RAM | ~$130 |
| Memorystore | 2GB Redis | ~$45 |
| Cloud Storage | 100GB + operations | ~$3 |
| **Total (Managed)** | | **~$564/month** |

## Cleanup

```bash
# Delete PyBase deployment
kubectl delete namespace pybase

# Delete GKE cluster with gcloud
gcloud container clusters delete pybase-production --region=us-central1

# OR delete with Terraform
terraform destroy

# Delete related resources
gcloud compute routers nats delete pybase-nat \
  --router=pybase-router \
  --region=us-central1

gcloud compute routers delete pybase-router --region=us-central1

gcloud compute networks subnets delete pybase-subnet-private --region=us-central1
gcloud compute networks subnets delete pybase-subnet-public --region=us-central1
gcloud compute networks delete pybase-network

# Delete service account
gcloud iam service-accounts delete pybase-sa@${PROJECT_ID}.iam.gserviceaccount.com
```

## Additional Resources

- **[GKE Documentation](https://cloud.google.com/kubernetes-engine/docs)** - Official Google Cloud GKE documentation
- **[gcloud CLI Reference](https://cloud.google.com/sdk/gcloud)** - gcloud CLI tool documentation
- **[Terraform Google Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)** - Terraform Google provider docs
- **[Kubernetes GKE Documentation](https://kubernetes.io/docs/concepts/cluster-administration/cloud-providers/gke/)** - Kubernetes on GKE

## Support

- **Google Cloud Support**: https://cloud.google.com/support
- **Google Cloud Community**: https://cloud.google.com/community
- **PyBase Documentation**: https://pybase.dev/docs
- **GitHub Issues**: https://github.com/pybase/pybase/issues
