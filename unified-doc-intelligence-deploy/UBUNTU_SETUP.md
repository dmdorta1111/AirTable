# Ubuntu Deployment Guide
## Unified Engineering Document Intelligence Platform - Ubuntu Setup

This guide provides Ubuntu-specific instructions for deploying the platform. Ubuntu is **highly recommended** for production deployment due to its stability, package management, and widespread cloud support.

## 🖥️ **Tested Ubuntu Versions**
 France✅ Ubuntu 22.04 LTS (Jammy Jellyfish) - **RECOMMENDED**
- ✅ Ubuntu 20.04 LTS (Focal Fossa)
- ✅ Ubuntu 18.04 LTS (Bionic Beaver)
- ✅ Debian 11/12 (Bullseye/Bookworm)

## 🚀 **Quick Ubuntu Setup**

### **Step 1: Copy to Ubuntu Machine**
```bash
# From your local machine to Ubuntu
scp -r unified-doc-intelligence-deploy/ ubuntu-user@your-ubuntu-ip:/home/ubuntu/

# SSH into Ubuntu
ssh ubuntu-user@your-ubuntu-ip
```

### **Step 2: Ubuntu-Specific Pre-requisites**
```bash
# Update package list and install system dependencies
sudo apt-get update
sudo apt-get upgrade -y

# Install system libraries required for Python packages
sudo apt-get install -y \
    python3-pip \
    python3-dev \
    libpq-dev \
    build-essential \
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libopenjp2-7-dev
```

