# Quick Start Guide - Resume App with Monitoring

## 🚀 Start the Application

```bash
docker compose up -d --build
```

## 🔗 Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| **Frontend** | http://localhost:8501 | - |
| **Backend API** | http://localhost:8000 | - |
| **Grafana Dashboard** | http://localhost:3000 | admin/admin |
| **Prometheus** | http://localhost:9090 | - |
| **Loki API** | http://localhost:3100 | - |

## 📊 Grafana Dashboard Features

### Metrics (Top)
- **System Uptime** - Server uptime in minutes
- **CPU Usage** - 5-minute average CPU utilization
- **Memory Usage** - Current memory consumption
- **Total Resumes Reviewed** - Cumulative count of all reviews
- **Avg Review Generation Time** - Average time to generate reviews
- **Requests Over Time** - HTTP request trends
- **API Throughput** - Requests per second
- **Error Rates** - 4xx and 5xx errors
- **Avg Request Duration** - API response time
- **Latency Percentiles** - p50, p90, p95, p99 latencies

### Logs (Bottom Left And Right)
- **Application Logs (Info/Debug)** - Normal operation logs
- **Application Logs (Errors/Warnings)** - Issues and warnings

## 🧪 Test the Setup

### 1. Generate Metrics
```bash
# Upload a resume via the frontend
open http://localhost:8501

# Or use curl
curl -X POST http://localhost:8000/api/v1/review \
  -F "file=@CV_v1.pdf"
```

### 2. View Logs
```bash
# Run the test script
./test_logging.sh

# Or query directly
curl -s -G "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={compose_service="backend"}' \
  --data-urlencode 'limit=10' | jq -r '.data.result[0].values[] | .[1]'
```

### 3. Check Metrics
```bash
# Via Prometheus
curl http://localhost:8000/metrics

# Total reviews
curl -s "http://localhost:9090/api/v1/query?query=sum(resume_reviews_total)" | jq

# Avg review time
curl -s "http://localhost:9090/api/v1/query?query=sum(rate(review_generation_seconds_sum[5m]))/sum(rate(review_generation_seconds_count[5m]))" | jq
```

## 🛑 Stop the Application

```bash
docker compose down
```


## 🐛 Troubleshooting

### Check Container Status
```bash
docker ps
docker logs resume_app_backend
docker logs resume_loki
docker logs resume_promtail
```

### Verify Loki is Ready
```bash
curl http://localhost:3100/ready
```

### Check Available Log Labels
```bash
curl http://localhost:3100/loki/api/v1/labels | jq
```

### Restart Services
```bash
docker compose restart
```

## 🎯 What's Monitored

### Prometheus Metrics
- ✅ Total resumes reviewed (by status)
- ✅ Review generation time (histogram)
- ✅ File upload sizes
- ✅ HTTP request metrics (auto-instrumented)
- ✅ System metrics (CPU, memory, disk, network)

### Loki Logs
- ✅ Application logs (backend & frontend)
- ✅ Parsed log levels (INFO, DEBUG, WARNING, ERROR, CRITICAL)
- ✅ Separated into info and error panels
- ✅ Real-time log streaming
- ✅ 7-day retention


## 🚨 Important Notes

- Loki takes ~15 seconds to fully start (wait for "ready" status)
- Logs are retained for 7 days (configurable)
- Dashboard updates every 5 seconds
- First metrics appear after first resume upload
