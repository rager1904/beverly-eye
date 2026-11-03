#!/usr/bin/env bash
set -euo pipefail

#=============================================================================
# Zambia Health Platform - Health Monitoring Script
# Monitors system health, services, databases, and AI inference endpoints
#=============================================================================

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly TIMESTAMP=$(date +%Y%m%d-%H%M%S)
readonly LOG_FILE="/var/log/zambia-health/monitor-${TIMESTAMP}.log"
readonly STATE_FILE="/var/run/zambia-health/monitor.state"
readonly THRESHOLD_FILE="/etc/zambia-health/monitor-thresholds.conf"

# Default thresholds
DISK_WARN=80
DISK_CRIT=90
MEM_WARN=80
MEM_CRIT=90
CPU_WARN=80
CPU_CRIT=90
LATENCY_WARN=1000
LATENCY_CRIT=5000
ERROR_RATE_WARN=10
ERROR_RATE_CRIT=50

# Alert configuration
ALERT_METHOD="log"  # log, email, slack, sns
ALERT_DESTINATION=""
SLACK_WEBHOOK=""
SNS_TOPIC_ARN=""

# Check configuration
CHECK_INTERVAL=60
RUN_ONCE=false
VERBOSE=false
EXPORT_PROMETHEUS=false
PROMETHEUS_OUTPUT="/var/lib/prometheus/node-exporter/monitor.prom"

log()   { echo "[$(date +%H:%M:%S)] $*" | tee -a "${LOG_FILE}"; }
warn()  { echo "[WARN] $*" | tee -a "${LOG_FILE}" >&2; }
error() { echo "[ERROR] $*" | tee -a "${LOG_FILE}" >&2; }
debug() { [[ "${VERBOSE}" == "true" ]] && echo "[DEBUG] $*"; }

usage() {
    cat <<EOF
Zambia Health - System Monitoring Script

Usage: $(basename "$0") [options]

Options:
  -i, --interval SECS   Check interval in seconds (default: 60)
  -o, --once           Run once and exit
  -a, --alert METHOD   Alert method: log|email|slack|sns
  -d, --destination DEST Alert destination (email/webhook)
  -v, --verbose        Verbose output
  -p, --prometheus     Export Prometheus metrics
  -h, --help           Show this help message

Examples:
  $(basename "$0") --once --verbose
  $(basename "$0") --interval 300 --alert slack --destination https://hooks.slack.com/...
EOF
    exit 0
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -i|--interval)     CHECK_INTERVAL="$2"; shift 2 ;;
            -o|--once)         RUN_ONCE=true; shift ;;
            -a|--alert)        ALERT_METHOD="$2"; shift 2 ;;
            -d|--destination)  ALERT_DESTINATION="$2"; shift 2 ;;
            -v|--verbose)      VERBOSE=true; shift ;;
            -p|--prometheus)   EXPORT_PROMETHEUS=true; shift ;;
            -h|--help)         usage ;;
            *)                 error "Unknown option: $1"; usage ;;
        esac
    done
}

load_thresholds() {
    if [[ -f "${THRESHOLD_FILE}" ]]; then
        source "${THRESHOLD_FILE}"
        log "Loaded thresholds from ${THRESHOLD_FILE}"
    fi
}

check_disk() {
    local status="ok"
    local message=""
    local critical=false

    while read -r line; do
        local mount=$(echo "${line}" | awk '{print $6}')
        local pct=$(echo "${line}" | awk '{print $5}' | sed 's/%//')

        if [[ "${mount}" == "/dev" || "${mount}" == "/proc" || "${mount}" == "/sys" ]]; then
            continue
        fi

        if [[ "${pct}" -ge "${DISK_CRIT}" ]]; then
            message="${message}CRITICAL: ${mount} at ${pct}% | "
            critical=true
            status="critical"
        elif [[ "${pct}" -ge "${DISK_WARN}" ]]; then
            message="${message}WARNING: ${mount} at ${pct}% | "
            [[ "${status}" == "ok" ]] && status="warning"
        fi
    done < <(df -h | tail -n +2)

    echo "${status}|${message}|${critical}"
}

check_memory() {
    local total used pct status="ok"
    total=$(free -m | awk '/Mem:/ {print $2}')
    used=$(free -m | awk '/Mem:/ {print $3}')
    pct=$((used * 100 / total))

    if [[ "${pct}" -ge "${MEM_CRIT}" ]]; then
        status="critical"
    elif [[ "${pct}" -ge "${MEM_WARN}" ]]; then
        status="warning"
    fi

    echo "${status}|Memory: ${used}MB/${total}MB (${pct}%)"
}

