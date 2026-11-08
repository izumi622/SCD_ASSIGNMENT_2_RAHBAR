# Phase 1 — Stub stack bootstrap (NOT a complete assignment)

This overlay adds three Dockerfiles, the Kubernetes deployment and API readiness.
It intentionally still uses the teacher-provided **stub retriever and stub provider**.
The Job writes three fake chunks; the UI's answers are **not real university answers**.

## Windows CMD commands from repository root

```cmd
cd /d "D:\5th Semester\SCD\A2\rahbar-starter"
docker build -t rahbar-api:dev api
docker build -t rahbar-indexer:dev indexer
docker build -t rahbar-ui:dev ui
minikube image load rahbar-api:dev
minikube image load rahbar-indexer:dev
minikube image load rahbar-ui:dev
minikube kubectl -- apply -k k8s/overlays/dev
minikube kubectl -- get pods,jobs,pvc -n rahbar
minikube kubectl -- wait --for=condition=complete job/indexer-initial -n rahbar --timeout=300s
minikube kubectl -- rollout status deployment/api -n rahbar --timeout=300s
minikube kubectl -- rollout status deployment/ui -n rahbar --timeout=300s
minikube kubectl -- get endpoints -n rahbar
minikube kubectl -- get hpa -n rahbar
```

To use Ingress on Windows, open a separate **administrator** CMD and keep this running:
`minikube tunnel`. Use an independent CMD to test:

```cmd
curl.exe -H "Host: rahbar.local" http://127.0.0.1/
curl.exe -X POST http://127.0.0.1/api/ask -H "Host: rahbar.local" -H "Content-Type: application/json" -d "{\"question\":\"What is the attendance policy?\"}"
```

If the tunnel doesn't expose Ingress, use a fallback port-forward in a CMD window:
`minikube kubectl -- port-forward svc/ui 8080:8080 -n rahbar`, then inspect http://localhost:8080/.
For API, `minikube kubectl -- port-forward svc/api 8000:8000 -n rahbar` and query
http://localhost:8000/healthz . Port-forward bypasses Ingress and cannot prove it works.

## Debug

```cmd
minikube kubectl -- get pods -n rahbar -o wide
minikube kubectl -- describe pod -n rahbar <POD-NAME>
minikube kubectl -- logs -n rahbar job/indexer-initial
minikube kubectl -- logs -n rahbar deployment/api
minikube kubectl -- get networkpolicy -n rahbar
```

## Important requirements still outstanding

- Real PDF/OCR extraction and version-aware Chroma retrieval; LLM generation.
- Redis semantic cache, grounded abstention and citation validation.
- Golden evaluation set, measured chunking/cache thresholds, CI and CD.
- Registry SHA tags, pull requests, branch protection, evidence and 3 other ADRs.
- Tests and README; CPU/memory requests need measured justification.
- Review of NetworkPolicy and security against real integration tests.

Disclose any AI-assisted files in `docs/AI-USAGE.md` and understand your implementation.
