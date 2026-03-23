# AWS Infrastructure Sizing Recommendations

## Non-Functional and Volumetric Requirements Summary

| Requirement | Target |
|---|---|
| Web Application Latency | ≤ 20 ms (end-to-end response time) |
| Daily Batch Job | 10,000 records/day |
| Monthly Batch Job | ~50,000–100,000 records (estimated 5–10x daily) |
| Quarterly Batch Job | ~150,000–300,000 records (estimated 15–30x daily) |
| Annual Batch Job | ~500,000–1,000,000 records (estimated 50–100x daily) |

> Volume multipliers for monthly/quarterly/annual are estimates. Adjust based on actual business data.

---

## 1. Web Application Tier (≤ 20 ms Latency Target)

### 1.1 CloudFront (CDN)

| Parameter | Recommendation |
|---|---|
| Distribution | Standard distribution with edge caching |
| Cache Policy | Optimized for dynamic + static content |
| Origin Shield | Enabled (reduces origin load, improves cache hit ratio) |
| Price Class | PriceClass_100 or PriceClass_200 depending on user geography |
| TTL | Static assets: 86400s, Dynamic: 0s with cache headers |

Rationale: CloudFront edge locations serve cached content in single-digit ms. This offloads static content delivery and keeps the 20 ms budget available for dynamic requests.

