# feat(phase-8): the image, package and chart published when a release is cut, a Helm chart that runs each run as a Kubernetes Job on kind, and weekly upkeep of what it depends on [slice 05]

**Issue:** #140 · **Spec:** PLAN.md#4c-phase-8-the-product · **Plan:** plans/phase-8/05-package.md
**Depends on:** 03-api (slice 03 of this batch)
**Labels:** phase-8
**Needs:** Docker Desktop with its engine running (`docker info` answers); kind and helm, which this slice installs with winget.

## Deliverable

deploy/Dockerfile (python 3.13 slim, Pango from Debian for WeasyPrint, the package, app/ and web/ copied by a whitelist in deploy/Dockerfile.dockerignore so a web/ folder that is not there yet does not break the build), started as `docker run -p 8000:8000 -v <runs>:/app/runs ghcr.io/muhanad-husn/diligence-reader`. .github/workflows/image.yml builds the image on a pull request only when it changes deploy/, pyproject.toml or app/, and publishes nothing on a merge. .github/workflows/release.yml runs when the founder cuts a release tag such as v0.8.1, and publishes that one version three ways: the image to ghcr.io as the version and `latest`, for amd64 and for arm64 on GitHub's ARM runners; the package to PyPI by trusted publishing, which `pipx install diligence-reader` needs; and the chart to ghcr.io as an OCI artefact. The image is built for speed: layers in the order they change (system libraries, then Python packages from pyproject.toml alone, then the code), the base image pinned by digest, packages installed with uv, and the GitHub Actions layer cache kept between runs. The pull request prints the cold and the cached build times, and a code-only rebuild is expected under a minute. A Helm chart deploy/helm/diligence-reader: the API as a Deployment and Service, a volume for runs, a ServiceAccount and Role allowed to create, read and delete Jobs. app/runner_k8s.py, the KubernetesRunner chosen by `RLM_RUNNER=kubernetes`: one Job per run, created, watched and deleted through the Kubernetes API with httpx and the pod's service account token; the Job fetches the key once from the API pod by a one-time run token over the cluster network, and the API forgets the key after handing it over.

**Upkeep, added at the founder's request.** `.github/dependabot.yml` opens weekly grouped updates for pip, docker (the base image in deploy/), github-actions and the Helm chart where Dependabot reads it. The exact pins in pyproject.toml stay, and a Dependabot pull request is merged by the founder like any other. There is no npm entry: web/ has no package.json, and its one vendored file is updated by hand. `.github/workflows/weekly.yml` runs on a weekly schedule, and on a pull request that changes it, with four jobs, none needing a key or spending a dollar: the model check, `python -m rlm.modelcheck`, which reads OpenRouter's free /api/v1/models list through `Gateway.models()` with no key and fails when a task module's DEFAULT_MODEL is gone or its price differs from PRICES in src/rlm/gateway.py, since a wrong price breaks the estimate the user confirms; `pytest -q` with DeprecationWarning as an error; a Trivy scan of the image, failing on a fixable high or critical finding; and the chart installed on kind, waiting for the API to roll out, which catches a retired Kubernetes API.

A limit to state: runs/ is never committed, so in CI the phase tests that read pinned artefacts skip. A dependency update is checked there by the tests that need no artefact, the image build and the weekly jobs; the pinned-artefact suite runs only on the founder's machine.

## Mechanism

Docker, GitHub Actions' docker/build-push-action, Helm. The Kubernetes calls are three requests (create, read status, delete) through httpx, which the gateway already uses, so the `kubernetes` client package is not added.

Survey: no skill or MCP applies; library is Docker and Helm (industry standard); no model call.

## Acceptance criterion

Given Docker Desktop, when the image is built and run, then tests/test_phase8_api.py passes against the container on sample 3; given kind and helm (installed with winget by this slice), when the chart is installed and a run on sample 3 is started through the API, then it runs as one Kubernetes Job, the report grades recall 100, the Job is deleted after the run, and `kubectl get` of every Secret, ConfigMap, Job and Pod as YAML does not contain the key; the workflow builds the image on the pull request, and a second build after a code-only change reuses every layer but the last; release.yml is run once as a dry run with publishing switched off. The weekly workflow goes green on the pull request; `python -m rlm.modelcheck` fails on a fixture models list with one default model removed and on one with a changed price, and passes on the live list. The gate checks the weekly workflow green on main.

## Files

```aeo-independence
slice: 05-package
creates: deploy/Dockerfile
creates: deploy/Dockerfile.dockerignore
creates: deploy/helm/diligence-reader
creates: .github/workflows/image.yml
creates: .github/workflows/release.yml
creates: app/runner_k8s.py
creates: tests/test_phase8_package.py
creates: .github/dependabot.yml
creates: .github/workflows/weekly.yml
creates: src/rlm/modelcheck.py
creates: tests/test_phase8_modelcheck.py
depends-on: 03-api
```

## Out of scope

A managed cluster; any paid hosting; image signing; a multi-node storage class beyond a chart value; automatic merging of Dependabot pull requests.
