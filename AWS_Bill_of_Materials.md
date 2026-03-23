# AWS Infrastructure – Bill of Materials (BOM)

Region: us-east-1 (N. Virginia) | Pricing: On-Demand (USD) | Date: March 2026

> Prices are approximate on-demand rates. Actual costs vary by region, commitment type (Reserved/Savings Plans), and usage patterns. Use the [AWS Pricing Calculator](https://calculator.aws/) for precise estimates.

---

## 1. Web Application Tier

### 1.1 Amazon CloudFront (CDN)

| Line Item | Specification | Qty | Unit Price | Monthly Est. |
|---|---|---|---|---|
| Data Transfer Out (first 10 TB) | Standard distribution | 500 GB/mo (est.) | $0.085/GB | $42.50 |
| HTTPS Requests | 10M requests/mo (est.) | 10M | $0.01/10K req | $10.00 |
| Origin Shield Requests | Enabled | 5M | $0.0075/10K req | $3.75 |
| **CloudFront Subtotal** | | | | **$56.25** |

### 1.2 Amazon Route 53

| Line Item | Specification | Qty | Unit Price | Monthly Est. |
|---|---|---|---|---|
| Hosted Zone | 1 public hosted zone | 1 | $0.50/zone | $0.50 |
| Standard DNS Queries | ~10M queries/mo | 10M | $0.40/1M queries | $4.00 |
| Health Checks | 2 endpoints | 2 | $0.50/check | $1.00 |
| **Route 53 Subtotal** | | | | **$5.50** |

### 1.3 Application Load Balancer (ALB)

| Line Item | Specification | Qty | Unit Price | Monthly Est. |
|---|---|---|---|---|
| ALB Hours | 1 ALB (managed via AWS LB Controller) | 730 hrs | $0.0225/hr | $16.43 |
| LCU Hours | ~2 LCU avg (est.) | 1,460 LCU-hrs | $0.008/LCU-hr | $11.68 |
| **ALB Subtotal** | | | | **$28.11** |

### 1.4 Amazon EKS Control Plane

| Line Item | Specification | Qty | Unit Price | Monthly Est. |
|---|---|---|---|---|
| EKS Cluster (Standard Support) | 1 cluster, 24x7 | 730 hrs | $0.10/hr | $73.00 |
| **EKS Control Plane Subtotal** | | | | **$73.00** |

### 1.5 EKS Worker Nodes – Web Tier (Managed Node Group)

| Line Item | Specification | Qty | Unit Price | Monthly Est. |
|---|---|---|---|---|
| c6i.xlarge (On-Demand) | 4 vCPU, 8 GiB RAM | 2 nodes (steady) | $0.170/hr | $248.20 |
| EBS gp3 (root volume) | 50 GiB per node | 2 × 50 GiB | $0.08/GiB/mo | $8.00 |
| Auto Scaling headroom | Avg ~2.5 nodes (peak) | +0.5 node (avg) | $0.170/hr × 50% time | $31.03 |
| **Web Node Group Subtotal** | | | | **$287.23** |

> Managed Node Group: min=2, max=4, desired=2. Cost assumes avg ~2.5 nodes over the month.

### 1.6 EKS Worker Nodes – System Node Group

| Line Item | Specification | Qty | Unit Price | Monthly Est. |
|---|---|---|---|---|
| t3.medium (On-Demand) | 2 vCPU, 4 GiB RAM | 2 nodes | $0.0416/hr | $60.74 |
| EBS gp3 (root volume) | 30 GiB per node | 2 × 30 GiB | $0.08/GiB/mo | $4.80 |
| **System Node Group Subtotal** | | | | **$65.54** |

> Runs CoreDNS, Karpenter controller, Fluent Bit DaemonSet, Metrics Server.


### 1.7 Amazon ElastiCache (Redis)

| Line Item | Specification | Qty | Unit Price | Monthly Est. |
|---|---|---|---|---|
| cache.r6g.large (Primary) | 2 vCPU, 13.07 GiB | 1 node | $0.206/hr | $150.38 |
| cache.r6g.large (Replica) | Multi-AZ read replica | 1 node | $0.206/hr | $150.38 |
| **ElastiCache Subtotal** | | | | **$300.76** |

### 1.8 Amazon RDS (PostgreSQL)

| Line Item | Specification | Qty | Unit Price | Monthly Est. |
|---|---|---|---|---|
| db.r6g.large (Primary) | 2 vCPU, 16 GiB RAM | 1 instance | $0.260/hr | $189.80 |
| db.r6g.large (Multi-AZ Standby) | HA standby replica | 1 instance | $0.260/hr | $189.80 |
| db.r6g.large (Read Replica) | Read scaling | 1 instance | $0.260/hr | $189.80 |
| gp3 Storage | 100 GiB, 3000 IOPS, 125 MiB/s | 3 × 100 GiB | $0.08/GiB/mo | $24.00 |
| Automated Backups | 7-day retention, 100 GiB | 100 GiB | $0.095/GiB/mo | $9.50 |
| Performance Insights | Retention: 7 days (free) | 1 | Free | $0.00 |
| **RDS Subtotal** | | | | **$602.90** |

---

## 2. Batch Processing Tier (Kubernetes Jobs on EKS)

### 2.1 EKS Worker Nodes – Batch Tier (Karpenter, Scale-to-Zero)

Batch nodes are provisioned by Karpenter only when Kubernetes Jobs are submitted, and terminated when jobs complete.

| Job Type | Instance | Nodes | Run Hours/Mo | Unit Price (Spot ~35% of OD) | Monthly Est. |
|---|---|---|---|---|---|
| Daily (10K records, 1 pod) | m6i.xlarge | 1 | ~60 hrs (2 hrs × 30 days) | $0.067/hr (Spot) | $4.03 |
| Monthly (100K records, 2 pods) | m6i.xlarge | 1 | ~5 hrs (1 run) | $0.067/hr (Spot) | $0.34 |
| Quarterly (300K records, 4 pods) | m6i.2xlarge | 1 | ~7 hrs (1 run/3 mo, amortized) | $0.134/hr (Spot) | $0.31 |
| Annual (1M records, 8 pods) | m6i.2xlarge | 2 | ~10 hrs (1 run/12 mo, amortized) | $0.134/hr (Spot) | $0.22 |
| EBS gp3 (batch nodes) | 50 GiB per node (ephemeral) | varies | — | $0.08/GiB/mo (prorated) | $1.00 |
| **Batch Compute Subtotal** | | | | | **$5.90** |

> Spot pricing estimated at ~35% of on-demand for m6i family. Actual Spot prices fluctuate. Karpenter handles Spot interruptions with graceful node drain.

### 2.2 Batch Supporting Services

| Line Item | Specification | Qty | Unit Price | Monthly Est. |
|---|---|---|---|---|
| S3 (batch data staging) | Standard storage | 50 GiB | $0.023/GiB/mo | $1.15 |
| S3 PUT/GET Requests | Batch I/O | ~100K requests | $0.005/1K PUT, $0.0004/1K GET | $0.54 |
| CloudWatch Logs | Batch job logs | 5 GiB | $0.50/GiB ingested | $2.50 |
| **Batch Support Subtotal** | | | | **$4.19** |

---

## 3. Networking & Security

| Line Item | Specification | Qty | Unit Price | Monthly Est. |
|---|---|---|---|---|
| VPC | 1 VPC, 2 AZs | 1 | Free | $0.00 |
| NAT Gateway (AZ-1) | 24x7 | 730 hrs | $0.045/hr | $32.85 |
| NAT Gateway (AZ-2) | 24x7 (HA) | 730 hrs | $0.045/hr | $32.85 |
| NAT Gateway Data Processing | Outbound traffic | 100 GiB/mo (est.) | $0.045/GiB | $4.50 |
| S3 Gateway VPC Endpoint | Private S3 access | 1 | Free | $0.00 |
| ECR VPC Endpoints (dkr + api) | Private image pulls | 2 endpoints | $0.01/hr × 730 | $14.60 |
| STS VPC Endpoint | IAM auth for pods | 1 endpoint | $0.01/hr × 730 | $7.30 |
| AWS Certificate Manager | SSL/TLS for ALB + CloudFront | 2 certs | Free (public) | $0.00 |
| **Networking Subtotal** | | | | **$92.10** |

---

## 4. Monitoring & Operations

| Line Item | Specification | Qty | Unit Price | Monthly Est. |
|---|---|---|---|---|
| CloudWatch Container Insights | EKS cluster monitoring | 1 cluster | ~$0.01/metric/mo | $5.00 |
| CloudWatch Custom Metrics | App-level metrics | 10 metrics | $0.30/metric | $3.00 |
| CloudWatch Alarms | Latency, CPU, HPA alerts | 10 alarms | $0.10/alarm | $1.00 |
| CloudWatch Logs | Application + system logs | 15 GiB/mo | $0.50/GiB ingested | $7.50 |
| CloudWatch Logs Storage | Retention: 30 days | 15 GiB | $0.03/GiB stored | $0.45 |
| Amazon ECR | Container image registry | 5 GiB images | $0.10/GiB/mo | $0.50 |
| AWS CloudTrail | Management events | 1 trail | Free (1 trail) | $0.00 |
| **Monitoring Subtotal** | | | | **$17.45** |

---

## 5. Monthly Cost Summary

| Category | Monthly Estimate (USD) |
|---|---|
| CloudFront (CDN) | $56.25 |
| Route 53 (DNS) | $5.50 |
| Application Load Balancer | $28.11 |
| EKS Control Plane | $73.00 |
| EKS Web Node Group (c6i.xlarge × 2–4) | $287.23 |
| EKS System Node Group (t3.medium × 2) | $65.54 |
| ElastiCache Redis (Primary + Replica) | $300.76 |
| RDS PostgreSQL (Primary + Standby + Read Replica) | $602.90 |
| EKS Batch Nodes (Karpenter, Spot) | $5.90 |
| Batch Supporting Services (S3, Logs) | $4.19 |
| Networking (NAT Gateways, VPC Endpoints) | $92.10 |
| Monitoring (CloudWatch, ECR, CloudTrail) | $17.45 |
| **TOTAL MONTHLY (On-Demand + Spot)** | **$1,538.93** |
| **TOTAL ANNUAL (On-Demand + Spot)** | **$18,467.16** |

### Cost Comparison: ECS vs EKS

| | ECS (Previous) | EKS (Current) | Difference |
|---|---|---|---|
| Monthly | $1,245.40 | $1,538.93 | +$293.53 (+24%) |
| Annual | $14,944.80 | $18,467.16 | +$3,522.36 |

EKS costs more due to:
- EKS control plane fee: +$73/month
- Larger worker nodes (c6i.xlarge vs Fargate tasks): +$127/month (but better bin-packing)
- System node group for cluster services: +$66/month
- VPC Endpoints for ECR/STS: +$22/month
- Trade-off: EKS provides full Kubernetes API, Karpenter flexibility, Helm ecosystem, multi-cloud portability

---

## 6. Cost with Savings Plans / Reserved Instances

| Scenario | Monthly Est. | Annual Est. | Savings vs On-Demand |
|---|---|---|---|
| On-Demand + Spot (baseline) | $1,538.93 | $18,467.16 | — |
| 1-Year Compute Savings Plan (EC2 nodes + RDS + ElastiCache) | ~$1,100 | ~$13,200 | ~28% |
| 1-Year Savings Plan + Spot batch | ~$1,090 | ~$13,080 | ~29% |
| 3-Year Reserved + Graviton migration | ~$850 | ~$10,200 | ~45% |

---

## 7. BOM Line Item Count

| # | AWS Service | Purpose | Specification |
|---|---|---|---|
| 1 | Amazon EKS | Kubernetes control plane | 1 cluster, standard support |
| 2 | EC2 (c6i.xlarge) | EKS web worker nodes | 2–4 nodes, managed node group |
| 3 | EC2 (t3.medium) | EKS system worker nodes | 2 nodes, managed node group |
| 4 | EC2 (m6i.xlarge/2xlarge) | EKS batch worker nodes | 0–4 nodes, Karpenter (Spot) |
| 5 | Amazon EBS (gp3) | Node root volumes | 50 GiB (web/batch), 30 GiB (system) |
| 6 | Amazon CloudFront | CDN, edge caching | Standard distribution, Origin Shield |
| 7 | Amazon Route 53 | DNS management | 1 hosted zone, health checks |
| 8 | Application Load Balancer | Layer 7 load balancing | 1 ALB via AWS LB Controller |
| 9 | Amazon ElastiCache (Redis) | In-memory caching | cache.r6g.large, 1 primary + 1 replica |
| 10 | Amazon RDS (PostgreSQL) | Relational database | db.r6g.large, Multi-AZ + 1 read replica |
| 11 | Amazon S3 | Batch data staging | Standard, 50 GiB |
| 12 | Amazon ECR | Container image registry | 5 GiB |
| 13 | Amazon VPC | Network isolation | 1 VPC, 2 AZs, public + private subnets |
| 14 | NAT Gateway | Outbound internet for private subnets | 2 (1 per AZ) |
| 15 | VPC Endpoints | Private access to ECR, S3, STS | 3 interface + 1 gateway |
| 16 | AWS Certificate Manager | TLS certificates | 2 public certs |
| 17 | Amazon CloudWatch | Monitoring, Container Insights, alarms | Metrics, logs, 10 alarms |
| 18 | AWS CloudTrail | API audit logging | 1 trail (free tier) |

**Total: 18 AWS services/components**

---

## Notes & Assumptions

1. Traffic estimate: ~10M requests/month, 500 GiB data transfer out via CloudFront
2. Batch volumes: daily=10K, monthly=50K–100K, quarterly=150K–300K, annual=500K–1M records
3. EKS cluster runs Kubernetes standard support version ($0.10/hr, not extended support at $0.60/hr)
4. Web tier: 2–8 pods on 2–4 c6i.xlarge nodes; batch tier: 1–8 pods on 0–4 m6i nodes (Spot)
5. Spot pricing estimated at ~35% of on-demand for m6i family; actual prices fluctuate
6. VPC Endpoints for ECR avoid NAT Gateway charges for container image pulls
7. All prices are us-east-1 on-demand rates as of early 2026
8. Pricing sources: [AWS EKS Pricing](https://aws.amazon.com/eks/pricing/), [AWS EC2 Pricing](https://aws.amazon.com/ec2/pricing/on-demand/), [Holori Calculator](https://calculator.holori.com/)
