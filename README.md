# python-webapp-ci-template

A minimal Flask "Hello World" web app, containerized with Docker, built/pushed
to Docker Hub, and deployed to Kubernetes via GitOps, all through a GitHub
Actions CI pipeline.

Kubernetes manifests and ArgoCD `Application` resources live in a separate
repo: [python-webapp-ci-template-gitops](https://github.com/rftecpro-ai/python-webapp-ci-template-gitops).

## Folder structure

```
.
├── .github/workflows/ci.yml   # CI pipeline: test, build & push, then update GitOps repo
├── app.py                     # Flask app entrypoint
├── conftest.py                # pytest fixtures/config
├── Dockerfile                 # container build
├── requirements.txt           # runtime dependencies
├── requirements-dev.txt       # dev/test dependencies
├── tests/
│   └── test_app.py            # app tests
└── VERSION                    # image tag for the current release
```

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

python app.py          # runs on http://localhost:8000
pytest                 # run tests
```

## Docker

```bash
docker build -t ffribeiro/python-webapp-ci-template:local .
docker run -p 8000:8000 ffribeiro/python-webapp-ci-template:local
```

## CI/CD

`.github/workflows/ci.yml` runs on every push/PR to `main`:

1. **test** — installs dependencies and runs `pytest`.
2. **build-and-push** — on push to `main` only (after tests pass), builds a
   multi-arch (`linux/amd64`, `linux/arm64`) image and pushes it to Docker Hub
   as `ffribeiro/python-webapp-ci-template:<VERSION>`.
3. **update-gitops** — checks out
   [python-webapp-ci-template-gitops](https://github.com/rftecpro-ai/python-webapp-ci-template-gitops),
   bumps the image tag in `dev/deployment.yaml` to the new
   `<VERSION>`, and pushes the change. ArgoCD watches that repo and syncs the
   dev environment automatically. Promoting to prod is a separate, deliberate
   step done in the GitOps repo (see its README).

## Releasing a new version

1. When an app update is required, create a branch off `main` named
   `release/<newtag>` (e.g. `release/1.1`) — the branch name should match
   the version you're about to ship.
2. Make the code change on that branch and commit it.
3. Bump the version in [`VERSION`](VERSION) to match the branch (e.g.
   `1.0` → `1.1`) — this is what produces a new image tag. Without it,
   `build-and-push` just re-pushes the same tag and `update-gitops`
   becomes a no-op commit.
4. Open a PR from `release/<newtag>` against `main` so tests gate it
   before merge.
5. Merge to `main`. CI runs `test` → `build-and-push` → `update-gitops`
   (see [CI/CD](#cicd) above), pushing the new image and bumping the dev
   tag in the GitOps repo.
6. ArgoCD picks up the change and syncs `myapp` automatically — no
   manual `kubectl apply` needed.
7. Verify the rollout in dev (`kubectl get pods -n myapp`, confirm the
   image tag, hit the app, or check ArgoCD's sync status) before trusting
   the release.
8. Promote to prod as a separate, deliberate step: open a PR in the
   [GitOps repo](https://github.com/rftecpro-ai/python-webapp-ci-template-gitops)
   bumping `prod/deployment.yaml`'s tag to the verified version.
   See that repo's README for details.

### Required repository secrets

These jobs need secrets set in the GitHub repo
(**Settings → Secrets and variables → Actions**):

| Secret | Used by | Value |
|---|---|---|
| `DOCKERHUB_USERNAME` | build-and-push | Your Docker Hub username |
| `DOCKERHUB_TOKEN` | build-and-push | A Docker Hub [access token](https://hub.docker.com/settings/security) (not your password) |
| `GITOPS_PAT` | update-gitops | A GitHub PAT with `repo` write access to `rftecpro-ai/python-webapp-ci-template-gitops` (the default `GITHUB_TOKEN` can't write to a different repo) |

#### Creating and adding `GITOPS_PAT`

Two parts: create the PAT, then add it as a secret.

**1. Create the PAT** (use an account with write access to the GitOps repo):

- Go to GitHub → **Settings → Developer settings → Personal access tokens**.
- **Fine-grained token (recommended):** scope it to `rftecpro-ai/python-webapp-ci-template-gitops` only, with **Contents: Read and write** permission (add **Pull requests: Read and write** too if the workflow opens PRs). If the org has fine-grained PAT approval enabled, an org admin will need to approve it.
- **Classic token (simpler if the org restricts fine-grained tokens):** scope `repo` (full control of private repos, or just `public_repo` if it's public).
- Set an expiration and copy the token value once — it won't be shown again.

**2. Add it as a repo secret:**

- Go to `rftecpro-ai/python-webapp-ci-template` → **Settings → Secrets and variables → Actions → Repository secrets**.
- Click **New repository secret**.
- Name: `GITOPS_PAT`
- Value: paste the token.
- Save.

The workflow then references it as `${{ secrets.GITOPS_PAT }}` when checking out and pushing to the GitOps repo.

> **Note:** a PAT tied to a personal account means the token dies if that person leaves or rotates credentials, and audit logs show the action as that person rather than the automation. If this pattern recurs across repos, consider a GitHub App or bot/service account instead — cleaner for OSFI-aligned access management and offboarding.

These secrets require access we don't have (your Docker Hub credentials, your
GitHub account) — someone with the right permissions needs to create them
manually before merging to `main`, or the corresponding job will fail.