check_cpu() {
    local idle pct status="ok"
    idle=$(top -bn1 | grep "Cpu(s)" | awk '{print $8}' | cut -d. -f1)
    pct=$((100 - idle))

    if [[ "${pct}" -ge "${CPU_CRIT}" ]]; then
        status="critical"
    elif [[ "${pct}" -ge "${CPU_WARN}" ]]; then
        status="warning"
    fi

    echo "${status}|CPU: ${pct}%"
}

check_docker() {
    local status="ok"

    if ! command -v docker >/dev/null 2>&1; then
        echo "critical|Docker not installed"
        return
    fi

    if ! docker info >/dev/null 2>&1; then
        echo "critical|Docker daemon not running"
        return
    fi

    # Check container status
    local unhealthy
    unhealthy=$(docker ps -a --filter "health=unhealthy" --format "{{.Names}}" 2>/dev/null | tr '\n' ',')
    if [[ -n "${unhealthy}" ]]; then
        status="warning"
    fi

    local running=$(docker ps -q 2>/dev/null | wc -l)
    local stopped=$(docker ps -aq 2>/dev/null | wc -l)
    stopped=$((stopped - running))

    echo "${status}|Containers: ${running} running, ${stopped} stopped${unhealthy:+ | Unhealthy: ${unhealthy}}"
}

check_database() {
    local status="ok"
    local message=""

    # Try to check PostgreSQL
    if command -v psql >/dev/null 2>&1; then
        local pg_status
        pg_status=$(PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST:-localhost}" \
            -U "${DB_USER:-postgres}" \
            -d "${DB_NAME:-zambia_health}" \
            -c "SELECT 1" 2>&1) || pg_status=""
        if [[ -z "${pg_status}" ]]; then
            message="${message}PostgreSQL: DOWN | "
            status="critical"
        else
            message="${message}PostgreSQL: OK | "
        fi
    fi

    # Try to check Redis
    if command -v redis-cli >/dev/null 2>&1; then
        if redis-cli -u "${REDIS_URL:-redis://localhost:6379}" PING >/dev/null 2>&1; then
            message="${message}Redis: OK | "
        else
            message="${message}Redis: DOWN | "
            [[ "${status}" == "ok" ]] && status="critical"
        fi
    fi

    echo "${status}|${message}"
}

check_api() {
    local status="ok"
    local message=""
    local endpoints=(
        "https://api.zambia-health.example.com/health"
        "https://api.zambia-health.example.com/ready"
    )

    for endpoint in "${endpoints[@]}"; do
        local start_time elapsed http_code
        start_time=$(date +%s%N)
        http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "${endpoint}" 2>/dev/null || echo "000")
        elapsed=$(( ($(date +%s%N) - start_time) / 1000000 ))

        if [[ "${http_code}" == "000" ]]; then
            message="${message}${endpoint}: DOWN (timeout) | "
            status="critical"
        elif [[ "${http_code}" -ge 500 ]]; then
            message="${message}${endpoint}: ERROR (${http_code}) | "
            [[ "${status}" == "ok" ]] && status="critical"
        elif [[ "${http_code}" -ge 400 ]]; then
            message="${message}${endpoint}: WARN (${http_code}) | "
            [[ "${status}" == "ok" ]] && status="warning"
        else
            message="${message}${endpoint}: OK (${http_code}, ${elapsed}ms) | "
        fi

        # Latency check
        if [[ "${elapsed}" -gt "${LATENCY_CRIT}" ]]; then
            message="${message}[LATENCY_CRIT] | "
            status="critical"
        elif [[ "${elapsed}" -gt "${LATENCY_WARN}" ]]; then
            message="${message}[LATENCY_WARN] | "
            [[ "${status}" == "ok" ]] && status="warning"
        fi
    done

    echo "${status}|${message}"
}

check_gpu() {
    local status="ok"
    local message=""

    if ! command -v nvidia-smi >/dev/null 2>&1; then
        echo "ok|No NVIDIA GPU detected"
        return
    fi

    # GPU utilization
    local gpu_info
    gpu_info=$(nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu \
        --format=csv,noheader,nounits 2>/dev/null) || {
        echo "critical|nvidia-smi failed"
        return
    }

    while IFS=, read -r idx name util mem_used mem_total temp; do
        idx=$(echo "${idx}" | xargs)
        util=$(echo "${util}" | xargs)
        temp=$(echo "${temp}" | xargs)

        message="${message}GPU ${idx} (${name}): util=${util}% temp=${temp}C mem=${mem_used}/${mem_total}MiB | "

        if [[ "${util}" -gt 90 ]]; then
            [[ "${status}" == "ok" ]] && status="warning"
        fi
        if [[ "${temp}" -gt 85 ]]; then
            status="critical"
        fi
    done <<< "${gpu_info}"

    echo "${status}|${message}"
}

