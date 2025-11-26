---
schema_type: common
title: "Log Aggregation Pipeline Guide"
description: "Guide for log aggregation with ELK, Vector, and CloudWatch"
tags:
  - guide
  - logging
  - infrastructure
  - monitoring
status: published
owner: core-maintainer
authors:
  - name: "Byron Williams"
purpose: "Document log aggregation options and configurations for production deployments."
---

This guide covers log aggregation options for the Image Preprocessing Detector, including ELK Stack, Vector, and CloudWatch configurations.

## Overview

The logging framework outputs structured JSON logs that are compatible with common log aggregation systems:

- **ELK Stack** (Elasticsearch, Logstash, Kibana): Full-featured search and visualization
- **Vector**: Lightweight, high-performance log routing
- **CloudWatch**: AWS-native logging for cloud deployments

---

## Log Format

All logs follow this JSON structure:

```json
{
  "timestamp": "2025-01-15T10:30:00.123456Z",
  "level": "INFO",
  "event": "page_processed",
  "correlation_id": "req-abc123",
  "service": "image-preprocessing-detector",
  "version": "0.1.0",
  "environment": "production",
  "document_id": "doc_20250115_001",
  "page_index": 0,
  "duration_ms": 145.3,
  "model_used": "student",
  "device": "cpu"
}
```

### Key Fields

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | ISO 8601 | UTC timestamp with microseconds |
| `level` | string | DEBUG, INFO, WARNING, ERROR |
| `event` | string | Event type (snake_case) |
| `correlation_id` | string | Request tracking ID |
| `service` | string | Service name |
| `version` | string | Application version |
| `environment` | string | Deployment environment |

---

## ELK Stack Integration

### Architecture

```text
Application → Filebeat → Logstash → Elasticsearch → Kibana
     ↓
  JSON Logs
```text

### Filebeat Configuration

```yaml
# filebeat.yml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/imgprep/*.log
    json.keys_under_root: true
    json.overwrite_keys: true
    json.add_error_key: true
    json.expand_keys: true
    fields:
      service: image-preprocessing-detector
      environment: production
    fields_under_root: true

processors:
  - timestamp:
      field: timestamp
      layouts:
        - '2006-01-02T15:04:05.999999Z07:00'
      target_field: '@timestamp'
  - drop_fields:
      fields: ['host', 'agent', 'ecs']
      ignore_missing: true

output.logstash:
  hosts: ["logstash:5044"]
  ssl.enabled: true
  ssl.certificate_authorities: ["/etc/filebeat/ca.crt"]
```

### Logstash Pipeline

```ruby
# logstash/pipeline/imgprep.conf
input {
  beats {
    port => 5044
    ssl => true
    ssl_certificate => "/etc/logstash/certs/logstash.crt"
    ssl_key => "/etc/logstash/certs/logstash.key"
  }
}

filter {
  # Parse correlation_id for request grouping
  if [correlation_id] {
    mutate {
      add_field => { "request_group" => "%{correlation_id}" }
    }
  }

  # Extract error details
  if [level] == "ERROR" {
    if [error_code] {
      mutate {
        add_tag => ["error", "%{error_code}"]
      }
    }
  }

  # Calculate latency buckets
  if [duration_ms] {
    ruby {
      code => '
        duration = event.get("duration_ms").to_f
        bucket = case duration
          when 0..50 then "fast"
          when 50..200 then "normal"
          when 200..500 then "slow"
          else "very_slow"
        end
        event.set("latency_bucket", bucket)
      '
    }
  }

  # Enrich with geo (if client_ip present)
  if [client_ip] {
    geoip {
      source => "client_ip"
      target => "geo"
    }
  }

  # Tag teacher model usage
  if [model_used] == "teacher" {
    mutate {
      add_tag => ["teacher_inference"]
    }
  }

  # Tag Modal GPU usage
  if [device] == "modal_gpu" {
    mutate {
      add_tag => ["modal_usage"]
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "imgprep-logs-%{+YYYY.MM.dd}"
    user => "${ELASTIC_USER}"
    password => "${ELASTIC_PASSWORD}"
  }
}
```

### Elasticsearch Index Template

