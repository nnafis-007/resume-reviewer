# Grafana Loki Logging Setup

## Overview
This document describes the Grafana Loki log aggregation setup for the Resume Reviewer application.

## Architecture

### Components

1. **Loki** (Port 3100)
   - Log aggregation system
   - Stores and indexes logs
   - Provides LogQL query interface

2. **Promtail**
   - Log collection agent
   - Scrapes logs from Docker containers
   - Parses and labels logs before sending to Loki

3. **Grafana**
   - Visualization layer
   - Displays logs using Loki datasource
   - Provides LogQL query interface

## Configuration

### Loki Configuration (`loki/loki-config.yml`)
- **Storage**: Filesystem-based (local development)
- **Retention**: 7 days (168 hours)
- **Schema**: v13 with TSDB
- **Rate Limits**: 10MB/s ingestion rate

### Promtail Configuration (`promtail/promtail-config.yml`)
- **Log Source**: Docker containers via socket
- **Filters**: Only scrapes containers from `resume-app` project
- **Labels**: 
  - `job`: Container name
  - `container`: Container name
  - `compose_service`: Service name from docker-compose
  - `level`: Log level (INFO, DEBUG, WARNING, ERROR, CRITICAL)
  - `logger`: Python logger name

### Log Parsing
Promtail automatically parses two log formats:

1. **Python Logging Format**:
   ```
   2026-01-12 10:30:45,123 - module.name - INFO - Log message
   ```

2. **Uvicorn/FastAPI Format**:
   ```
   INFO:     Log message
   ```

## Grafana Dashboard

### Log Panels

#### 1. Application Logs (Info/Debug)
- **Location**: Right side, middle
- **LogQL Query**: 
  ```logql
  {compose_service=~"backend|frontend"} |~ "INFO|DEBUG" !~ "ERROR|WARNING|CRITICAL"
  ```
- **Purpose**: Shows normal application operation logs
- **Filters**: INFO and DEBUG level logs, excludes errors

#### 2. Application Logs (Errors/Warnings)
- **Location**: Right side, bottom
- **LogQL Query**: 
  ```logql
  {compose_service=~"backend|frontend"} |~ "ERROR|WARNING|CRITICAL"
  ```
- **Purpose**: Shows errors and warnings for troubleshooting
- **Filters**: ERROR, WARNING, and CRITICAL level logs

## LogQL Query Examples

### Basic Queries

1. **All logs from backend**:
   ```logql
   {compose_service="backend"}
   ```

2. **All error logs**:
   ```logql
   {compose_service=~"backend|frontend"} |~ "ERROR"
   ```

3. **Logs containing "resume"**:
   ```logql
   {compose_service=~"backend|frontend"} |~ "(?i)resume"
   ```

4. **Logs from specific logger**:
   ```logql
   {logger="services.resume_service"}
   ```

### Advanced Queries

1. **Error rate (last 5 minutes)**:
   ```logql
   sum(rate({compose_service=~"backend|frontend"} |~ "ERROR" [5m]))
   ```

2. **Log count by level**:
   ```logql
   sum by (level) (count_over_time({compose_service=~"backend|frontend"}[5m]))
   ```

3. **Logs with response time > 1s**:
   ```logql
   {compose_service="backend"} |~ "duration.*[1-9][0-9]{3,}"
   ```

## Accessing Logs

### Via Grafana
1. Open Grafana at **http://localhost:3000**
2. Navigate to "Resume Ops & System Dashboard"
3. View logs in the two panels on the right side

### Via Loki API
Query logs directly using curl:

```bash
# Get recent logs
curl -G -s "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={compose_service="backend"}' \
  --data-urlencode 'limit=100' | jq

# Get error logs
curl -G -s "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={compose_service="backend"} |~ "ERROR"' \
  --data-urlencode 'limit=50' | jq
```

### Via LogCLI (Optional)
Install LogCLI for command-line log queries:

```bash
# Install
go install github.com/grafana/loki/cmd/logcli@latest

# Query logs
logcli query '{compose_service="backend"}' --addr=http://localhost:3100
```

## Performance Considerations

1. **Non-Blocking**: Promtail collects logs asynchronously without blocking the application
2. **Buffering**: Promtail buffers logs locally before sending to Loki
3. **Rate Limiting**: Loki is configured with rate limits to prevent overload
4. **Retention**: Logs are retained for 7 days to balance storage and observability

## Troubleshooting

### Check Promtail Status
```bash
docker logs resume_promtail
```

### Check Loki Status
```bash
docker logs resume_loki
curl http://localhost:3100/ready
```

### Check if Logs are Being Ingested
```bash
curl -G -s "http://localhost:3100/loki/api/v1/labels" | jq
```

### View Available Label Values
```bash
# Check available compose services
curl -G -s "http://localhost:3100/loki/api/v1/label/compose_service/values" | jq

# Check available log levels
curl -G -s "http://localhost:3100/loki/api/v1/label/level/values" | jq
```

## Testing

To generate test logs:

1. Upload a resume via the frontend at **http://localhost:8501**
2. Check the logs in Grafana
3. Try uploading an invalid file to generate error logs

## Log Levels in Application

The application uses Python's logging module with these levels:

- **DEBUG**: Detailed diagnostic information
- **INFO**: Confirmation that things are working (default)
- **WARNING**: Something unexpected happened
- **ERROR**: Software error occurred
- **CRITICAL**: Serious error, program may not continue

## Benefits

1. **Centralized Logging**: All container logs in one place
2. **Powerful Queries**: LogQL allows complex log searches
3. **Real-time Monitoring**: See logs as they happen
4. **Debugging**: Quickly identify errors and trace issues
5. **No Application Changes**: Works with existing logging
6. **Performance**: Asynchronous collection doesn't slow down the app