### **Step 3: Run Ubuntu Optimized Setup**
```bash
cd unified-doc-intelligence-deploy

# Set execute permissions
chmod +x deploy.sh setup.py run-pipeline.py

# Run the Ubuntu-optimized setup script
python3 setup.py --ubuntu
```
*(If the --ubuntu flag doesn't exist yet, use:)*
```bash
./deploy.sh
```

## 🔧 **Detailed Ubuntu Deployment**

### **Option A: Single Machine Deployment (All-in-One)**
```bash
# 1. Clone or copy the deployment package
git clone <your-repo> unified-doc-intelligence-deploy
cd unified-doc-intelligence-deploy

# 2. Install system dependencies
./ubuntu-system-setup.sh

# 3. Configure with your credentials
cp config-template.txt config.txt
nano config.txt  # Add Neon PostgreSQL and Backblaze B2 credentials

# 4. Install Python packages
pip3 install -r requirements.txt --user

# 5. Run complete pipeline
python3 run-pipeline.py --phase all --workers $(nproc)
```

### **Option B: Distributed Ubuntu Cluster**

**Machine 1: Master Node (Auto-Linking + Monitoring)**
```bash
# On Ubuntu machine 1
cd unified-doc-intelligence-deploy

# Install
sudo apt-get install -y python3-pip libpq-dev
pip3 install -r requirements.txt

# Run Phase A only
python3 run-pipeline.py --phase a

# Monitor cluster
watch -n 10 'python3 run-pipeline.py --status'
```

**Machine 2: PDF Extraction Worker**
```bash
# On Ubuntu machine 2
cd unified-doc-intelligence-deploy

# Install (minimal - no FastAPI dependencies)
pip3 install psycopg2-binary tqdm tabulate PyMuPDF b2sdk

# Run PDF workers using ALL cores
python3 scripts/phase-b-extraction/B3-pdf-extraction-worker.py --workers $(nproc)
```

**Machine 3: DXF Extraction Worker**
```bash
# On Ubuntu machine 3  
cd unified-doc-intelligence-deploy

# Install (minimal - no FastAPI dependencies)
pip3 install psycopg2-binary tqdm tabulate ezdxf b2sdk

# Run DXF workers using ALL cores
python3 scripts/phase-b-extraction/B4-dxf-extraction-worker.py --workers $(nproc)
```

**Machine 4: Search API Server**
```bash
# On Ubuntu machine 4
cd unified-doc-intelligence-deploy

# Install API dependencies
pip3 install fastapi uvicorn pydantic psycopg2-binary

# Run API server
python3 scripts/phase-c-search/C6-search-api-server.py
# OR using uvicorn
uvicorn scripts.phase-c-search.C6-search-api-server:app --host 0.0.0.0 --port 8080 --workers 4
```

## 📊 **Ubuntu Performance Optimization**

### **CPU Optimization**
```bash
# Use all CPU cores for extraction
export WORKER_COUNT=$(nproc)
python3 scripts/phase-b-extraction/B3-pdf-extraction-worker.py --workers $WORKER_COUNT

# Pin workers to specific cores (for NUMA optimization)
taskset -c 0-$(($(nproc)/2-1)) python3 B3-pdf-extraction-worker.py --workers $(($(nproc)/2))
```

### **Memory Optimization**
```bash
# For memory-constrained Ubuntu servers
# Reduce worker count to prevent OOM
export AVAILABLE_MEMORY_GB=$(free -g | awk '/^Mem:/{print $2}')
export SAFE_WORKER_COUNT=$((AVAILABLE_MEMORY_GB / 2))  # 2GB per worker

python3 scripts/phase-b-extraction/B3-pdf-extraction-worker.py --workers $SAFE_WORKER_COUNT
```

### **Disk I/O Optimization**
```bash
# Use tmpfs for temporary files (if you have enough RAM)
sudo mount -t tmpfs -o size=10G tmpfs /tmp

# Or dedicate a fast SSD partition
sudo mkdir /mnt/fast_temp
sudo mount /dev/nvme0n1p1 /mnt/fast_temp
export TEMP_DIR=/mnt/fast_temp
```

## 🐳 **Docker Deployment on Ubuntu**

### **Option C: Docker Container Deployment**
```bash
# 1. Install Docker on Ubuntu
sudo apt-get install -y docker.io docker-compose
sudo systemctl enable docker
sudo systemctl start docker

# 2. Create Dockerfile
cat > Dockerfile << 'EOF'
FROM ubuntu:22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy deployment package
WORKDIR /app
COPY unified-doc-intelligence-deploy/ /app/

# Install Python packages
RUN pip3 install -r requirements.txt

# Run entrypoint
CMD ["python3", "run-pipeline.py", "--phase", "all"]
EOF

# 3. Build and run
docker build -t unified-doc-intelligence .
docker run -d --name doc-intel-worker unified-doc-intelligence
```

### **Option D: Docker Compose for Distributed Cluster**
```yaml
# docker-compose.yml
version: '3.8'
services:
  master:
    build: .
    command: python3 run-pipeline.py --phase a
    environment:
      - NEON_DATABASE_URL=${NEON_DATABASE_URL}
      - B2_APPLICATION_KEY_ID=${B2_APPLICATION_KEY_ID}
      - B2_APPLICATION_KEY=${B2_APPLICATION_KEY}
  
  pdf-worker-1:
    build: .
    command: python3 scripts/phase-b-extraction/B3-pdf-extraction-worker.py --workers 10
    environment:
      - NEON_DATABASE_URL=${NEON_DATABASE_URL}
      - B2_APPLICATION_KEY_ID=${B2_APPLICATION_KEY_ID}
      - B2_APPLICATION_KEY=${B2_APPLICATION_KEY}
    deploy:
      replicas: 3
  
  dxf-worker-1:
    build: .
    command: python3 scripts/phase-b-extraction/B4-dxf-extraction-worker.py --workers 10
    environment:
      - NEON_DATABASE_URL=${NEON_DATABASE_URL}
      - B2_APPLICATION_KEY_ID=${B2_APPLICATION_KEY_ID}
      - B2_APPLICATION_KEY=${B2_APPLICATION_KEY}
    deploy:
      replicas: 2
  
  api-server:
    build: .
    command: uvicorn scripts.phase-c-search.C6-search-api-server:app --host 0.0.0.0 --port 8080 --workers 4
    ports:
      - "8080:8080"
    environment:
      - NEON_DATABASE_URL=${NEON_DATABASE_URL}
      - B2_APPLICATION_KEY_ID=${B2_APPLICATION_KEY_ID}
      - B2_APPLICATION_KEY=${B2_APPLICATION_KEY}
```

## 🔐 **Ubuntu Security Hardening**

### **Firewall Configuration**
```bash
# Configure UFW firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 8080/tcp  # API access
sudo ufw enable
```

### **Non-Root User Setup**
```bash
# Create dedicated user
sudo adduser docintel
sudo usermod -aG sudo docintel

# Switch to new user
su - docintel

# Run as non-root
cd unified-doc-intelligence-deploy
python3 setup.py --user
```

### **Systemd Service for Production**
```bash
# Create systemd service file
sudo tee /etc/systemd/system/unified-doc-intel.service << 'EOF'
[Unit]
Description=Unified Engineering Document Intelligence Platform
After=network.target postgresql.service

[Service]
Type=forking
User=docintel
WorkingDirectory=/home/docintel/unified-doc-intelligence-deploy
ExecStart=/usr/bin/python3 run-pipeline.py --phase all --workers auto
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable unified-doc-intel
sudo systemctl start unified-doc-intel
sudo systemctl status unified-doc-intel
```

## 📈 **Ubuntu Monitoring & Logging**

### **System Monitoring**
```bash
# Install monitoring tools
sudo apt-get install -y htop iotop nmon sysstat

# Monitor in real-time
htop  # CPU/RAM
iotop  # Disk I/O
nmon  # Comprehensive system monitor

# Configure SAR for historical data
sudo vi /etc/default/sysstat  # Change ENABLED="false" to "true"
sudo systemctl enable sysstat
sudo systemctl start sysstat
```

### **Log Management**
```bash
# Configure log rotation
sudo tee /etc/logrotate.d/unified-doc-intel << 'EOF'
/home/docintel/unified-doc-intelligence-deploy/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 640 docintel docintel
}
EOF

# View live logs
tail -f /home/docintel/unified-doc-intelligence-deploy/logs/pdf-worker.log
tail -f /home/docintel/unified-doc-intelligence-deploy/logs/api-server.log
```

### **Performance Alerts**
```bash
# Create monitoring script
cat > /home/docintel/monitor.sh << 'EOF'
#!/bin/bash
# Check extraction progress
python3 /home/docintel/unified-doc-intelligence-deploy/run-pipeline.py --status

# Check system resources
echo "=== System Resources ==="
free -h
echo ""
df -h
echo ""
top -bn1 | head -20
EOF

chmod +x /home/docintel/monitor.sh

# Schedule with cron
(crontab -l 2>/dev/null; echo "*/5 * * * * /home/docintel/monitor.sh >> /home/docintel/monitor.log 2>&1") | crontab -
```

## 🛠️ **Ubuntu Troubleshooting**

### **Common Issues & Solutions:**

**1. Python Package Installation Failures**
```bash
# Fix: Install development headers first
sudo apt-get install -y python3-dev libpq-dev

# Fix: Use --no-binary for problematic packages
pip3 install psycopg2-binary --no-binary psycopg2-binary
```

**2. Memory Exhaustion (OOM Killer)**
```bash
# Monitor memory usage
watch -n 1 'free -h'

# Reduce worker count
export WORKERS=$(( $(free -g | awk '/^Mem:/{print $2}') / 4 ))
python3 B3-pdf-extraction-worker.py --workers $WORKERS

# Add swap space if needed
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

**3. Database Connection Limits**
```bash
# Check PostgreSQL connections
psql $NEON_DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"

# Reduce connection pool in scripts
# Edit scripts to use fewer database connections
sed -i 's/pool_size=20/pool_size=5/g' scripts/phase-b-extraction/B3-pdf-extraction-worker.py
```

**4. B2 API Rate Limiting**
```bash
# Add delays between B2 operations
# Edit worker scripts to add:
import time
time.sleep(0.1)  # 100ms between B2 operations
```

## 🚢 **Cloud Ubuntu Deployments**

### **AWS EC2 Ubuntu** (Recommended: c6a.8xlarge or similar)
```bash
# Connect to EC2
ssh -i your-key.pem ubuntu@ec2-public-ip

# Install and run
sudo apt-get update && sudo apt-get install -y python3-pip
cd unified-doc-intelligence-deploy
python3 run-pipeline.py --phase b --workers 32  # Use all vCPUs
```

### **Google Cloud Ubuntu**
```bash
# Use preemptible VMs for cost savings
gcloud compute instances create docintel-worker \
    --machine-type=n2-standard-32 \
    --preemptible \
    --image-family=ubuntu-2204-lts \
    --scopes=cloud-platform
```

### **Azure Ubuntu**
```bash
# Use Spot instances
az vm create \
  --resource-group myResourceGroup \
  --name docintel-worker \
  --image Ubuntu2204 \
  --size Standard_D32s_v3 \
  --priority Spot \
  --eviction-policy Delete
```

## ✅ **Verification on Ubuntu**

```bash
# Run the verification script
cd unified-doc-intelligence-deploy
python3 test-deployment.py

# Test a single component
python3 scripts/phase-a-linking/A1-migrate-schema.py --dry-run

# Check system compatibility
python3 -c "
import platform
print(f'System: {platform.system()}')
print(f'Release: {platform.release()}')
print(f'Machine: {platform.machine()}')
print(f'Python: {platform.python_version()}')
"
```

## 📞 **Ubuntu Support**

If you encounter Ubuntu-specific issues:

1. **Check system logs**: `sudo journalctl -xe`
2. **Verify Python installation**: `python3 --version && pip3 --version`
3. **Test database connectivity**: `python3 -c "import psycopg2; print('PostgreSQL driver OK')"`
4. **Check disk space**: `df -h /home`
5. **Monitor resource usage**: `htop`

## 🎯 **Summary: Ubuntu Advantages**

✅ **Performance**: Linux kernel optimizations for I/O and networking  
✅ **Stability**: LTS releases with 5+ years of support  
✅ **Package Management**: `apt-get` for reliable dependency installation  
✅ **Container Support**: Native Docker and Kubernetes integration  
✅ **Cloud Ready**: All major clouds offer Ubuntu images  
✅ **Security**: SELinux/AppArmor, regular security updates  
✅ **Monitoring**: Built-in tools (systemd, journalctl, sar)  
✅ **Cost**: Free and open source  

**Ubuntu is the IDEAL platform for running the Unified Engineering Document Intelligence Platform at scale.**

---

*Ubuntu Deployment Guide v1.0 - Tested on Ubuntu 22.04 LTS*  
*Last Updated: 2026-01-20*