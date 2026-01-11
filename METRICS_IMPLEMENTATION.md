# Custom Prometheus Metrics Implementation

## Overview
This document describes the custom Prometheus metrics implemented for the Resume Reviewer application.

## Metrics Implemented

### 1. Total Resumes Reviewed
- **Metric Name**: `resume_reviews_total`
- **Type**: Counter
- **Location**: `app.py` (lines 29-33)
- **Labels**: `status` (success, failed_type, failed_size, failed_service, failed_processing)
- **Description**: Tracks the total number of resume reviews processed, categorized by status

**Implementation Details**:
```python
RESUME_REVIEWS_TOTAL = Counter(
    "resume_reviews_total",
    "Total number of resume reviews processed",
    ["status"]
)
```

**Tracked at**:
- Line 82: `RESUME_REVIEWS_TOTAL.labels(status="failed_type").inc()` - Invalid file type
- Line 88: `RESUME_REVIEWS_TOTAL.labels(status="failed_size").inc()` - File too large
- Line 96: `RESUME_REVIEWS_TOTAL.labels(status="failed_service").inc()` - Service not initialized
- Line 119: `RESUME_REVIEWS_TOTAL.labels(status="success").inc()` - Successful review
- Line 129: `RESUME_REVIEWS_TOTAL.labels(status="failed_processing").inc()` - Processing error

### 2. Review Generation Time
- **Metric Name**: `review_generation_seconds`
- **Type**: Histogram
- **Location**: `app.py` (lines 34-38)
- **Buckets**: [1, 5, 10, 20, 30, 45, 60, 90, 120] seconds
- **Description**: Measures the time spent generating resume reviews from start to finish

**Implementation Details**:
```python
REVIEW_GENERATION_TIME = Histogram(
    "review_generation_seconds",
    "Time spent generating the resume review",
    buckets=[1, 5, 10, 20, 30, 45, 60, 90, 120]
)
```

**Tracked at**:
- Line 113: `with REVIEW_GENERATION_TIME.time():` - Wraps the entire review generation process

## Grafana Dashboard

### New Panels Added

#### Panel 1: Total Resumes Reviewed
- **Type**: Stat
- **Query**: `sum(resume_reviews_total)`
- **Position**: Top row, right side (x: 14, y: 0)
- **Size**: 5 wide x 6 high
- **Display**: Blue colored value with area graph background
- **Description**: Shows the cumulative total of all resumes reviewed across all statuses

#### Panel 2: Average Review Generation Time
- **Type**: Stat
- **Query**: `sum(rate(review_generation_seconds_sum[5m])) / sum(rate(review_generation_seconds_count[5m]))`
- **Position**: Top row, far right (x: 19, y: 0)
- **Size**: 5 wide x 6 high
- **Unit**: Seconds (with 2 decimal places)
- **Thresholds**: 
  - Green: < 20s
  - Yellow: 20-40s
  - Red: > 40s
- **Display**: Colored value with area graph background
- **Description**: Shows the average time to generate a review over the last 5 minutes

## How to Access

1. **Prometheus**: http://localhost:9090
   - View raw metrics at: http://localhost:9090/metrics
   - Query metrics using PromQL

2. **Grafana**: http://localhost:3000
   - Default credentials: admin/admin
   - Dashboard: "Resume Ops & System Dashboard"
   - The new metrics are displayed in stat panels on the top row

## Prometheus Queries

### Total Resumes Reviewed
```promql
sum(resume_reviews_total)
```

### Total Successful Reviews
```promql
sum(resume_reviews_total{status="success"})
```

### Average Review Generation Time (5m window)
```promql
sum(rate(review_generation_seconds_sum[5m])) / sum(rate(review_generation_seconds_count[5m]))
```

### Review Generation Time Percentiles
```promql
# 95th percentile
histogram_quantile(0.95, sum(rate(review_generation_seconds_bucket[5m])) by (le))

# 99th percentile
histogram_quantile(0.99, sum(rate(review_generation_seconds_bucket[5m])) by (le))
```

## Testing the Metrics

To test the metrics:

1. Upload a resume through the Streamlit frontend at http://localhost:8501
2. Wait for the review to complete
3. Check Grafana dashboard at http://localhost:3000
4. The "Total Resumes Reviewed" should increment by 1
5. The "Avg Review Generation Time" should show the time taken

## Additional Metrics Available

The application also tracks these metrics automatically via `prometheus-fastapi-instrumentator`:

- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - HTTP request latency
- `uploaded_file_size_bytes` - Size of uploaded files

All system metrics from node-exporter are also available (CPU, memory, disk, network, etc.)
