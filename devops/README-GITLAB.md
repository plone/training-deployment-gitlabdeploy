# DevOps pipelines in GitLab CI/CD 🚀

This project is built, tested and deployed entirely by GitLab CI/CD.
GitHub Actions are not used.

## Pipeline overview 🧭

The pipeline lives in [`.gitlab-ci.yml`](../.gitlab-ci.yml) with the job definitions split into
[`.gitlab/ci/`](../.gitlab/ci/).

| Stage | Jobs | Runs on |
| --- | --- | --- |
| `.pre` | `config` | every pipeline |
| `check` | `backend:lint`, `frontend:lint`, `frontend:i18n`, `changelog:*` | merge requests, branches, `main`, tags |
| `test` | `backend:test`, `frontend:test` | merge requests, branches, `main`, tags |
| `build` | `build:backend`, `build:frontend` | `main` and tags only |
| `deploy` | `deploy:production` | `main` and tags only |

`config` resolves everything once so no other job re-derives it: versions from
`uvx repoplone settings dump`, the registry, the image tag, and the `[deployment]` settings below.

It publishes them as **two** artifacts, and the split is deliberate:

| Artifact | Holds | Why |
| --- | --- | --- |
| `build.env` (dotenv report) | Build arguments and `DEPLOY_URL` | Values that must be real CI/CD variables. `environment:url` is resolved by GitLab, not by a shell |
| `deploy.env` (ordinary artifact) | Everything the stack file interpolates | GitLab caps a **dotenv report at 20 variables** and rejects a larger one with an opaque `400`. An ordinary artifact has no such limit |

The deploy job sources the second with `set -a && . ./deploy.env && set +a`. Values are written with
`shlex.quote`, since several contain spaces. A guard in `config` fails the job with a clear message
if the dotenv report ever exceeds 20 again.

## Deployment settings ⚙️

Everything host-specific lives in the `[deployment]` section of
[`repository.toml`](../repository.toml) — not in the stack file, the Makefile or the pipeline.

```toml
[deployment]
gitlab_project = "plone-training1/training-deployment-gitlabdeploy"
hostname      = "playcluster.plone.org"
stack_name    = "playcluster-plone-org"
stack_prefix  = "reference"
stack_file    = "devops/stacks/stack.yml"
data_path     = "/srv/playcluster-demo/data"
db_placement  = "node.labels.storage == persistent"
app_placement = "node.labels.type == worker"

[deployment.local]
hostname = "playcluster-demo.localhost"

[deployment.traefik]
network = "nw-public"
constraint_label = "public"
entrypoint = "https"
certresolver = "le"
```

| Key | Used for |
| --- | --- |
| `hostname` | Traefik router rules, `RAZZLE_API_PATH`, the VHM rewrites, and `DEPLOY_URL` |
| `stack_name` | The swarm stack, and the `${STACK_NAME}_nw-internal` network name |
| `stack_prefix` | Namespaces Traefik router, service and middleware names, which are **global** to the Traefik instance. Without it a second project defining `rt-frontend` would collide silently |
| `db_placement` | Pins the database to the node holding `data_path`. Required — the deploy refuses to run without it |
| `app_placement` | Keeps the stateless services on the intended nodes. Optional; its default matches any Linux node |
| `[deployment.traefik]` | Must match the cluster's Traefik. Get one wrong and the service is simply not routed, usually with no error |

> `repoplone` parses `repository.toml` but **ignores unknown sections** — it does not error, and it
> does not expose them either. So `repoplone settings dump` will not show `[deployment]`. The
> `config` job and the root `Makefile` read it directly with `tomllib`.

`make debug-settings` prints the resolved values.

### Image tags 🏷️

Every build publishes an **immutable** tag, and `main` additionally moves `latest`:

| Pipeline | Tags pushed |
| --- | --- |
| push to `main` | `sha-<short-sha>` and `latest` |
| git tag `1.0.0a1` | `1.0.0a1` |

### Choosing a registry 📦

The pipeline supports two registries. A single CI/CD variable, `REGISTRY_IMAGE_PREFIX`, picks
between them; the `config` job resolves it and publishes `REGISTRY_IMAGE_PREFIX` and
`REGISTRY_HOST` to every other job.

#### Mode A — GitLab Container Registry (default)

Leave `REGISTRY_IMAGE_PREFIX` **unset**. The pipeline uses `$CI_REGISTRY_IMAGE`
(`<registry-host>/<project-path>`, supplied by GitLab), pushes with GitLab's built-in per-job
credentials, and pulls with a deploy token.

