#!/usr/bin/env bash
# cloud-provider-kind helpers for PROFILE=kind-oss (adapted from KCD Argentina demo).
# NOT MetalLB. Podman: --enable-lb-port-mapping.
# shellcheck shell=bash

asf_kind_run_dir() {
  local root
  root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
  printf '%s\n' "${root}/.run/kind-oss"
}

asf_ccm_pidfile() { printf '%s\n' "$(asf_kind_run_dir)/cloud-provider-kind.pid"; }
asf_ccm_logfile() { printf '%s\n' "$(asf_kind_run_dir)/cloud-provider-kind.log"; }
asf_ccm_owned() { printf '%s\n' "$(asf_kind_run_dir)/cloud-provider-kind.owned"; }

asf_ccm_bin() { command -v cloud-provider-kind 2>/dev/null || true; }

asf_ccm_pid_alive() {
  local pid="$1"
  [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null
}

asf_kind_enable_loadbalancer() {
  local name="$1"
  local ctx="kind-${name}"
  local node
  while IFS= read -r node; do
    [[ -z "${node}" ]] && continue
    kubectl --context "${ctx}" label node "${node}" \
      node.kubernetes.io/exclude-from-external-load-balancers- \
      --overwrite >/dev/null 2>&1 || true
  done < <(kubectl --context "${ctx}" get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' 2>/dev/null || true)
}

asf_ensure_cloud_provider_kind() {
  local bin pidfile logfile owned run_dir
  bin="$(asf_ccm_bin)"
  if [[ -z "${bin}" ]]; then
    printf 'error: cloud-provider-kind not on PATH\n' >&2
    printf 'hint: go install sigs.k8s.io/cloud-provider-kind@latest\n' >&2
    return 1
  fi
  run_dir="$(asf_kind_run_dir)"
  pidfile="$(asf_ccm_pidfile)"
  logfile="$(asf_ccm_logfile)"
  owned="$(asf_ccm_owned)"
  mkdir -p "${run_dir}"

  if [[ -f "${pidfile}" ]]; then
    local old_pid
    old_pid="$(tr -d '[:space:]' <"${pidfile}" || true)"
    if asf_ccm_pid_alive "${old_pid}"; then
      printf 'kind-up: cloud-provider-kind already running (pid %s)\n' "${old_pid}"
      return 0
    fi
    rm -f "${pidfile}" "${owned}"
  fi

  if pgrep -f '(^|/)cloud-provider-kind( |$)' >/dev/null 2>&1; then
    printf 'kind-up: cloud-provider-kind already running (external) — not starting another\n'
    return 0
  fi

  export KIND_EXPERIMENTAL_PROVIDER="${KIND_EXPERIMENTAL_PROVIDER:-podman}"
  # shellcheck disable=SC2086
  nohup env KIND_EXPERIMENTAL_PROVIDER="${KIND_EXPERIMENTAL_PROVIDER}" \
    "${bin}" --enable-lb-port-mapping \
    >"${logfile}" 2>&1 &
  echo $! >"${pidfile}"
  touch "${owned}"
  sleep 1
  if ! asf_ccm_pid_alive "$(tr -d '[:space:]' <"${pidfile}")"; then
    printf 'error: cloud-provider-kind failed to start; see %s\n' "${logfile}" >&2
    rm -f "${pidfile}" "${owned}"
    return 1
  fi
  printf 'kind-up: started cloud-provider-kind pid %s (log %s)\n' "$(cat "${pidfile}")" "${logfile}"
}

asf_stop_cloud_provider_kind_if_ours() {
  local pidfile owned pid
  pidfile="$(asf_ccm_pidfile)"
  owned="$(asf_ccm_owned)"
  [[ -f "${owned}" && -f "${pidfile}" ]] || return 0
  pid="$(tr -d '[:space:]' <"${pidfile}" || true)"
  if asf_ccm_pid_alive "${pid}"; then
    printf 'kind-down: stopping demo-owned cloud-provider-kind pid %s\n' "${pid}"
    kill "${pid}" 2>/dev/null || true
    sleep 1
    kill -9 "${pid}" 2>/dev/null || true
  fi
  rm -f "${pidfile}" "${owned}"
}
