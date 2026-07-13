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
   bumps the image tag in `overlays/dev/kustomization.yaml` to the new
   `<VERSION>`, and pushes the change. ArgoCD watches that repo and syncs the
   dev environment automatically. Promoting to prod is a separate, deliberate
   step done in the GitOps repo (see its README).

## Releasing a new version

1. Make the code change and commit it (open a PR against `main` if you want
   tests to gate it before merge).
2. Bump the version in [`VERSION`](VERSION) (e.g. `1.0` → `1.1`) — this is
   what produces a new image tag. Without it, `build-and-push` just
   re-pushes the same tag and `update-gitops` becomes a no-op commit.
3. Merge to `main`. CI runs `test` → `build-and-push` → `update-gitops` (see
   [CI/CD](#cicd) above), pushing the new image and bumping the dev tag in
   the GitOps repo.
4. ArgoCD picks up the change and syncs `myapp-dev` automatically — no
   manual `kubectl apply` needed.
5. Verify the rollout in dev (`kubectl get pods -n myapp-dev`, confirm the
   image tag, hit the app, or check ArgoCD's sync status) before trusting
   the release.
6. Promote to prod as a separate, deliberate step: open a PR in the
   [GitOps repo](https://github.com/rftecpro-ai/python-webapp-ci-template-gitops)
   bumping `overlays/prod/kustomization.yaml`'s tag to the verified version.
   See that repo's README for details.

### Required repository secrets

These jobs need secrets set in the GitHub repo
(**Settings → Secrets and variables → Actions**):

| Secret | Used by | Value |
|---|---|---|
| `DOCKERHUB_USERNAME` | build-and-push | Your Docker Hub username (`ffribeiro`) |
| `DOCKERHUB_TOKEN` | build-and-push | A Docker Hub [access token](https://hub.docker.com/settings/security) (not your password) |
| `GITOPS_PAT` | update-gitops | A GitHub PAT with `repo` write access to `rftecpro-ai/python-webapp-ci-template-gitops` (the default `GITHUB_TOKEN` can't write to a different repo) |

I can't create these secrets for you — add them manually before merging to
`main`, otherwise the corresponding job will fail.