| Credential | Source |
| --- | --- |
| Push | `$CI_REGISTRY_USER` / `$CI_REGISTRY_PASSWORD` — automatic, nothing to configure |
| Pull | `$CI_DEPLOY_USER` / `$CI_DEPLOY_PASSWORD` — requires a deploy token named exactly `gitlab-deploy-token` |

> **This mode requires the registry to be enabled**, both on the instance (`registry_external_url`
> in `/etc/gitlab/gitlab.rb`, then `gitlab-ctl reconfigure`) and on the project (Settings → General →
> Visibility → Container registry). On GitLab.com it is always enabled — which has a catch: if
> `REGISTRY_IMAGE_PREFIX` is missing from a pipeline, for instance because it was marked
> *Protected* and the pipeline runs on an unprotected branch, the `config` job does not fail. It
> quietly falls back to Mode A, builds push to GitLab.com's registry, and the deploy looks for the
> images in the self-hosted one. This project uses Mode B.

#### Mode B — self-hosted registry

Set these CI/CD variables. Protect the credentials, but **not** `REGISTRY_IMAGE_PREFIX` — the
`config` job needs it on every pipeline, merge requests included. Mask the passwords; the user
names are too short to mask. The cluster documentation, chapter 6, has the full table.

| Variable | Example / purpose |
| --- | --- |
| `REGISTRY_IMAGE_PREFIX` | `registry.playcluster.plone.org/$CI_PROJECT_PATH` |
| `REGISTRY_USER` / `REGISTRY_PASSWORD` | Push account, used by the build jobs |
| `REGISTRY_PULL_USER` / `REGISTRY_PULL_PASSWORD` | **Read-only** account, handed to the swarm |

The registry host is derived from the prefix (everything before the first `/`, port included), so
there is no separate host variable to keep in sync.

**The pull account must be read-only and must not expire.** The deploy runs
`docker stack deploy --with-registry-auth`, which copies those credentials onto every swarm node,
where they persist so nodes can re-pull after a reboot or reschedule.

#### In both modes

Images are `<prefix>/backend` and `<prefix>/frontend`, with the BuildKit layer cache at
`<prefix>/backend/cache` and `<prefix>/frontend/cache`.

The deploy job passes the resolved prefix to the stack file as `REGISTRY_IMAGE_PREFIX`, which is why
[`stacks/stack.yml`](stacks/stack.yml)
hardcodes no registry. `container_images_prefix` in `repository.toml` should match whichever mode is
active — it is what `make build-image` uses when building locally.

### Deployment 🚢