```json
{
  "index_patterns": ["imgprep-logs-*"],
  "template": {
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 1,
      "index.lifecycle.name": "imgprep-logs-policy",
      "index.lifecycle.rollover_alias": "imgprep-logs"
    },
    "mappings": {
      "properties": {
        "@timestamp": { "type": "date" },
        "level": { "type": "keyword" },
        "event": { "type": "keyword" },
        "correlation_id": { "type": "keyword" },
        "service": { "type": "keyword" },
        "version": { "type": "keyword" },
        "environment": { "type": "keyword" },
        "document_id": { "type": "keyword" },
        "page_index": { "type": "integer" },
        "duration_ms": { "type": "float" },
        "model_used": { "type": "keyword" },
        "device": { "type": "keyword" },
        "error_code": { "type": "keyword" },
        "latency_bucket": { "type": "keyword" },
        "message": { "type": "text" },
        "details": { "type": "object", "enabled": false }
      }
    }
  }
}
```

### Kibana Dashboards

Create these visualizations in Kibana:

1. **Request Volume** - Line chart of events over time
2. **Error Rate** - Percentage of ERROR level events
3. **Latency Distribution** - Histogram of `duration_ms`
4. **Model Usage** - Pie chart of `model_used` field
5. **Device Distribution** - Bar chart of `device` field
6. **Error Codes** - Data table of `error_code` counts

---

## Vector Integration

Vector is a lightweight alternative to the ELK stack, ideal for container environments.

### Architecture

```text
Application → Vector → (Multiple Sinks)
     ↓           ↓
  JSON Logs   ├─→ Elasticsearch
              ├─→ CloudWatch
              ├─→ S3/GCS
              └─→ Datadog
```text

### Vector Configuration

```toml
# vector.toml

# Sources
[sources.imgprep_logs]
type = "file"
include = ["/var/log/imgprep/*.log"]
read_from = "beginning"

[sources.imgprep_logs.encoding]
codec = "json"

# Transforms
[transforms.parse_timestamp]
type = "remap"
inputs = ["imgprep_logs"]
source = '''
  .timestamp = parse_timestamp!(.timestamp, "%Y-%m-%dT%H:%M:%S%.fZ")
'''

[transforms.add_metadata]
type = "remap"
inputs = ["parse_timestamp"]
source = '''
  .host = get_hostname!()
  .pipeline_version = "1.0.0"
'''

[transforms.filter_errors]
type = "filter"
inputs = ["add_metadata"]
condition = '.level == "ERROR"'

[transforms.sample_debug]
type = "sample"
inputs = ["add_metadata"]
rate = 10
condition = '.level == "DEBUG"'

[transforms.aggregate_latency]
type = "aggregate"
inputs = ["add_metadata"]
interval_ms = 60000
group_by = ["model_used", "device"]
source = '''
  .latency_p50 = quantile!(.duration_ms, 0.5)
  .latency_p99 = quantile!(.duration_ms, 0.99)
  .count = count!()
'''

# Sinks - Elasticsearch
[sinks.elasticsearch]
type = "elasticsearch"
inputs = ["add_metadata"]
endpoints = ["http://elasticsearch:9200"]
bulk.index = "imgprep-logs-%Y.%m.%d"
auth.strategy = "basic"
auth.user = "${ELASTIC_USER}"
auth.password = "${ELASTIC_PASSWORD}"

# Sinks - S3 for long-term storage
[sinks.s3_archive]
type = "aws_s3"
inputs = ["add_metadata"]
bucket = "imgprep-logs-archive"
region = "us-east-1"
key_prefix = "logs/%Y/%m/%d/"
compression = "gzip"
encoding.codec = "json"
batch.max_bytes = 10485760
batch.timeout_secs = 300

# Sinks - CloudWatch for AWS deployments
[sinks.cloudwatch]
type = "aws_cloudwatch_logs"
inputs = ["add_metadata"]
group_name = "/imgprep/application"
stream_name = "{{ host }}"
region = "us-east-1"
encoding.codec = "json"

# Sinks - Error alerts to Slack
[sinks.slack_errors]
type = "http"
inputs = ["filter_errors"]
uri = "https://hooks.slack.com/services/${SLACK_WEBHOOK}"
method = "post"
encoding.codec = "json"
request.headers.Content-Type = "application/json"
```

