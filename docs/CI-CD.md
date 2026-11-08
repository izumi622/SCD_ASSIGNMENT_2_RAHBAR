# RAHBAR CI/CD setup and verification

This is an **implementation guide**, not evidence that a remote workflow already succeeded. The generated code was checked offline, but a kind/GitHub Actions/Docker Hub run is still required.

## Setup in GitHub

1. Create one GitHub repository for the team. Use the local `dev` branch for work and protect `main`; do not push directly to protected main.
2. Create three Docker Hub repositories: `rahbar-api`, `rahbar-indexer`, and `rahbar-ui` (public repositories are easiest for grading).
3. In **GitHub → Settings → Secrets and variables → Actions**, add the repository **variable** `DOCKERHUB_USERNAME` containing only the Docker Hub username; add the repository **secret** `DOCKERHUB_TOKEN` containing a Docker Hub *access token*, not an account password. Do not print or commit the token.
4. In **Settings → Branches → Branch protection** (or the repository Rulesets screen), protect `main`: require a pull request, at least one approving review, required CI status checks, and block direct pushes. Required checks should correspond to the actual CI job names visible after the first run (`lint`, `test`, `manifests`, `build`, `scan`, `e2e-eval`).
5. Push `dev`, open a PR `dev -> main`, wait for the CI workflow, request an approval, then merge. The merge triggers CD, which builds full-SHA Docker Hub images and deploys into a **new ephemeral kind cluster** for the Ingress smoke test.

The workflows declare minimal `permissions: contents: read`. All jobs that **publish** or **deploy** use explicit `needs:`. Neither workflow uses `:latest` for the project images.

## What CI actually tests

The `test` job runs 60%-minimum API package coverage and the indexer/evaluation unit tests. `manifests` runs Kustomize and kubeconform strict validation. `build` builds three images without pushing on PRs. `scan` runs Trivy against all three, failing on fixable HIGH/CRITICAL findings. `e2e-eval` starts kind, runs the **real indexer pipeline** against the three Markdown fixture documents, waits for the API and UI rollouts, and executes `eval/run_eval.py` with the fixture golden set.

**Fixture embedding:** `scripts/fixture_embed_server.py` implements the same local `/api/embed` HTTP response shape, but with deterministic term vectors. It is deployed only through `k8s/ci/fixture-embed.yaml`. The API and indexer both receive `EMBED_MODEL=fixture-bow-768`, so the metadata pin is still exercised. The LLM provider is `stub` on CI: **no real OpenAI/Ollama token or Windows host is needed**. The actual production Ollama model and real-corpus numerical results remain separate.

The `deploy` job pulls Docker Hub images tagged `github.sha`, creates a **fresh kind** cluster, runs the same fixture indexer/evaluation and then installs nginx Ingress and tests both `/` and `/api/ask` using `Host: rahbar.local`.

## Windows CMD commands when the remote is ready

From `D:\5th Semester\SCD\A2\rahbar-starter`:

```cmd
git status --short
git remote -v
git branch --show-current
```

After checking `eval/results.json` and `eval/baseline.json` have the newest **15/15 strict-gate-passed** records, and **only after reviewing the changes**:

```cmd
git add .github k8s scripts eval docs README.md api indexer corpus/MANIFEST.md corpus/sources.yaml

git status --short

git commit -m "Complete RAHBAR RAG evaluation and GitHub CI CD"

git push -u origin dev
```

If `git remote -v` shows nothing, create the GitHub repository first, then `git remote add origin YOUR_ACTUAL_GITHUB_REPO_URL` before pushing. Never use a guessed URL. Do not commit `corpus/raw`, `.env`, passwords, tokens, or `.git` copies of another repository. `git status` must be checked before the final commit.

## Evidence to capture

- GitHub URL, successful **CI workflow** and successful **CD workflow** links (CD must display test → build-push → deploy dependency chain).
- Docker Hub repository links showing tags equal to the same commit SHA.
- Protected `main` rule, PR approval, and a **genuinely failing** CI check preventing a merge; after fixing it, a successful PR.
- Screenshots/logs for `kubectl top pods`, HPA current/target, three API endpoints, model pin mismatch producing unready pods, real Job indexing once, Chroma storage, a rolling update and a rollback.
- The real evaluation `eval/results.json` and `eval/baseline.json` committed and visible in GitHub.

**Important:** If the first CI/CD run fails, inspect the failing job log and fix the specific issue. The existence of YAML files is not evidence of a successful remote deployment. A local kind fixture run also does not prove that the hosted GitHub runner or its Ingress route worked.