`deploy:production` uses [kitconcept/docker-stack-deploy](https://github.com/kitconcept/docker-stack-deploy)
as its job image. That image sets `DOCKER_HOST=ssh://…` and runs `docker stack deploy` against the
remote swarm over SSH, so the job needs **no** Docker-in-Docker and **no** mounted Docker socket.

The image tag to deploy is passed as `STACK_PARAM`, which the stack file interpolates
(`image: …/backend:${STACK_PARAM:-latest}`).

## Repository setup 🛠️

See [Get started with GitLab CI/CD](https://docs.gitlab.com/ci/).

### Step 1: Runners

The pipeline selects runners by tag, using two variables with these defaults:

| Variable | Default | Requirement |
| --- | --- | --- |
| `RUNNER_TAG_BUILD` | `docker` | Docker executor with the host's docker socket mounted into job containers |
| `RUNNER_TAG_DEPLOY` | `deploy` | Only needs to reach `DEPLOY_HOST` on port 22 |

Either tag your runners `docker` and `deploy`, or override the two variables under
`Settings` → `CI/CD` → `Variables`.

Two things to check on the build runner, both of which fail confusingly rather than clearly:

1.  **The host's docker socket must be mounted into job containers** — for example, a
    `/var/run/docker.sock:/var/run/docker.sock` entry in `docker_volumes`. The build jobs deliberately
    do *not* start a `docker:dind` service, because a mounted socket makes dind unable to bind
    `/var/run/docker.sock` and it dies after a 30-second health-check timeout while the build
    proceeds against the host daemon regardless.

    The trade-off is that builds are not isolated from the host daemon: a job can control every
    container on that machine. On a runner host that also runs the registry, that is worth a
    deliberate decision. To go the other way, remove the socket mount from the runner and restore
    `services: [docker:dind]` plus `DOCKER_TLS_CERTDIR` in `.gitlab/ci/templates.yml` — dind then
    needs `privileged = true`, which `riemers.gitlab-runner` ships as `docker_privileged: false`.

2.  **If the runner shares a host with a self-hosted registry** (Mode B), the push may leave the
    host and have to come back through NAT. Many setups do not hairpin, and the push simply hangs.
    Since there is no dind service, the push comes from the buildx builder running on the host's own
    daemon — so mapping the registry name to the host's own address in `[runners.docker]` fixes it.
    `extra_hosts` also reaches any service container, because GitLab Runner gives services "the same
    DNS servers, search domains, and additional hosts as the CI container":

    ```toml
    extra_hosts = ["registry.example.com:10.0.0.4"]
    ```

    With `riemers.gitlab-runner`, which has no dedicated variable for this, use its generic
    passthrough:

    ```yaml
    gitlab_runner:
      extra_configs:
        runners.docker:
          extra_hosts: ["registry.example.com:10.0.0.4"]
    ```

    Test before working around it — if the host holds its public IP directly rather than sitting
    behind NAT, there is nothing to fix.

### Step 2: Registry credentials

Pick a mode from [Choosing a registry](#choosing-a-registry-) first.

**Mode B (self-hosted):** set the four `REGISTRY_*` variables described there and skip the rest of
this step — the registry's own accounts do the job.

**Mode A (GitLab registry):** pushing needs no configuration, but the swarm's long-lived pull does.
The deploy passes `--with-registry-auth`, which forwards registry credentials to the swarm nodes so
they can pull images later — after a reboot, or when a task is rescheduled.
**Do not use the pipeline's own `$CI_JOB_TOKEN` for this**: it expires when the pipeline ends.

1.  Go to `Settings` → `Repository` → `Deploy tokens`.
2.  Create a token named **exactly `gitlab-deploy-token`**, with the scope `read_registry`.

    The name matters: GitLab only exposes a deploy token to CI/CD jobs as `CI_DEPLOY_USER` /
    `CI_DEPLOY_PASSWORD` when it carries that exact name. The deploy job reads those two variables,
    so there is nothing further to configure — but with any other name they are empty and the
    deploy fails to log in.

3.  Give it a long expiry, or none. These credentials end up on the swarm nodes and are what they
    use to pull images later; when they expire, a node reboot months from now can no longer start
    the stack.

Pushing images during the `build` stage uses the built-in `$CI_REGISTRY_USER` /
`$CI_REGISTRY_PASSWORD`, so no extra configuration is needed there.

If neither the `REGISTRY_PULL_*` pair nor a correctly-named deploy token is present, the deploy job
stops with an explicit message rather than failing later inside the registry login.

### Step 3: Add the deployment variables

1.  Go to `Settings` → `CI/CD` and expand `Variables`.
2.  Add each variable below. Mark them **Masked**, and — since deploys only run from `main` and from
    tags — also **Protected**, with `main` and your tags configured as protected refs under
    `Settings` → `Repository` → `Protected branches` / `Protected tags`.

| Variable | Value |
| --- | --- |
| `DEPLOY_HOST` | Hostname of the Docker Swarm manager |
| `DEPLOY_USER` | SSH user on that host, member of the `docker` group |
| `DEPLOY_SSH_PRIVATE_KEY` | Private SSH key (see the next step) |

The registry credentials are **not** in this list. In Mode B they are the four `REGISTRY_*`
variables from [Choosing a registry](#choosing-a-registry-); in Mode A they come from the
`gitlab-deploy-token` deploy token automatically.

No `SSH_KNOWN_HOSTS` variable is needed: `docker-stack-deploy` runs `ssh-keyscan` against
`DEPLOY_HOST` itself.

### Step 4: Add an SSH deployment key

1.  Create a key for GitLab CI/CD to connect to the host:

    ```shell
    ssh-keygen -t ed25519 -C "gitlab-ci@playcluster-demo" -f ./deploy_key
    ```

2.  Append `deploy_key.pub` to `~/.ssh/authorized_keys` of `DEPLOY_USER` on `DEPLOY_HOST`.
3.  Store the contents of `deploy_key` as the `DEPLOY_SSH_PRIVATE_KEY` variable.
4.  Delete your local copy of the private key.

See [Use SSH keys to communicate with GitLab](https://docs.gitlab.com/user/ssh/).

### Step 5: Prepare the host

On the playcluster these are provisioned by the
[training-deployment-playcluster](https://github.com/plone/training-deployment-playcluster) Ansible
repository, except the data directory, which is per project and created by hand — see chapter 6 of
the documentation. The list below is what this stack needs to exist, however it got there.

> **This stack ships no Traefik of its own.** The cluster already runs one holding ports 80 and 443,
> and only one service can. Deploying a second fails with
> `port '80' is already in use by service 'traefik_traefik'`. Routing here is labels only.

1.  Docker installed, and the node initialized as a swarm manager: `docker swarm init`.
2.  The overlay network the cluster's Traefik uses — `deployment.traefik.network` in
    `repository.toml`. This stack attaches to it as an **external** network and does not create it:

    ```shell
    docker network create --driver overlay --attachable nw-public
    ```

3.  **Pin the database to one node.** `vol-site-data` is a bind mount to a path on a single host.
    If Swarm reschedules the task elsewhere, that path resolves to a different — empty — directory
    and the site comes up with a blank database. Create the directory on the node that will hold it,
    then label that node to match `deployment.db_placement`:

    ```shell
    sudo mkdir -p /srv/playcluster-demo/data
    ```

    ```shell
    docker node update --label-add storage=persistent <node>
    ```

    Until the label exists the `db` task stays pending with "no suitable node", which is at least a
    loud failure rather than a silent data loss.

4.  DNS for the hostname in `repository.toml` `[deployment]` pointing at the cluster, with ports 80
    and 443 reachable — the cluster's Traefik obtains the Let's Encrypt certificate.
5.  Every swarm node must be able to reach the registry and trust its certificate — here,
    `registry.playcluster.plone.org`, whose certificate is from Let's Encrypt, so nothing needs
    distributing. If the registry is ever placed behind a proxy that caps request bodies
    (Cloudflare's defaults to 100 MB), pushing the frontend image's larger layers fails with a
    `413`; keep that hostname off such a proxy.

## Deploying 🚀

Deployment is automatic:

- Every push to `main` deploys `sha-<short-sha>`.
- Every git tag deploys that tag.

Deploys are serialized by `resource_group: production`, so two pipelines never touch the stack at
the same time. Progress is visible under `Deploy` → `Environments`.

### First deploy only

Create the Plone site once, after the stack is up:

```shell
docker exec $(docker ps -qf name=_backend | head -1) ./docker-entrypoint.sh create-site
```

### Rolling back ⏮️

Because every build is published under an immutable `sha-…` or version tag, a rollback is just a
redeploy of an older tag. Two ways:

- Go to `Deploy` → `Environments` → `production` and use `Re-deploy` on an earlier deployment.
- Or run a new pipeline on `main` (`Build` → `Pipelines` → `Run pipeline`) with a variable:

  | Key | Value |
  | --- | --- |
  | `IMAGE_TAG` | `sha-abc1234` — the tag you want to go back to |

  Manual pipeline variables take precedence over the ones `config` computes, so the deploy uses the
  tag you gave it.

### Manual deploys

To require a click instead of deploying on every push to `main`, add `when: manual` to the
`main` rule of `deploy:production` in [`.gitlab/ci/deploy.yml`](../.gitlab/ci/deploy.yml):

```yaml
rules:
  - if: $CI_COMMIT_TAG
  - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
    when: manual
```

## Validating pipeline changes ✅

Validate locally before pushing — this resolves `extends`, `include` and `!reference` the way GitLab
does, and checks the result against GitLab's CI JSON schema:

```shell
npx --yes gitlab-ci-local@latest --list
```

It also prints the resolved job list, so you can confirm which jobs a given branch or tag would
actually create.

Alternatively use the pipeline editor (`Build` → `Pipeline editor` → `Validate`), or `glab ci lint`
if you have `glab` set up against this instance.

> **A YAML trap worth knowing.** A `script` entry is a *plain* scalar, so a `: ` (colon followed by
> a space) anywhere in it silently turns the entry into a mapping, and GitLab rejects the job with
> "script config should be a string or a nested array of strings". The file still parses as valid
> YAML, so a plain syntax check will not catch it. Either avoid `: ` in script lines or wrap the
> whole entry in single quotes.

The stack file can be checked the same way, without a Docker daemon:

```shell
docker compose -f devops/stacks/stack.yml config
```

It interpolates every `${VAR}` and shows the result, so the required-variable guards fire here
rather than half-way through a deploy.

## Further reading 📚

- The **documentation** in [`docs/`](../docs/) — the same material at more length, with the
  reasoning behind the awkward parts
- [training-deployment-playcluster](https://github.com/plone/training-deployment-playcluster) — the cluster this deploys onto, and its documentation