### Docker Compose with Vector

```yaml
# docker-compose.logging.yml
version: '3.8'

services:
  imgprep-api:
    image: image-preprocessing-detector:latest
    volumes:
      - logs:/var/log/imgprep
    environment:
      - IMGPREP_LOG_TO_FILE=true
      - IMGPREP_LOG_PATH=/var/log/imgprep
      - IMGPREP_JSON_LOGS=true

  vector:
    image: timberio/vector:0.34.0-alpine
    volumes:
      - ./vector.toml:/etc/vector/vector.toml:ro
      - logs:/var/log/imgprep:ro
    environment:
      - ELASTIC_USER=${ELASTIC_USER}
      - ELASTIC_PASSWORD=${ELASTIC_PASSWORD}
      - SLACK_WEBHOOK=${SLACK_WEBHOOK}
    depends_on:
      - imgprep-api

volumes:
  logs:
```

---

## AWS CloudWatch Integration

### Direct CloudWatch Logging

For AWS deployments, logs can be sent directly to CloudWatch:

```python
# Enable CloudWatch handler
import logging
import watchtower

# Configure CloudWatch handler
cloudwatch_handler = watchtower.CloudWatchLogHandler(
    log_group_name="/imgprep/application",
    log_stream_name=f"{hostname}-{environment}",
    use_queues=True,
    send_interval=60,
    max_batch_size=10000,
)

# Add to structlog
logging.getLogger("imgprep").addHandler(cloudwatch_handler)
```

### CloudWatch Log Insights Queries

```sql
-- Error rate by hour
fields @timestamp, @message
| filter level = "ERROR"
| stats count(*) as errors by bin(1h)

-- Latency percentiles
fields duration_ms
| filter ispresent(duration_ms)
| stats pct(duration_ms, 50) as p50,
        pct(duration_ms, 95) as p95,
        pct(duration_ms, 99) as p99
  by bin(5m)

-- Teacher model usage
fields @timestamp, model_used, device
| filter model_used = "teacher"
| stats count(*) by device, bin(1h)

-- Error codes breakdown
fields @timestamp, error_code, message
| filter level = "ERROR"
| stats count(*) by error_code

-- Request tracing
fields @timestamp, event, duration_ms
| filter correlation_id = "req-abc123"
| sort @timestamp asc
```

### CloudWatch Alarms

```yaml
# cloudformation/alarms.yml
AWSTemplateFormatVersion: '2010-09-09'

Resources:
  ErrorRateAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: imgprep-error-rate-high
      MetricName: ErrorCount
      Namespace: ImgPrep/Application
      Statistic: Sum
      Period: 300
      EvaluationPeriods: 2
      Threshold: 10
      ComparisonOperator: GreaterThanThreshold
      AlarmActions:
        - !Ref AlertSNSTopic

  LatencyAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: imgprep-latency-high
      MetricName: ProcessingLatency
      Namespace: ImgPrep/Application
      ExtendedStatistic: p99
      Period: 300
      EvaluationPeriods: 3
      Threshold: 500
      ComparisonOperator: GreaterThanThreshold
      AlarmActions:
        - !Ref AlertSNSTopic

  TeacherUsageAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: imgprep-teacher-usage-high
      MetricName: TeacherInferenceCount
      Namespace: ImgPrep/Application
      Statistic: Sum
      Period: 3600
      EvaluationPeriods: 1
      Threshold: 100
      ComparisonOperator: GreaterThanThreshold
      AlarmActions:
        - !Ref AlertSNSTopic
```

---

## Kubernetes Logging

### Fluent Bit DaemonSet

