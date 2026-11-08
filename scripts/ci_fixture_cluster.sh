#!/usr/bin/env bash
# Run on Linux GitHub Actions runner with an existing kind cluster and three local images.
# Arguments: API_IMAGE UI_IMAGE INDEXER_IMAGE [--ingress]
# Applies an isolated fixture configuration; does not touch Minikube on Windows.
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo 'Usage: scripts/ci_fixture_cluster.sh API_IMAGE UI_IMAGE INDEXER_IMAGE [--ingress]' >&2
  exit 2
fi
API_IMAGE="$1"
UI_IMAGE="$2"
INDEXER_IMAGE="$3"
INGRESS="${4:-}"

cleanup() {
  if [[ -n "${FORWARD_PID:-}" ]]; then kill "$FORWARD_PID" 2>/dev/null || true; fi
  if [[ -n "${INGRESS_PID:-}" ]]; then kill "$INGRESS_PID" 2>/dev/null || true; fi
}
show_diagnostics() {
  echo '== Debug: workloads =='; kubectl -n rahbar get pods,jobs,deployments -o wide || true
  echo '== Debug: indexer =='; kubectl -n rahbar logs job/indexer-fixture --all-containers=true --tail=100 || true
  echo '== Debug: API =='; kubectl -n rahbar logs deployment/api --tail=100 || true
}
trap cleanup EXIT
trap show_diagnostics ERR

# kind loads the exact local or pulled images before creating the workloads.
for img in "$API_IMAGE" "$UI_IMAGE" "$INDEXER_IMAGE"; do
  kind load docker-image "$img" --name "${KIND_CLUSTER:-kind}"
done

python scripts/render_ci_manifests.py --api-image "$API_IMAGE" --ui-image "$UI_IMAGE" \
  --indexer-image "$INDEXER_IMAGE" --out /tmp/rahbar-ci-manifests.yaml
kubectl apply -f /tmp/rahbar-ci-manifests.yaml

kubectl -n rahbar create configmap fixture-embed-code \
  --from-file=server.py=scripts/fixture_embed_server.py \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n rahbar create configmap fixture-corpus \
  --from-file=eval/fixtures/academic-rules-2023.md \
  --from-file=eval/fixtures/academic-rules-2026.md \
  --from-file=eval/fixtures/fees-2026.md \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f k8s/ci/fixture-embed.yaml
kubectl -n rahbar rollout status deployment/fixture-embed --timeout=180s

python scripts/render_fixture_job.py --image "$INDEXER_IMAGE" --out /tmp/rahbar-fixture-job.yaml
kubectl apply -f /tmp/rahbar-fixture-job.yaml
kubectl -n rahbar wait --for=condition=complete job/indexer-fixture --timeout=420s
kubectl -n rahbar rollout status deployment/api --timeout=240s
kubectl -n rahbar rollout status deployment/ui --timeout=180s

kubectl -n rahbar port-forward service/api 18000:8000 >/tmp/rahbar-api-pf.log 2>&1 &
FORWARD_PID=$!
for i in $(seq 1 45); do
  if curl -fsS --max-time 5 http://127.0.0.1:18000/readyz > /tmp/rahbar-ready.json; then break; fi
  sleep 2
done
cat /tmp/rahbar-ready.json
python eval/run_eval.py --api http://127.0.0.1:18000 \
  --golden eval/fixtures/golden.fixture.yaml \
  --baseline eval/fixtures/nonexistent-baseline-ci.json \
  --out /tmp/rahbar-fixture-results.json

if [[ "$INGRESS" == '--ingress' ]]; then
  # The nginx admission webhook, ingressClass and controller are created here.
  kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.14.2/deploy/static/provider/kind/deploy.yaml
  kubectl -n ingress-nginx wait --for=condition=Ready pods \
    -l app.kubernetes.io/component=controller --timeout=360s
  kubectl -n ingress-nginx port-forward service/ingress-nginx-controller 18080:80 >/tmp/rahbar-ingress-pf.log 2>&1 &
  INGRESS_PID=$!
  for i in $(seq 1 60); do
    if curl -fsS --max-time 5 -H 'Host: rahbar.local' http://127.0.0.1:18080/ > /tmp/rahbar-ui.html; then break; fi
    sleep 2
  done
  grep -qiE 'rahbar|doctype|html' /tmp/rahbar-ui.html
  curl -fsS --max-time 15 -H 'Host: rahbar.local' -H 'Content-Type: application/json' \
    -d '{"question":"When is a student placed on academic warning?"}' \
    http://127.0.0.1:18080/api/ask | python -c 'import json,sys; d=json.load(sys.stdin);assert d.get("answered_from_context") is True; assert d.get("citations")'
  echo 'Ingress UI and /api/ask smoke tests passed'
fi

echo 'Fixture-backed indexing, retrieval, generation and evaluation passed.'
