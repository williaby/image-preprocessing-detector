# Kubernetes Deployment

Kubernetes manifests for deploying the Image Preprocessing Detector API.

## Prerequisites

- Kubernetes cluster (1.25+)
- kubectl configured
- NGINX Ingress Controller (for ingress)
- cert-manager (for TLS, optional)

## Quick Start

```bash
# Create namespace and deploy all resources
kubectl apply -k k8s/

# Or apply individually
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/ingress.yaml
```

## Configuration

### Secrets

**Important**: The `secret.yaml` file contains placeholder values. For production:

```bash
# Create secret with real API keys
kubectl create secret generic imgprep-secret \
  --from-literal=IMGPREP_API_AUTH_ENABLED=true \
  --from-literal=IMGPREP_API_API_KEYS='key1,key2,key3' \
  --from-literal=IMGPREP_API_INTERNAL_CALLERS='["10.0.0.0/8"]' \
  --namespace=imgprep

# Or use sealed-secrets for GitOps
kubeseal --format=yaml < k8s/secret.yaml > k8s/sealed-secret.yaml
```

### ConfigMap

Edit `configmap.yaml` to adjust:
- Rate limiting settings
- Processing limits
- Timeout values
- Default processing options

### Ingress

1. Update the host in `ingress.yaml` with your domain
2. For TLS, uncomment the TLS section and configure cert-manager

## Scaling

The HPA automatically scales pods based on CPU (70%) and memory (80%) utilization:

```bash
# Check HPA status
kubectl get hpa -n imgprep

# Manual scaling (overrides HPA temporarily)
kubectl scale deployment imgprep-api --replicas=5 -n imgprep
```

## Monitoring

```bash
# Check deployment status
kubectl get pods -n imgprep
kubectl get deployments -n imgprep

# View logs
kubectl logs -f deployment/imgprep-api -n imgprep

# Port forward for local access
kubectl port-forward svc/imgprep-api 8000:80 -n imgprep

# Health check
curl http://localhost:8000/health
```

## Resource Requirements

| Resource | Request | Limit |
|----------|---------|-------|
| CPU | 250m | 1000m |
| Memory | 512Mi | 2Gi |

Adjust in `deployment.yaml` based on workload.

## Production Considerations

1. **Secrets Management**: Use external-secrets, vault, or sealed-secrets
2. **TLS**: Configure cert-manager with Let's Encrypt
3. **Monitoring**: Add Prometheus ServiceMonitor
4. **Logging**: Configure log aggregation (EFK/Loki)
5. **Network Policies**: Restrict pod-to-pod communication
6. **PodDisruptionBudget**: Add for high availability
