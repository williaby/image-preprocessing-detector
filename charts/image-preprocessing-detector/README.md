<!--
SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>

SPDX-License-Identifier: MIT
-->

# Image Preprocessing Detector Helm Chart

Helm chart for deploying the Image Preprocessing Detector API to Kubernetes.

## Prerequisites

- Kubernetes 1.20+
- Helm 3.8+
- PV provisioner support in the underlying infrastructure (optional, for model persistence)

## Installing the Chart

### Development Environment

```bash
helm install imgprep-api ./charts/image-preprocessing-detector \
  -f charts/image-preprocessing-detector/values-dev.yaml \
  --namespace imgprep-dev \
  --create-namespace
```

### Staging Environment

```bash
helm install imgprep-api ./charts/image-preprocessing-detector \
  --namespace imgprep-staging \
  --create-namespace \
  --set image.tag=v1.0.0-rc.1
```

### Production Environment

```bash
helm install imgprep-api ./charts/image-preprocessing-detector \
  -f charts/image-preprocessing-detector/values-prod.yaml \
  --namespace imgprep-prod \
  --create-namespace \
  --set image.tag=v1.0.0 \
  --set secrets.apiKeys="prod-key-1,prod-key-2"
```

## Upgrading the Chart

```bash
# Development
helm upgrade imgprep-api ./charts/image-preprocessing-detector \
  -f charts/image-preprocessing-detector/values-dev.yaml \
  --namespace imgprep-dev

# Production
helm upgrade imgprep-api ./charts/image-preprocessing-detector \
  -f charts/image-preprocessing-detector/values-prod.yaml \
  --namespace imgprep-prod \
  --set image.tag=v1.1.0
```

## Uninstalling the Chart

```bash
helm uninstall imgprep-api --namespace imgprep-dev
```

## Configuration

See [values.yaml](values.yaml) for all available configuration options.

### Key Configuration Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `2` |
| `image.repository` | Image repository | `image-preprocessing-detector` |
| `image.tag` | Image tag | `latest` |
| `resources.limits.cpu` | CPU limit | `2000m` |
| `resources.limits.memory` | Memory limit | `4Gi` |
| `config.authEnabled` | Enable API key authentication | `true` |
| `config.rateLimitEnabled` | Enable rate limiting | `true` |
| `autoscaling.enabled` | Enable HPA | `true` |
| `autoscaling.minReplicas` | Minimum replicas | `2` |
| `autoscaling.maxReplicas` | Maximum replicas | `10` |

### GPU Support

To enable GPU support:

```yaml
gpu:
  enabled: true
  count: 1
  type: "nvidia.com/gpu"

nodeSelector:
  accelerator: nvidia-tesla-t4
```

### Ingress Configuration

```yaml
ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
  hosts:
    - host: api.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: imgprep-api-tls
      hosts:
        - api.example.com
```

## Examples

### Override specific values

```bash
helm install imgprep-api ./charts/image-preprocessing-detector \
  --set replicaCount=3 \
  --set image.tag=v1.2.0 \
  --set config.maxFileSizeMb=100
```

### Use custom values file

```bash
helm install imgprep-api ./charts/image-preprocessing-detector \
  -f my-custom-values.yaml
```

### Dry run to see generated manifests

```bash
helm install imgprep-api ./charts/image-preprocessing-detector \
  -f values-prod.yaml \
  --dry-run --debug
```

## Monitoring

The chart includes Prometheus annotations by default:

```yaml
podAnnotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8000"
  prometheus.io/path: "/metrics"
```

## Troubleshooting

### Check pod logs

```bash
kubectl logs -l app.kubernetes.io/name=image-preprocessing-detector -n imgprep-prod
```

### Check pod status

```bash
kubectl get pods -l app.kubernetes.io/name=image-preprocessing-detector -n imgprep-prod
```

### Describe deployment

```bash
kubectl describe deployment imgprep-api -n imgprep-prod
```

### Test API health

```bash
kubectl port-forward svc/imgprep-api 8080:80 -n imgprep-prod
curl http://localhost:8080/health
```

## License

See project LICENSE file.
