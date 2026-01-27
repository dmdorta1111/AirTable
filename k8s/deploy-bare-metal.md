# Bare Metal / Local Kubernetes Deployment Guide

> Complete guide for deploying PyBase on bare metal, Minikube, k3s, MicroK8s, and other local Kubernetes distributions

[![Minikube](https://img.shields.io/badge/Minikube-1.30+-32CD60.svg)](https://minikube.sigs.k8s.io/)
[![k3s](https://img.shields.io/badge/k3s-1.27+-FF6600.svg)](https://k3s.io/)
[![MicroK8s](https://img.shields.io/badge/MicroK8s-1.27+-E95420.svg)](https://microk8s.io/)
[![MetalLB](https://img.shields.io/badge/MetalLB-0.13+-2C3E50.svg)](https://metallb.universe.tf/)

## Overview

This guide covers deploying PyBase on bare metal Kubernetes clusters and local distributions including Minikube, k3s, and MicroK8s. These options are ideal for:
- **Development and testing** on local machines
- **On-premises deployments** in air-gapped environments
- **Edge deployments** on resource-constrained hardware
- **Home labs** and self-hosting enthusiasts

### Comparison Table

| Distribution | Resource Usage | Setup Complexity | Best For |
|--------------|----------------|------------------|----------|
| **Minikube** | High (2+ CPU, 4+ Gi RAM) | Low | Local development, testing |
| **k3s** | Low (1 CPU, 1 Gi RAM) | Low | Edge, IoT, resource-constrained |
| **MicroK8s** | Medium (1+ CPU, 2+ Gi RAM) | Low | Workstations, multi-user |
| **Bare Metal** | Variable | High | Production on-premises |

### Prerequisites

**Hardware Requirements (Minimum):**
- **CPU**: 4 cores (2 cores for Minikube, 1 core for k3s/MicroK8s)
- **RAM**: 8 Gi (4 Gi for Minikube, 2 Gi for k3s, 1 Gi for MicroK8s)
- **Storage**: 30 Gi free disk space

**Software Requirements:**
- **Operating System**: Linux, macOS, or Windows with WSL2
- **Docker**: 20.10+ (for Minikube Docker driver)
- **kubectl**: 1.24+ (matching Kubernetes version)
- **Helm**: 3.0+ (optional, for Helm deployments)
- **git**: For cloning PyBase repository

---

## Option A: Minikube (Recommended for Development)

Minikube provides a full-featured local Kubernetes cluster ideal for development and testing.

### 1. Install Minikube

**Linux (Debian/Ubuntu):**
```bash
# Download Minikube binary
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# Verify installation
minikube version
```

**macOS:**
```bash
# Using Homebrew
brew install minikube

# Verify installation
minikube version
```

**Windows (Chocolatey):**
```powershell
# Install using Chocolatey
choco install minikube

# Verify installation
minikube version
```

### 2. Start Minikube Cluster

**Basic startup (Docker driver - Recommended):**
```bash
# Start cluster with Docker driver
minikube start \
  --driver=docker \
  --cpus=4 \
  --memory=8192 \
  --disk-size=40g \
  --kubernetes-version=1.28.0

# Enable required addons
minikube addons enable ingress
minikube addons enable metrics-server
minikube addons enable storage-provisioner

# Verify cluster status
minikube status
kubectl get nodes
```

**Advanced startup (Podman driver):**
```bash
# Start with Podman (alternative to Docker)
minikube start \
  --driver=podman \
  --container-runtime=crio \
  --cpus=4 \
  --memory=8192
```

**Multi-node cluster (for HA testing):**
```bash
# Start with 3 nodes
minikube start \
  --driver=docker \
  --cpus=4 \
  --memory=8192 \
  --nodes=3 \
  --addons=ingress,metrics-server
```

### 3. Configure MetalLB for Ingress

Minikube's ingress addon requires MetalLB for LoadBalancer support:

```bash
# MetalLB is automatically enabled with ingress addon
# Verify MetalLB is running
kubectl get pods -n metallb-system

# Create IPAddressPool for LoadBalancer IPs
cat <<EOF | kubectl apply -f -
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: pybase-pool
  namespace: metallb-system
spec:
  addresses:
  - 192.168.49.100-192.168.49.150
---
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: pybase-advert
  namespace: metallb-system
spec:
  ipAddressPools:
  - pybase-pool
EOF

# Verify IPAddressPool
kubectl get ipaddresspool -n metallb-system
```

**Note:** The IP range `192.168.49.100-150` matches Minikube's default Docker network. Adjust if using a different driver or network.

### 4. Configure Storage Classes

Minikube includes a default StorageClass, but verify it's working:

```bash
# Check default StorageClass
kubectl get storageclass

# Create a custom StorageClass for PyBase (optional)
cat <<EOF | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: pybase-storage
  annotations:
    storageclass.kubernetes.io/is-default-class: "false"
provisioner: rancher.io/local-path
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
EOF

# Set as default (optional)
kubectl patch storageclass pybase-storage \
  -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

### 5. Deploy PyBase

```bash
# Create namespace
kubectl create namespace pybase

# Create secrets
kubectl create secret generic pybase-api-secret \
  --from-literal=secret-key=$(openssl rand -hex 32) \
  --from-literal=database-url="postgresql+asyncpg://pybase:CHANGE_ME@pybase-postgres:5432/pybase" \
  --from-literal=redis-url="redis://:CHANGE_ME@pybase-redis:6379/0" \
  --from-literal=s3-endpoint-url="http://pybase-minio:9000" \
  --from-literal=s3-access-key="minioadmin" \
  --from-literal=s3-secret-key="CHANGE_ME" \
  -n pybase

# Deploy PyBase
kubectl apply -k k8s/base

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=pybase -n pybase --timeout=300s

# Check deployment status
kubectl get all -n pybase
```

### 6. Access PyBase

```bash
# Get Minikube IP
MINIKUBE_IP=$(minikube ip)

# Add to /etc/hosts (Linux/macOS) or C:\Windows\System32\drivers\etc\hosts (Windows)
echo "$MINIKUBE_IP pybase.local" | sudo tee -a /etc/hosts

# Access the application
echo "PyBase is available at: http://pybase.local"
```

**Or use port-forwarding:**
```bash
# Forward API port
kubectl port-forward -n pybase svc/pybase-api 8000:8000

# Forward frontend port
kubectl port-forward -n pybase svc/pybase-frontend 8080:8080

# Access at http://localhost:8080
```

### Minikube-Specific Tips

**Enable Metrics Server for HPA:**
```bash
minikube addons enable metrics-server
kubectl get apiservice v1beta1.metrics.k8s.io
```

**Increase Resources:**
```bash
# Stop cluster and restart with more resources
minikube stop
minikube start --cpus=6 --memory=12288
```

**Persistent Configuration:**
```bash
# Set default values in ~/.minikube/config/profiles/minikube/config.json
{
  "cpus": 4,
  "memory": 8192,
  "driver": "docker",
  "kubernetes-version": "1.28.0"
}
```

---

## Option B: k3s (Recommended for Production Bare Metal)

k3s is a lightweight, certified Kubernetes distribution ideal for production bare metal deployments.

### 1. Install k3s

**Single-node cluster (Quick Start):**
```bash
# Install k3s with latest version
curl -sfL https://get.k3s.io | sh -

# Check status
sudo systemctl status k3s

# Get kubeconfig
sudo cat /etc/rancher/k3s/k3s.yaml
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

# Verify cluster
kubectl get nodes
```

**Multi-node cluster (High Availability):**

**Server (Master) nodes:**
```bash
# On first server
curl -sfL https://get.k3s.io | sh -s - server \
  --cluster-init \
  --tls-san $(hostname -I | awk '{print $1}') \
  --disable traefik

# Get token
sudo cat /var/lib/rancher/k3s/server/node-token
# Output: K10...<token>::server:<node-id>

# On additional servers
curl -sfL https://get.k3s.io | sh -s - server \
  --server https://<first-server-ip>:6443 \
  --token <token-from-first-server> \
  --tls-san $(hostname -I | awk '{print $1}')
```

**Agent (Worker) nodes:**
```bash
# On worker nodes
curl -sfL https://get.k3s.io | K3S_URL=https://<server-ip>:6443 \
  K3S_TOKEN=<token-from-server> sh -
```

### 2. Configure Traefik Ingress (k3s Default)

k3s includes Traefik as the default ingress controller:

```bash
# Verify Traefik is running
kubectl get pods -n kube-system

# Get Traefik LoadBalancer IP
kubectl get svc traefik -n kube-system

# Create Ingress for PyBase
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: pybase-ingress
  namespace: pybase
  annotations:
    traefik.ingress.kubernetes.io/router.entrypoints: web
spec:
  rules:
  - host: pybase.local
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: pybase-frontend
            port:
              number: 8080
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: pybase-api
            port:
              number: 8000
EOF
```

### 3. Configure Local Path Storage

k3s includes Local Path Storage provisioner:

```bash
# Verify StorageClass
kubectl get storageclass

# Create custom StorageClass (optional)
cat <<EOF | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: pybase-local-storage
provisioner: rancher.io/local-path
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
allowVolumeExpansion: true
EOF
```

### 4. Deploy PyBase

```bash
# Create namespace
kubectl create namespace pybase

# Create secrets
kubectl create secret generic pybase-api-secret \
  --from-literal=secret-key=$(openssl rand -hex 32) \
  --from-literal=database-url="postgresql+asyncpg://pybase:CHANGE_ME@pybase-postgres:5432/pybase" \
  --from-literal=redis-url="redis://:CHANGE_ME@pybase-redis:6379/0" \
  --from-literal=s3-endpoint-url="http://pybase-minio:9000" \
  --from-literal=s3-access-key="minioadmin" \
  --from-literal=s3-secret-key="CHANGE_ME" \
  -n pybase

# Deploy PyBase
kubectl apply -k k8s/base

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=pybase -n pybase --timeout=300s
```

### 5. Access PyBase

```bash
# Get server IP
SERVER_IP=$(hostname -I | awk '{print $1}')

# Add to /etc/hosts
echo "$SERVER_IP pybase.local" | sudo tee -a /etc/hosts

# Access the application
echo "PyBase is available at: http://pybase.local"
```

### k3s-Specific Tips

**Disable Traefik and Use MetalLB:**
```bash
# Install k3s without Traefik
curl -sfL https://get.k3s.io | sh -s - server --disable traefik

# Install MetalLB
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/main/config/manifests/metallb-native.yaml

# Configure MetalLB
cat <<EOF | kubectl apply -f -
apiVersion: metallb.io/v1beta2
kind: IPAddressPool
metadata:
  name: pybase-pool
  namespace: metallb-system
spec:
  addresses:
  - $SERVER_IP-$SERVER_IP
---
apiVersion: metallb.io/v1beta2
kind: L2Advertisement
metadata:
  name: pybase-advert
  namespace: metallb-system
spec:
  ipAddressPools:
  - pybase-pool
EOF
```

**Configure k3s for Production:**
```bash
# Edit /etc/rancher/k3s/config.yaml
sudo nano /etc/rancher/k3s/config.yaml

# Add configuration
write-kubeconfig-mode: "0644"
tls-san:
  - pybase.yourdomain.com
  - <your-public-ip>
cluster-domain: "pybase.local"
disable:
  - servicelb
  - traefik

# Restart k3s
sudo systemctl restart k3s
```

**Air-Gapped Installation:**
```bash
# Download k3s binary and images
wget https://github.com/k3s-io/k3s/releases/download/v1.28.3+k3s1/k3s
wget https://github.com/k3s-io/k3s/releases/download/v1.28.3+k3s1/k3s-airgap-images-amd64.tar.gz

# Install manually
sudo mv k3s /usr/local/bin/
sudo chmod +x /usr/local/bin/k3s
sudo mkdir -p /var/lib/rancher/k3s/agent/images/
sudo cp k3s-airgap-images-amd64.tar.gz /var/lib/rancher/k3s/agent/images/

# Install k3s
sudo INSTALL_K3S_SKIP_DOWNLOAD=true ./k3s-install.sh
```

---

## Option C: MicroK8s (Multi-User Workstations)

MicroK8s is a lightweight, pure-upstream Kubernetes developed by Canonical.

### 1. Install MicroK8s

**Linux (Snap):**
```bash
# Install MicroK8s via Snap
sudo snap install microk8s --classic --channel=1.28/stable

# Verify installation
microk8s status --wait-ready

# Add to PATH (add to ~/.bashrc or ~/.zshrc)
echo 'alias kubectl=microk8s kubectl' >> ~/.bashrc
source ~/.bashrc
```

**macOS (Homebrew):**
```bash
# Install Multipass (required for macOS)
brew install --cask multipass

# Install MicroK8s
brew install ubuntu/microk8s/microk8s

# Start cluster
microk8s start
microk8s status --wait-ready
```

**Windows (Snapd):**
```powershell
# Install WSL2 and Ubuntu
wsl --install

# In WSL Ubuntu, install MicroK8s
sudo snap install microk8s --classic
```

### 2. Enable Required Addons

```bash
# Enable ingress (nginx)
microk8s enable ingress

# Enable storage
microk8s enable storage

# Enable metrics server (for HPA)
microk8s enable metrics-server

# Enable DNS (usually enabled by default)
microk8s enable dns

# Verify addons
microk8s status
```

### 3. Configure Storage

```bash
# Verify default StorageClass
microk8s kubectl get storageclass

# Create custom StorageClass for PyBase
cat <<EOF | microk8s kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: pybase-storage
  annotations:
    storageclass.kubernetes.io/is-default-class: "false"
provisioner: microk8s.io/hostpath
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
EOF
```

### 4. Deploy PyBase

```bash
# Create namespace
microk8s kubectl create namespace pybase

# Create secrets
microk8s kubectl create secret generic pybase-api-secret \
  --from-literal=secret-key=$(openssl rand -hex 32) \
  --from-literal=database-url="postgresql+asyncpg://pybase:CHANGE_ME@pybase-postgres:5432/pybase" \
  --from-literal=redis-url="redis://:CHANGE_ME@pybase-redis:6379/0" \
  --from-literal=s3-endpoint-url="http://pybase-minio:9000" \
  --from-literal=s3-access-key="minioadmin" \
  --from-literal=s3-secret-key="CHANGE_ME" \
  -n pybase

# Deploy PyBase
microk8s kubectl apply -k k8s/base

# Wait for pods to be ready
microk8s kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=pybase -n pybase --timeout=300s
```

### 5. Access PyBase

```bash
# Get ingress IP
microk8s kubectl get ingress -n pybase

# Add to /etc/hosts
echo "127.0.0.1 pybase.local" | sudo tee -a /etc/hosts

# Access the application
echo "PyBase is available at: http://pybase.local"
```

### MicroK8s-Specific Tips

**Enable RBAC:**
```bash
# Enable RBAC for production
microk8s enable rbac

# Create admin user
microk8s enable dashboard
microk8s config > ~/.kube/config
```

**Configure Ingress:**
```bash
# Customize ingress configuration
sudo nano /var/snap/microk8s/current/addons/ingress/config

# Reload ingress
microk8s disable ingress
microk8s enable ingress
```

**Increase Resources:**
```bash
# Edit MicroK8s configuration
sudo nano /var/snap/microk8s/current/args/containerd-env

# Add resource limits
CONTAINERD_RUNTIME="runc"
containerd_configure_selinux="--selinux-enabled"

# Restart MicroK8s
microk8s stop
microk8s start
```

---

## Option D: Bare Metal with Kubeadm (Production)

For production bare metal deployments with full control over the cluster.

### 1. Prepare All Nodes

**On all nodes (Ubuntu/Debian):**
```bash
# Disable swap
sudo swapoff -a
sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab

# Load kernel modules
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

sudo modprobe overlay
sudo modprobe br_netfilter

# Set sysctl parameters
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF

sudo sysctl --system

# Install containerd
sudo apt-get update
sudo apt-get install -y containerd

# Configure containerd
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml

# Use systemd cgroup driver
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml

# Restart containerd
sudo systemctl restart containerd
sudo systemctl enable containerd
```

### 2. Install Kubernetes Components

**On all nodes:**
```bash
# Add Kubernetes repository
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl

curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.28/deb/Release.key | \
  sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg

echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.28/deb/ /' | \
  sudo tee /etc/apt/sources.list.d/kubernetes.list

# Install Kubernetes components
sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl

# Pin versions
sudo apt-mark hold kubelet kubeadm kubectl

# Enable kubelet
sudo systemctl enable --now kubelet
```

### 3. Initialize Cluster

**On master node:**
```bash
# Initialize cluster
sudo kubeadm init \
  --pod-network-cidr=10.244.0.0/16 \
  --control-plane-endpoint="$(hostname -I | awk '{print $1}')" \
  --upload-certs

# Save kubeconfig
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

# Verify cluster
kubectl get nodes
```

**On worker nodes:**
```bash
# Join cluster (use output from kubeadm init on master)
sudo kubeadm join <master-ip>:6443 \
  --token <token> \
  --discovery-token-ca-cert-hash sha256:<hash>

# On master, verify nodes
kubectl get nodes
```

### 4. Install CNI Plugin (Calico)

```bash
# Install Calico CNI
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.26.1/manifests/calico.yaml

# Wait for Calico pods
kubectl wait --for=condition=ready pod -l k8s-app=calico-node -n kube-system --timeout=300s

# Verify nodes are Ready
kubectl get nodes
```

### 5. Install MetalLB for LoadBalancer

```bash
# Install MetalLB
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/main/config/manifests/metallb-native.yaml

# Wait for MetalLB pods
kubectl wait --for=condition=ready pod -l app=metallb -n metallb-system --timeout=300s

# Configure MetalLB
cat <<EOF | kubectl apply -f -
apiVersion: metallb.io/v1beta2
kind: IPAddressPool
metadata:
  name: pybase-pool
  namespace: metallb-system
spec:
  addresses:
  - 192.168.1.100-192.168.1.150
---
apiVersion: metallb.io/v1beta2
kind: L2Advertisement
metadata:
  name: pybase-advert
  namespace: metallb-system
spec:
  ipAddressPools:
  - pybase-pool
EOF
```

### 6. Install Nginx Ingress Controller

```bash
# Install Nginx ingress
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.9.4/deploy/static/provider/baremetal/deploy.yaml

# Wait for ingress controller
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=ingress-nginx -n ingress-nginx --timeout=300s

# Verify ingress
kubectl get pods -n ingress-nginx
```

### 7. Configure Storage

```bash
# Install local-path-provisioner
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.26/deploy/local-path-storage.yaml

# Set as default storage class
kubectl patch storageclass local-path \
  -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'

# Verify storage class
kubectl get storageclass
```

### 8. Deploy PyBase

```bash
# Create namespace
kubectl create namespace pybase

# Create secrets
kubectl create secret generic pybase-api-secret \
  --from-literal=secret-key=$(openssl rand -hex 32) \
  --from-literal=database-url="postgresql+asyncpg://pybase:CHANGE_ME@pybase-postgres:5432/pybase" \
  --from-literal=redis-url="redis://:CHANGE_ME@pybase-redis:6379/0" \
  --from-literal=s3-endpoint-url="http://pybase-minio:9000" \
  --from-literal=s3-access-key="minioadmin" \
  --from-literal=s3-secret-key="CHANGE_ME" \
  -n pybase

# Deploy PyBase
kubectl apply -k k8s/base

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=pybase -n pybase --timeout=300s
```

### 9. Access PyBase

```bash
# Get ingress IP
INGRESS_IP=$(kubectl get svc ingress-nginx-controller -n ingress-nginx -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Add to /etc/hosts
echo "$INGRESS_IP pybase.local" | sudo tee -a /etc/hosts

# Access the application
echo "PyBase is available at: http://pybase.local"
```

---

## Storage Classes Configuration

Different distributions use different storage provisioners. Choose the one appropriate for your setup:

### Minikube Storage

```bash
# Default: standard (k8s.io/minikube-hostpath)
kubectl get storageclass

# Create custom StorageClass
cat <<EOF | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: pybase-minikube-storage
provisioner: k8s.io/minikube-hostpath
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
EOF
```

### k3s Local Path Storage

```bash
# Default: local-path (rancher.io/local-path)
kubectl get storageclass

# Configure storage paths
sudo mkdir -p /var/lib/rancher/k3s/storage
sudo chmod 755 /var/lib/rancher/k3s/storage
```

### MicroK8s Hostpath Storage

```bash
# Default: microk8s-hostpath (microk8s.io/hostpath)
microk8s kubectl get storageclass

# Configure storage path
sudo mkdir -p /var/snap/microk8s/common/default-storage
sudo chmod 755 /var/snap/microk8s/common/default-storage
```

### Bare Metal with NFS (Shared Storage)

```bash
# Install NFS provisioner
helm repo add nfs-subdir-external-provisioner https://kubernetes-sigs.github.io/nfs-subdir-external-provisioner/
helm install nfs-subdir-external-provisioner nfs-subdir-external-provisioner/nfs-subdir-external-provisioner \
  --set nfs.server=192.168.1.10 \
  --set nfs.path=/exported/path \
  --set storageClass.default=true

# Create StorageClass
cat <<EOF | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: pybase-nfs-storage
provisioner: cluster.local/nfs-subdir-external-provisioner
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
EOF
```

---

## MetalLB Configuration

MetalLB provides LoadBalancer support for bare metal clusters.

### Layer 2 Mode (Simple)

```bash
# Install MetalLB
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/main/config/manifests/metallb-native.yaml

# Create IPAddressPool
cat <<EOF | kubectl apply -f -
apiVersion: metallb.io/v1beta2
kind: IPAddressPool
metadata:
  name: pybase-l2-pool
  namespace: metallb-system
spec:
  addresses:
  - 192.168.1.100-192.168.1.150
---
apiVersion: metallb.io/v1beta2
kind: L2Advertisement
metadata:
  name: pybase-l2-advert
  namespace: metallb-system
spec:
  ipAddressPools:
  - pybase-l2-pool
EOF
```

### BGP Mode (Advanced)

```bash
# Create BGP peer configuration
cat <<EOF | kubectl apply -f -
apiVersion: metallb.io/v1beta2
kind: BGPPeer
metadata:
  name: pybase-bgp-peer
  namespace: metallb-system
spec:
  myASN: 64500
  peerASN: 64501
  peerAddress: 192.168.1.1
---
apiVersion: metallb.io/v1beta2
kind: IPAddressPool
metadata:
  name: pybase-bgp-pool
  namespace: metallb-system
spec:
  addresses:
  - 192.168.1.100-192.168.1.150
---
apiVersion: metallb.io/v1beta2
kind: BGPAdvertisement
metadata:
  name: pybase-bgp-advert
  namespace: metallb-system
spec:
  ipAddressPools:
  - pybase-bgp-pool
EOF
```

---

## NetworkPolicies Configuration

For bare metal deployments, ensure NetworkPolicies are compatible with your CNI:

### Calico (Recommended)

```bash
# Verify NetworkPolicy support
kubectl get networkpolicy

# PyBase NetworkPolicies work out-of-the-box with Calico
kubectl apply -f k8s/base/network-policy.yaml
```

### Cilium

```bash
# Install Cilium
cilium install

# Enable NetworkPolicy support
cilium config enablePolicyEnforcement=true

# Apply PyBase NetworkPolicies
kubectl apply -f k8s/base/network-policy.yaml
```

### Flannel (No NetworkPolicy Support)

```bash
# Flannel doesn't support NetworkPolicies
# Either use a different CNI or disable NetworkPolicies
kubectl delete networkpolicy pybase-policy -n pybase
```

---

## Monitoring and Observability

### Metrics Server (Required for HPA)

```bash
# Install Metrics Server (if not already installed)
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Verify metrics
kubectl top nodes
kubectl top pods -n pybase
```

### Prometheus and Grafana

```bash
# Install Prometheus Operator
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring --create-namespace

# Access Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# Login: admin / prom-operator
```

---

## Backup and Restore

### Velero (Recommended)

```bash
# Install Velero CLI
wget https://github.com/vmware-tanzu/velero/releases/download/v1.12.0/velero-v1.12.0-linux-amd64.tar.gz
tar -xvf velero-v1.12.0-linux-amd64.tar.gz
sudo mv velero-v1.12.0-linux-amd64/velero /usr/local/bin/

# Install Velero server
velero install \
  --provider aws \
  --plugins velero/velero-plugin-for-aws:v1.8.0 \
  --bucket velero \
  --secret-file ./credentials-velero \
  --use-volume-snapshots=false

# Create backup
velero backup create pybase-backup --include-namespaces pybase

# Restore from backup
velero restore create --from-backup pybase-backup
```

### Manual Backup

```bash
# Backup PostgreSQL
kubectl exec -n pybase pybase-postgres-0 -- pg_dump -U pybase pybase > backup.sql

# Backup MinIO
kubectl exec -n pybase pybase-minio-0 -- sh -c "
  mc mirror /data /backup/$(date +%Y%m%d)
"

# Backup PVCs
kubectl get pvc -n pybase
# Use your backup solution (rsync, tar, etc.)
```

---

## Troubleshooting

### Minikube Issues

**Cluster won't start:**
```bash
# Delete and recreate
minikube delete
minikube start --driver=docker --cpus=4 --memory=8192

# Check logs
minikube logs
```

**Ingress not working:**
```bash
# Verify MetalLB is running
kubectl get pods -n metallb-system

# Check MetalLB logs
kubectl logs -n metallb-system -l app=metallb

# Recreate MetalLB configuration
kubectl delete ipaddresspool -n metallb-system --all
kubectl delete l2advertisement -n metallb-system --all
# Re-apply MetalLB configuration
```

### k3s Issues

**Nodes not ready:**
```bash
# Check k3s service
sudo systemctl status k3s

# Check logs
sudo journalctl -u k3s -f

# Restart k3s
sudo systemctl restart k3s
```

**Storage not working:**
```bash
# Check local-path provisioner
kubectl get pods -n kube-system -l app=local-path-provisioner

# Check provisioner logs
kubectl logs -n kube-system -l app=local-path-provisioner

# Verify storage path
ls -la /var/lib/rancher/k3s/storage/
```

### MicroK8s Issues

**Addons not enabling:**
```bash
# Check MicroK8s status
microk8s status

# Wait for readiness
microk8s status --wait-ready

# Disable and re-enable addon
microk8s disable ingress
microk8s enable ingress
```

**High resource usage:**
```bash
# Limit MicroK8s resources
sudo snap set microk8s cgroup-root=/
sudo snap set microk8s cgroup-limit=memory=4G
microk8s restart
```

### Common Bare Metal Issues

**Pods stuck in Pending state:**
```bash
# Describe pod to see why
kubectl describe pod <pod-name> -n pybase

# Common issues:
# 1. No available nodes
# 2. Insufficient resources
# 3. PVC not bound (check StorageClass)

# Check node resources
kubectl top nodes
kubectl describe node
```

**PVC not binding:**
```bash
# Check PVC events
kubectl describe pvc <pvc-name> -n pybase

# Verify StorageClass
kubectl get storageclass

# Check provisioner pod
kubectl get pods -n kube-system | grep provisioner
```

**Network connectivity:**
```bash
# Test pod-to-pod connectivity
kubectl exec -n pybase <api-pod> -- nc -zv pybase-postgres 5432

# Check NetworkPolicies
kubectl get networkpolicy -n pybase

# Temporarily disable NetworkPolicies for testing
kubectl delete networkpolicy pybase-policy -n pybase
```

---

## Performance Tuning

### Resource Limits

```bash
# Adjust node resources
kubectl edit node <node-name>

# Tune kubelet
sudo nano /etc/default/kubelet
# Add: KUBELET_EXTRA_ARGS="--max-pods=200 --pod-infra-container-image=registry.k8s.io/pause:3.9"

# Restart kubelet
sudo systemctl restart kubelet
```

### Database Tuning

```bash
# Increase PostgreSQL shared_buffers
kubectl edit configmap pybase-postgres-config -n pybase

# Add to init script:
# shared_buffers = 256MB
# effective_cache_size = 1GB
# maintenance_work_mem = 64MB
# checkpoint_completion_target = 0.9
```

### Worker Tuning

```bash
# Adjust Celery worker concurrency
kubectl edit deployment pybase-extraction-worker -n pybase

# Change command:
# --concurrency=4  # Increase for more parallel tasks
```

---

## Security Best Practices

### Firewall Configuration

```bash
# Allow Kubernetes API server (6443)
sudo ufw allow 6443/tcp

# Allow etcd (2379-2380)
sudo ufw allow 2379:2380/tcp

# Allow Kubelet (10250)
sudo ufw allow 10250/tcp

# Allow NodePort services (30000-32767)
sudo ufw allow 30000:32767/tcp
```

### Pod Security Policies

```bash
# Create PodSecurityPolicy
cat <<EOF | kubectl apply -f -
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: pybase-psp
spec:
  privileged: false
  runAsUser:
    rule: MustRunAsNonRoot
  seLinux:
    rule: RunAsAny
  fsGroup:
    rule: RunAsAny
  supplementalGroups:
    rule: RunAsAny
  volumes:
  - configMap
  - downwardAPI
  - emptyDir
  - persistentVolumeClaim
  - secret
  - projected
EOF
```

### Secrets Encryption

```bash
# Enable encryption at rest for k3s
sudo nano /etc/rancher/k3s/config.yaml

# Add:
secrets-encryption: true

# Restart k3s
sudo systemctl restart k3s
```

---

## Production Checklist

Before deploying to production bare metal:

- [ ] **High Availability**: Multi-master cluster with etcd backup
- [ ] **Load Balancer**: External load balancer for control plane
- [ ] **Storage**: Distributed storage (Ceph, NFS, Longhorn)
- [ ] **Monitoring**: Prometheus + Grafana + AlertManager
- [ ] **Logging**: EFK stack (Elasticsearch, Fluentd, Kibana)
- [ ] **Backup**: Velero or similar backup solution
- [ ] **TLS/SSL**: Valid certificates for all endpoints
- [ ] **Firewall**: Proper firewall rules configured
- [ ] **Updates**: Automated security patching strategy
- [ ] **Disaster Recovery**: Documented DR procedures
- [ ] **Resource Monitoring**: Resource quotas and limits defined
- [ ] **NetworkPolicies**: Least-privilege network access
- [ ] **RBAC**: Proper role-based access control
- [ ] **Secrets Management**: Encrypted secrets, consider Vault
- [ ] **Ingress**: Production-grade ingress controller
- [ ] **Autoscaling**: HPA configured and tested

---

## Cost Optimization

For bare metal deployments, optimize for hardware efficiency:

```yaml
# values.yaml for Helm chart
api:
  replicas: 2  # Start with minimum
  resources:
    requests:
      cpu: 200m
      memory: 256Mi
    limits:
      cpu: 1000m
      memory: 1Gi

extractionWorker:
  replicas: 1  # Scale based on workload
  concurrency: 2

postgresql:
  # Use external PostgreSQL for better performance
  enabled: false

redis:
  # Use external Redis for better performance
  enabled: false
```

---

## Upgrading

### Minikube Upgrades

```bash
# Stop Minikube
minikube stop

# Download new version
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# Start with new version
minikube start
```

### k3s Upgrades

```bash
# Upgrade to latest version
curl -sfL https://get.k3s.io | sh -

# Upgrade to specific version
curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="v1.28.3+k3s1" sh -
```

### MicroK8s Upgrades

```bash
# Refresh to latest stable channel
sudo snap refresh microk8s --channel=1.28/stable

# Check for issues
microk8s status
```

---

## Uninstallation

### Minikube Cleanup

```bash
# Delete PyBase deployment
kubectl delete -k k8s/base

# Stop and delete Minikube cluster
minikube stop
minikube delete

# Remove Minikube binary
sudo rm /usr/local/bin/minikube

# Remove Minikube home directory
rm -rf ~/.minikube
```

### k3s Cleanup

```bash
# Delete PyBase deployment
kubectl delete -k k8s/base

# Uninstall k3s
/usr/local/bin/k3s-uninstall.sh

# Remove data directories
sudo rm -rf /etc/rancher/k3s
sudo rm -rf /var/lib/rancher/k3s
```

### MicroK8s Cleanup

```bash
# Delete PyBase deployment
microk8s kubectl delete -k k8s/base

# Remove MicroK8s
sudo snap remove microk8s

# Remove data
sudo rm -rf /var/snap/microk8s
```

---

## Additional Resources

- **[Minikube Documentation](https://minikube.sigs.k8s.io/docs/)** - Official Minikube docs
- **[k3s Documentation](https://docs.k3s.io/)** - Official k3s docs
- **[MicroK8s Documentation](https://microk8s.io/docs)** - Official MicroK8s docs
- **[Kubeadm Documentation](https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/)** - Official kubeadm docs
- **[MetalLB Documentation](https://metallb.universe.tf/)** - LoadBalancer for bare metal
- **[Local Path Provisioner](https://github.com/rancher/local-path-provisioner)** - Local storage for Kubernetes
- **[Kubernetes Documentation](https://kubernetes.io/docs/)** - Official Kubernetes docs

## Support

- **Documentation**: https://pybase.dev/docs
- **Community**: https://github.com/pybase/pybase/discussions
- **Issues**: https://github.com/pybase/pybase/issues

## License

MIT License - see [LICENSE](../LICENSE) for details.