```yaml
# k8s/logging/fluent-bit.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: logging
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush         5
        Log_Level     info
        Daemon        off
        Parsers_File  parsers.conf

    [INPUT]
        Name              tail
        Tag               imgprep.*
        Path              /var/log/containers/imgprep*.log
        Parser            docker
        DB                /var/log/flb_imgprep.db
        Mem_Buf_Limit     50MB
        Skip_Long_Lines   On
        Refresh_Interval  10

    [FILTER]
        Name         kubernetes
        Match        imgprep.*
        Kube_URL     https://kubernetes.default.svc:443
        Kube_CA_File /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        Kube_Token_File /var/run/secrets/kubernetes.io/serviceaccount/token
        Labels       On
        Annotations  Off

    [FILTER]
        Name   parser
        Match  imgprep.*
        Key_Name log
        Parser json
        Reserve_Data On

    [OUTPUT]
        Name            es
        Match           imgprep.*
        Host            ${ELASTICSEARCH_HOST}
        Port            9200
        HTTP_User       ${ELASTICSEARCH_USER}
        HTTP_Passwd     ${ELASTICSEARCH_PASSWORD}
        Index           imgprep-logs
        Type            _doc
        Logstash_Format On
        Logstash_Prefix imgprep-logs
        Retry_Limit     3

  parsers.conf: |
    [PARSER]
        Name        docker
        Format      json
        Time_Key    time
        Time_Format %Y-%m-%dT%H:%M:%S.%LZ

    [PARSER]
        Name        json
        Format      json
        Time_Key    timestamp
        Time_Format %Y-%m-%dT%H:%M:%S.%LZ
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit
  namespace: logging
spec:
  selector:
    matchLabels:
      app: fluent-bit
  template:
    metadata:
      labels:
        app: fluent-bit
    spec:
      serviceAccountName: fluent-bit
      tolerations:
        - key: node-role.kubernetes.io/master
          effect: NoSchedule
      containers:
        - name: fluent-bit
          image: fluent/fluent-bit:2.1
          volumeMounts:
            - name: varlog
              mountPath: /var/log
            - name: config
              mountPath: /fluent-bit/etc/
          env:
            - name: ELASTICSEARCH_HOST
              valueFrom:
                secretKeyRef:
                  name: elasticsearch-credentials
                  key: host
            - name: ELASTICSEARCH_USER
              valueFrom:
                secretKeyRef:
                  name: elasticsearch-credentials
                  key: user
            - name: ELASTICSEARCH_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: elasticsearch-credentials
                  key: password
      volumes:
        - name: varlog
          hostPath:
            path: /var/log
        - name: config
          configMap:
            name: fluent-bit-config
```

---

## Log Retention Policies

### Elasticsearch ILM Policy

```json
{
  "policy": {
    "phases": {
      "hot": {
        "actions": {
          "rollover": {
            "max_size": "50GB",
            "max_age": "1d"
          }
        }
      },
      "warm": {
        "min_age": "7d",
        "actions": {
          "shrink": {
            "number_of_shards": 1
          },
          "forcemerge": {
            "max_num_segments": 1
          }
        }
      },
      "cold": {
        "min_age": "30d",
        "actions": {
          "freeze": {}
        }
      },
      "delete": {
        "min_age": "90d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}
```

### S3 Lifecycle Policy

```json
{
  "Rules": [
    {
      "ID": "TransitionToGlacier",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "logs/"
      },
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "GLACIER"
        }
      ],
      "Expiration": {
        "Days": 365
      }
    }
  ]
}
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Logs not appearing | File path mismatch | Verify log path in config |
| Timestamp parsing | Invalid format | Check timestamp format in parser |
| High memory usage | Large batch size | Reduce batch size, increase flush |
| Missing fields | JSON parsing error | Check `json.add_error_key` |
| Duplicate logs | Multiple collectors | Use single collector per host |

### Debug Commands

```bash
# Check log output format
tail -f /var/log/imgprep/app.log | jq '.'

# Verify JSON structure
cat /var/log/imgprep/app.log | head -1 | python -m json.tool

# Test Elasticsearch connection
curl -u $ELASTIC_USER:$ELASTIC_PASSWORD \
  http://elasticsearch:9200/_cat/indices?v

# Check Vector health
curl http://localhost:8686/health

# Query recent logs
curl -X GET "http://elasticsearch:9200/imgprep-logs-*/_search?pretty" \
  -H 'Content-Type: application/json' \
  -d '{"query": {"range": {"@timestamp": {"gte": "now-1h"}}}}'
```

---

## References

- [Elasticsearch Documentation](https://www.elastic.co/guide/index.html)
- [Vector Documentation](https://vector.dev/docs/)
- [AWS CloudWatch Logs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/)
- [Fluent Bit Documentation](https://docs.fluentbit.io/)