Source: [AWS Web Hosting Best Practices – Content Delivery](https://docs.aws.amazon.com/whitepapers/latest/web-application-hosting-best-practices/key-components-of-an-aws-web-hosting-architecture.html)

### 1.2 Application Load Balancer (ALB)

| Parameter | Recommendation |
|---|---|
| Type | Application Load Balancer (Layer 7) |
| Idle Timeout | 30 seconds |
| Cross-Zone Load Balancing | Enabled |
| Health Check Interval | 10 seconds |
| Deregistration Delay | 30 seconds (reduced from default 300s for faster failover) |
| Ingress Controller | AWS Load Balancer Controller (manages ALB via Kubernetes Ingress/Service) |

Rationale: ALB adds ~1–2 ms latency. Use the AWS Load Balancer Controller add-on to manage ALB lifecycle from Kubernetes manifests.

### 1.3 Amazon EKS Cluster – Control Plane & Data Plane

| Parameter | Recommendation |
|---|---|
| Orchestrator | Amazon EKS (Managed Kubernetes) |
| Kubernetes Version | Latest stable (1.29+) |
| Control Plane | EKS Managed (AWS manages API server, etcd, scheduler) |
| Control Plane Cost | $0.10/hr ($73/month) |
| Node Autoscaler | Karpenter (preferred) or Cluster Autoscaler |
| EKS Add-ons | VPC CNI, CoreDNS, kube-proxy, AWS Load Balancer Controller, Metrics Server |
| Cluster Count | 1 cluster, separate namespaces per workload (web, batch) |

Source: [EKS Scalability Best Practices](https://docs.aws.amazon.com/eks/latest/best-practices/scalability.html)
Source: [EKS Cluster Autoscaling Best Practices](https://docs.aws.amazon.com/eks/latest/best-practices/cluster-autoscaling.html)

### 1.4 EKS Managed Node Groups – Worker Nodes

| Parameter | Web Tier Node Group | Batch Tier Node Group |
|---|---|---|
| Instance Family | c6i (Compute Optimized) | m6i (General Purpose) |
| Instance Size | c6i.xlarge (4 vCPU, 8 GiB) | m6i.2xlarge (8 vCPU, 32 GiB) |
| Min Nodes | 2 | 0 (scale to zero between jobs) |
| Max Nodes | 4 | 4 |
| Desired Nodes | 2 | 0 |
| Capacity Type | On-Demand | Spot (with On-Demand fallback) |
| AMI Type | Amazon Linux 2023 (AL2023) |  Amazon Linux 2023 (AL2023) |
| Disk Size | 50 GiB gp3 | 50 GiB gp3 |
| Placement | Spread across 2+ AZs | Spread across 2+ AZs |
| Max Pods per Node | 29 (c6i.xlarge VPC CNI default) | 29 (m6i.2xlarge VPC CNI default) |


Why c6i.xlarge for web nodes (not c6i.large):
- Each c6i.large (2 vCPU) can only run ~1 web pod (1 vCPU request) + system pods, leaving no headroom
- c6i.xlarge (4 vCPU) fits 2–3 web pods per node, improving bin-packing efficiency and reducing node count
- VPC CNI limits max pods per ENI; larger instances support more pods

Why m6i.2xlarge for batch nodes:
- Batch pods need 2–4 vCPU and 4–8 GB memory; m6i.2xlarge (8 vCPU, 32 GiB) fits 2–4 batch pods per node
- General Purpose (M-family) provides balanced CPU + memory for ETL/data processing

Source: [EKS Managed Node Groups](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html)
Source: [Karpenter Best Practices](https://docs.aws.amazon.com/eks/latest/best-practices/karpenter.html)

### 1.5 Web Application Pods – Resource Requests & Limits

#### Assumptions for Pod Capacity Planning

| Parameter | Value | Rationale |
|---|---|---|
| Peak requests/sec (RPS) | ~115 RPS | ~10M requests/month ÷ 30 days ÷ 24 hrs ÷ 3600s ≈ 3.8 avg; peak = ~30x avg |
| Target latency (p99) | ≤ 15 ms at pod | Leaves 5 ms for CloudFront + ALB + network |
| Avg processing time/request | ~8 ms | Application logic + cache/DB call |
| Concurrent requests per pod | ~50 | Typical thread/connection pool for a web app container |
| Throughput per pod | ~125 RPS | At 8 ms/req with 50 concurrent threads: 1000ms/8ms × 50 ÷ 10 (overhead) ≈ 125 |
| Target CPU utilization | 50% | Headroom for latency-sensitive workloads |
| Effective throughput per pod | ~62 RPS | 125 × 50% utilization cap |

#### Pod Count Calculation (Web Tier)

| Scenario | Peak RPS | Pods Needed | Formula |
|---|---|---|---|
| Normal traffic | ~40 RPS | 2 | ceil(40 / 62) = 1, min 2 for HA |
| Peak traffic (3x) | ~115 RPS | 2 | ceil(115 / 62) = 2 |
| Spike traffic (5x) | ~190 RPS | 4 | ceil(190 / 62) = 4 |
| Burst traffic (10x) | ~380 RPS | 7 | ceil(380 / 62) = 7 |

#### Kubernetes Deployment – Web Application Pod Spec

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: web
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    spec:
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
      containers:
        - name: web-app
          resources:
            requests:
              cpu: "500m"        # 0.5 vCPU
              memory: "512Mi"
            limits:
              cpu: "1000m"       # 1 vCPU
              memory: "1536Mi"
          ports:
            - containerPort: 8080
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 15
            periodSeconds: 20
        - name: fluentbit-sidecar
          resources:
            requests:
              cpu: "50m"
              memory: "64Mi"
            limits:
              cpu: "100m"
              memory: "128Mi"
```

Why 500m request / 1000m limit per pod:
- Request of 500m (0.5 vCPU) guarantees scheduling; limit of 1000m (1 vCPU) allows bursting under load
- This lets Kubernetes scheduler fit 2–3 web pods per c6i.xlarge node (4 vCPU total, minus ~1 vCPU for system pods)
- Memory request 512Mi / limit 1536Mi accommodates JVM (Spring Boot) or Node.js apps with headroom
- Smaller requests (250m) risk CPU starvation under load, pushing latency above 20 ms

Source: [EKS Horizontal Pod Autoscaler](https://docs.aws.amazon.com/eks/latest/userguide/horizontal-pod-autoscaler.html)
Source: [EKS Workload Scaling](https://docs.aws.amazon.com/prescriptive-guidance/latest/scaling-amazon-eks-infrastructure/workload-scaling.html)

### 1.6 Horizontal Pod Autoscaler (HPA) – Web Tier

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-app-hpa
  namespace: web
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
  minReplicas: 2
  maxReplicas: 8
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 50
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
        - type: Pods
          value: 2
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Pods
          value: 1
          periodSeconds: 120
```

| HPA Parameter | Value | Rationale |
|---|---|---|
| Min Replicas | 2 | Multi-AZ HA (1 pod per AZ minimum) |
| Max Replicas | 8 | Handles 10x burst traffic (~380 RPS) |
| CPU Target | 50% | Aggressive to preserve latency headroom |
| Scale-Up Window | 60 seconds | Fast response to traffic spikes |
| Scale-Down Window | 300 seconds | Conservative to avoid flapping |
| Scale-Up Rate | 2 pods per 60s | Rapid scale-out for latency protection |
| Scale-Down Rate | 1 pod per 120s | Gradual scale-in |

Rationale: HPA at 50% CPU target ensures pods never saturate, keeping per-request latency within the 15 ms pod-level budget. The stabilization windows prevent oscillation.

Source: [EKS Horizontal Pod Autoscaler](https://docs.aws.amazon.com/eks/latest/userguide/horizontal-pod-autoscaler.html)
Source: [EKS Workload Scaling – HPA](https://docs.aws.amazon.com/prescriptive-guidance/latest/scaling-amazon-eks-infrastructure/workload-scaling.html)

### 1.7 ElastiCache (Redis)

| Parameter | Recommendation |
|---|---|
| Engine | Redis (cluster mode disabled for simplicity) |
| Node Type | cache.r6g.large (13.07 GiB, Graviton2) |
| Replicas | 1 read replica (Multi-AZ) |
| Eviction Policy | allkeys-lru |
| Max Memory | 75% of node memory |

Rationale: Caching frequently accessed data in Redis reduces DB round-trips. Redis delivers sub-millisecond response times, which is critical for staying within the 20 ms budget.

Source: [ElastiCache Best Practices](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/WorkingWithRedis.html)

### 1.8 RDS Database

| Parameter | Recommendation |
|---|---|
| Engine | PostgreSQL or MySQL (based on your app) |
| Instance Class | db.r6g.large (2 vCPU, 16 GiB RAM) – Memory Optimized |
| Storage Type | gp3 (3,000 baseline IOPS, 125 MiB/s throughput) |
| Storage Size | 100 GiB (start, auto-scaling enabled) |
| Multi-AZ | Yes (standby replica for HA) |
| Read Replicas | 1 (for read-heavy web workloads) |
| Backup Retention | 7 days |
| Performance Insights | Enabled |

Source: [RDS Best Practices – DB Instance RAM](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_BestPractices.html)

---

## 2. Batch Processing Tier (Kubernetes Jobs on EKS)

### 2.1 Batch Job Volume Estimates

| Job Frequency | Record Volume | Processing Window | Throughput Required |
|---|---|---|---|
| Daily | 10,000 | 1–2 hours | ~2–3 records/sec |
| Monthly | 50,000–100,000 | 4–6 hours | ~3–7 records/sec |
| Quarterly | 150,000–300,000 | 6–8 hours | ~5–10 records/sec |
| Annual | 500,000–1,000,000 | 8–12 hours | ~12–35 records/sec |

### 2.2 Batch Pod Sizing (Kubernetes Jobs)

Batch workloads run as Kubernetes Jobs on EKS. Each job spawns one or more pods with defined resource requests/limits.

#### Processing Capacity per Record (Estimated)

| Processing Step | Time per Record | CPU Intensity | Memory per Record |
|---|---|---|---|
| Read/Parse input | ~2 ms | Low | ~1 KB |
| Business logic/transform | ~10 ms | Medium | ~5 KB |
| Validation/enrichment | ~5 ms | Medium | ~2 KB |
| Write output (DB/S3) | ~8 ms | Low (I/O wait) | ~1 KB |
| **Total per record** | **~25 ms** | | **~9 KB** |

#### Pod Count Calculation (Batch Tier)

| Job Type | Records | Processing Window | Required Throughput | Pod Size (req/limit) | Pods Needed |
|---|---|---|---|---|---|
| Daily | 10,000 | 2 hours | ~1.4 records/sec | 500m/1000m CPU, 1Gi/2Gi mem | 1 |
| Monthly | 100,000 | 5 hours | ~5.6 records/sec | 1000m/2000m CPU, 2Gi/4Gi mem | 2 |
| Quarterly | 300,000 | 7 hours | ~11.9 records/sec | 1000m/2000m CPU, 2Gi/4Gi mem | 4 |
| Annual | 1,000,000 | 10 hours | ~27.8 records/sec | 2000m/4000m CPU, 4Gi/8Gi mem | 8 |


#### Kubernetes Job Spec – Batch Pods

```yaml
# Daily batch job (10K records, 1 pod)
apiVersion: batch/v1
kind: Job
metadata:
  name: daily-batch
  namespace: batch
spec:
  parallelism: 1
  completions: 1
  backoffLimit: 3
  activeDeadlineSeconds: 7200   # 2 hour timeout
  template:
    spec:
      restartPolicy: OnFailure
      nodeSelector:
        workload-type: batch
      tolerations:
        - key: "batch"
          operator: "Equal"
          value: "true"
          effect: "NoSchedule"
      containers:
        - name: batch-processor
          resources:
            requests:
              cpu: "500m"
              memory: "1Gi"
            limits:
              cpu: "1000m"
              memory: "2Gi"
---
# Annual batch job (1M records, 8 parallel pods)
apiVersion: batch/v1
kind: Job
metadata:
  name: annual-batch
  namespace: batch
spec:
  parallelism: 8
  completions: 8
  backoffLimit: 3
  activeDeadlineSeconds: 43200  # 12 hour timeout
  template:
    spec:
      restartPolicy: OnFailure
      nodeSelector:
        workload-type: batch
      tolerations:
        - key: "batch"
          operator: "Equal"
          value: "true"
          effect: "NoSchedule"
      containers:
        - name: batch-processor
          resources:
            requests:
              cpu: "2000m"
              memory: "4Gi"
            limits:
              cpu: "4000m"
              memory: "8Gi"
```

| Job Parameter | Daily | Monthly | Quarterly | Annual |
|---|---|---|---|---|
| parallelism | 1 | 2 | 4 | 8 |
| completions | 1 | 2 | 4 | 8 |
| backoffLimit | 3 | 3 | 3 | 3 |
| activeDeadlineSeconds | 7200 | 21600 | 28800 | 43200 |
| Records per Pod | 10,000 | 50,000 | 75,000 | 125,000 |
| Pod CPU request/limit | 500m/1000m | 1000m/2000m | 1000m/2000m | 2000m/4000m |
| Pod Memory request/limit | 1Gi/2Gi | 2Gi/4Gi | 2Gi/4Gi | 4Gi/8Gi |

Why scale pod size AND count for larger jobs:
- Daily (10K): single small pod is sufficient, simple and cost-effective
- Monthly (100K): 2 pods with 1 vCPU each provides parallel processing
- Quarterly (300K): 4 pods split the workload, each handling 75K records
- Annual (1M): 8 pods with 2 vCPU request each for maximum parallelism; larger memory (8 GB limit) accommodates in-memory buffering for bulk DB writes

### 2.3 Karpenter NodePool for Batch (Scale-to-Zero)

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: batch
spec:
  template:
    spec:
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["m6i.xlarge", "m6i.2xlarge", "m6i.4xlarge"]
      taints:
        - key: batch
          value: "true"
          effect: NoSchedule
  limits:
    cpu: "32"
    memory: "128Gi"
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 60s
```

Karpenter provisions batch nodes only when batch Jobs are submitted and removes them when jobs complete (scale-to-zero). Spot instances are preferred for cost savings (60–70% cheaper), with on-demand fallback for reliability.

Source: [Karpenter Best Practices](https://docs.aws.amazon.com/eks/latest/best-practices/karpenter.html)

### 2.4 Batch Job Scheduling

| Scheduler | Recommendation |
|---|---|
| Daily Jobs | Kubernetes CronJob (schedule: "0 2 * * *") |
| Monthly Jobs | Kubernetes CronJob (schedule: "0 1 1 * *") |
| Quarterly Jobs | External trigger (AWS EventBridge → Lambda → kubectl) |
| Annual Jobs | External trigger (AWS EventBridge → Lambda → kubectl) |

---

## 3. Latency Budget Breakdown (20 ms Target)

| Component | Expected Latency | Notes |
|---|---|---|
| CloudFront Edge | 1–5 ms | For cached content, near-zero |
| ALB (via AWS LB Controller) | 1–2 ms | Layer 7 routing to EKS pod |
| Pod Startup (warm) | 0 ms | Pods are pre-running, no cold start |
| Pod App Processing | 5–8 ms | Application logic within container |
| ElastiCache (cache hit) | < 1 ms | Sub-millisecond Redis |
| RDS (cache miss) | 3–5 ms | Within same AZ |
| Pod-to-service network | < 1 ms | VPC CNI (pod gets VPC IP directly) |
| **Total (cache hit)** | **~8–12 ms** | **Within budget** |
| **Total (cache miss)** | **~14–20 ms** | **At budget limit** |

EKS-specific latency considerations:
- VPC CNI plugin assigns each pod a real VPC IP address — no overlay network overhead, near-native networking performance
- Keep HPA minReplicas = 2 to avoid cold-start delays (new node provisioning via Karpenter takes 60–90s)
- Use topology spread constraints to distribute pods across AZs for both HA and latency consistency
- Connection pooling within pods is critical — pre-warm DB and Redis connections on startup
- Consider Kubernetes Service with `externalTrafficPolicy: Local` to avoid extra hop

---

## 4. Container Image & Deployment Best Practices

| Practice | Recommendation |
|---|---|
| Base Image | Use minimal images (Alpine, distroless) to reduce attack surface and pull time |
| Image Size | Target < 200 MB for fast pod launches |
| Image Caching | Use Karpenter's AMI with pre-pulled images or Bottlerocket OS |
| Health Checks | readinessProbe + livenessProbe on /health; period 10s, failure threshold 3 |
| Graceful Shutdown | Handle SIGTERM; set terminationGracePeriodSeconds: 30 |
| Logging | Write to stdout/stderr; use Fluent Bit DaemonSet to CloudWatch |
| Secrets | Use AWS Secrets Manager with CSI Secret Store driver (never bake into image) |
| Connection Pooling | Pre-warm DB (5–10 connections) and Redis (3–5 connections) pools on startup |
| Single Process | Run one application process per container for clean scaling |
| Pod Disruption Budget | Set PDB minAvailable: 1 for web tier to protect during node drains |

---

## 5. Network & VPC Configuration

| Parameter | Recommendation |
|---|---|
| VPC | Single VPC, multi-AZ (2 AZs minimum) |
| Public Subnets | ALB, NAT Gateway |
| Private Subnets | EKS worker nodes, RDS, ElastiCache |
| NAT Gateway | 1 per AZ for HA |
| VPC Endpoints | S3 Gateway, ECR (dkr + api), STS, CloudWatch Logs |
| EKS CNI Plugin | Amazon VPC CNI (pod-level VPC networking) |
| Pod Networking | Each pod gets a VPC IP (no overlay) |
| Security Groups | Security Groups for Pods (SGP) for fine-grained pod-level network policies |

---

## 6. Monitoring & Sizing Validation

After deployment, validate sizing using these metrics:

| Metric | Target | Action if Exceeded |
|---|---|---|
| Pod CPU Utilization | < 50% avg | Reduce HPA maxReplicas or lower CPU request |
| Pod CPU Utilization | > 70% avg | HPA scales out; if at maxReplicas, increase max or upsize CPU |
| Pod Memory Utilization | < 40% avg | Lower memory request to improve bin-packing |
| Pod Memory Utilization | > 80% avg | Increase memory limit (risk of OOMKill) |
| HPA Current Replicas | Stable at desired | Auto scaling is balanced |
| Node CPU Utilization | < 60% avg | Karpenter consolidates; consider smaller instance type |
| Node CPU Utilization | > 80% avg | Karpenter provisions more nodes |
| ALB Target Response Time | < 15 ms (p99) | Leaves 5 ms buffer for network |
| ALB Healthy Targets | ≥ HPA minReplicas | All pods are healthy |
| RDS ReadIOPS | Low and stable | Working set fits in memory – sizing is correct |
| RDS ReadIOPS | High/volatile | Scale up to next R-family size |
| ElastiCache Hit Rate | > 80% | Caching strategy is effective |
| Batch Job Duration | Within processing window | Pod count is correct |
| Batch Pod CPU | < 80% during job | Pod size is adequate |

Recommended tools: CloudWatch Container Insights, Kubernetes Metrics Server, Prometheus + Grafana (optional)

Source: [Tips for Right Sizing Your Workloads](https://docs.aws.amazon.com/whitepapers/latest/cost-optimization-right-sizing/tips-for-right-sizing-your-workloads.html)
Source: [EKS Scalability Best Practices](https://docs.aws.amazon.com/eks/latest/best-practices/scalability.html)

---

## 7. Pod & Node Summary – All Workloads

### Pod Summary

| Workload | CPU Request | CPU Limit | Mem Request | Mem Limit | Min Pods | Max Pods | Scaling |
|---|---|---|---|---|---|---|---|
| Web App | 500m | 1000m | 512Mi | 1536Mi | 2 | 8 | HPA (CPU 50%) |
| Batch – Daily (10K) | 500m | 1000m | 1Gi | 2Gi | 0 | 1 | Kubernetes Job |
| Batch – Monthly (100K) | 1000m | 2000m | 2Gi | 4Gi | 0 | 2 | Kubernetes Job |
| Batch – Quarterly (300K) | 1000m | 2000m | 2Gi | 4Gi | 0 | 4 | Kubernetes Job |
| Batch – Annual (1M) | 2000m | 4000m | 4Gi | 8Gi | 0 | 8 | Kubernetes Job |

### Node Summary

| Node Group | Instance Type | Min Nodes | Max Nodes | Capacity Type | Purpose |
|---|---|---|---|---|---|
| Web | c6i.xlarge (4 vCPU, 8 GiB) | 2 | 4 | On-Demand | Web app pods |
| Batch (Karpenter) | m6i.xlarge–m6i.4xlarge | 0 | 4 | Spot (preferred) | Batch job pods |
| System | t3.medium (2 vCPU, 4 GiB) | 2 | 2 | On-Demand | CoreDNS, Karpenter, monitoring |

Total capacity at peak:
- Web tier: 8 pods × 500m request = 4 vCPU requested (8 vCPU burst limit), across 2–4 c6i.xlarge nodes
- Batch tier (annual peak): 8 pods × 2000m request = 16 vCPU requested (32 vCPU burst limit), across 2–4 m6i nodes
- Batch nodes scale to zero between job runs via Karpenter consolidation

---

## 8. Cost Optimization Recommendations

| Strategy | Savings Potential | Applicable To |
|---|---|---|
| EKS Compute Savings Plans (1-yr) | ~30% | EC2 node groups (web tier) |
| Reserved Instances (1-yr) | ~30–40% | RDS, ElastiCache (steady state) |
| Spot Instances via Karpenter | ~60–70% | Batch node group |
| Graviton (ARM) instances | ~20–25% | c7g nodes (web), r7g (RDS/ElastiCache) |
| Karpenter consolidation | ~15–20% | Right-sizes nodes automatically, removes underutilized nodes |
| Scale-to-zero batch nodes | ~100% off-hours | Batch nodes only exist during job execution |
| VPC Endpoints for ECR/S3 | Reduces NAT costs | Avoids NAT Gateway data processing charges for image pulls |

Source: [Right Sizing Whitepaper](https://docs.aws.amazon.com/whitepapers/latest/cost-optimization-right-sizing/cost-optimization-right-sizing.html)
Source: [EKS Cost Optimization Best Practices](https://docs.aws.amazon.com/eks/latest/best-practices/cost-opt.html)