export_prometheus() {
    local output_dir
    output_dir=$(dirname "${PROMETHEUS_OUTPUT}")
    mkdir -p "${output_dir}"

    cat > "${PROMETHEUS_OUTPUT}" << PROM
# HELP zambia_health_disk_usage Disk usage percentage
# TYPE zambia_health_disk_usage gauge
zambia_health_disk_usage $(df / | tail -1 | awk '{print $5}' | sed 's/%//')
# HELP zambia_health_memory_usage Memory usage percentage
# TYPE zambia_health_memory_usage gauge
zambia_health_memory_usage $(free -m | awk '/Mem:/ {printf "%.0f", $3/$2 * 100}')
# HELP zambia_health_cpu_usage CPU usage percentage
# TYPE zambia_health_cpu_usage gauge
zambia_health_cpu_usage $(top -bn1 | grep "Cpu(s)" | awk '{print int(100 - $8)}')
# HELP zambia_health_api_response_ms API response time in milliseconds
# TYPE zambia_health_api_response_ms gauge
zambia_health_api_response_ms $(curl -s -o /dev/null -w "%{time_total}" --max-time 10 https://api.zambia-health.example.com/health 2>/dev/null || echo 0)
PROM
}

send_alert() {
    local status="$1"
    local message="$2"

    if [[ "${status}" == "ok" ]]; then
        return 0
    fi

    local color="warning"
    [[ "${status}" == "critical" ]] && color="danger"

    case "${ALERT_METHOD}" in
        log)
            if [[ "${status}" == "critical" ]]; then
                error "ALERT: ${message}"
            else
                warn "ALERT: ${message}"
            fi
            ;;
        slack)
            if [[ -n "${SLACK_WEBHOOK}" ]]; then
                curl -s -X POST "${SLACK_WEBHOOK}" \
                    -H "Content-Type: application/json" \
                    -d "{\"channel\":\"#alerts\",\"username\":\"Monitor Bot\",\"attachments\":[{\"color\":\"${color}\",\"title\":\"${HOSTNAME} - ${status}\",\"text\":\"${message}\"}]}" \
                    >/dev/null 2>&1 || true
            fi
            ;;
        sns)
            if [[ -n "${SNS_TOPIC_ARN}" ]]; then
                aws sns publish \
                    --topic-arn "${SNS_TOPIC_ARN}" \
                    --subject "Zambia Health Alert: ${status}" \
                    --message "${message}" \
                    >/dev/null 2>&1 || true
            fi
            ;;
    esac
}

run_checks() {
    local overall_status="ok"
    local all_messages=""

    # System checks
    local disk mem cpu
    disk=$(check_disk)
    mem=$(check_memory)
    cpu=$(check_cpu)

    # Service checks
    local docker db api gpu
    docker=$(check_docker)
    db=$(check_database)
    api=$(check_api)
    gpu=$(check_gpu)

    # Compile results
    for check in "DISK:${disk}" "MEMORY:${mem}" "CPU:${cpu}" "DOCKER:${docker}" "DATABASE:${db}" "API:${api}" "GPU:${gpu}"; do
        local name="${check%%:*}"
        local data="${check#*:}"
        local check_status="${data%%|*}"
        local check_message="${data#*|}"

        if [[ "${check_status}" == "critical" ]]; then
            overall_status="critical"
        elif [[ "${check_status}" == "warning" && "${overall_status}" != "critical" ]]; then
            overall_status="warning"
        fi

        all_messages="${all_messages}${name}: ${check_status} | ${check_message}"$'\n'
    done

    # Output
    echo "=== Zambia Health Monitor $(date) ==="
    echo "Overall Status: ${overall_status}"
    echo "${all_messages}"

    # Export Prometheus metrics
    if [[ "${EXPORT_PROMETHEUS}" == "true" ]]; then
        export_prometheus
    fi

    # Send alerts if not OK
    if [[ "${overall_status}" != "ok" ]]; then
        send_alert "${overall_status}" "${all_messages}"
    fi

    # Save state
    mkdir -p "$(dirname "${STATE_FILE}")"
    echo "${overall_status}|$(date +%s)|${all_messages}" > "${STATE_FILE}"
}

main() {
    parse_args "$@"
    load_thresholds
    mkdir -p "$(dirname "${LOG_FILE}")"

    log "=== Zambia Health Monitor Started ==="
    log "Interval: ${CHECK_INTERVAL}s | Alert: ${ALERT_METHOD} | Prometheus: ${EXPORT_PROMETHEUS}"

    if [[ "${RUN_ONCE}" == "true" ]]; then
        run_checks
    else
        while true; do
            run_checks
            sleep "${CHECK_INTERVAL}"
        done
    fi
}

main "$@"
