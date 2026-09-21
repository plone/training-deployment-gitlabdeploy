# training-deployment-gitlabdeploy

[![Built with Cookieplone](https://img.shields.io/badge/built%20with-Cookieplone-0083be.svg?logo=cookiecutter)](https://github.com/plone/cookieplone-templates/)
[![Black code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![pipeline status](https://gitlab.com/plone-training1/training-deployment-gitlabdeploy/badges/main/pipeline.svg)](https://gitlab.com/plone-training1/training-deployment-gitlabdeploy/-/commits/main)

A Plone 6 project that builds, publishes and deploys itself with GitLab CI/CD: lint and test, container
images into a private registry, and a Docker Swarm stack onto the playcluster. It is the reference
deployment of the Plone deployment training, served at <https://playcluster.plone.org>.

- **Documentation:** [`docs/`](docs/) — six chapters, from the project and its images to operating the
  deploy. Build them with `make html` or `make pdf` in `docs/`.
- **The cluster** it deploys onto is built by
  [training-deployment-playcluster](https://github.com/plone/training-deployment-playcluster).
- The pipeline runs here on GitLab.com. The repository is mirrored to
  [github.com/plone/training-deployment-gitlabdeploy](https://github.com/plone/training-deployment-gitlabdeploy).

## How this project was made

It is a cookieplone project with a GitLab CI/CD layer on top. cookieplone's `project` template was run
with a subset of its options — no Ansible playbooks (the cluster repository covers those), no Varnish
cache, no GitHub Actions deploy workflow, `container_registry = gitlab`. cookieplone does not generate
GitLab CI itself, so the layer was added afterwards:

| | File | What it is |
| --- | --- | --- |
| new | `.gitlab-ci.yml` | Stages, workflow rules, image pins, includes |
| new | `.gitlab/ci/config.yml` | The `config` job: reads `repository.toml`, publishes the settings |
| new | `.gitlab/ci/templates.yml` | Shared job templates and rules |
| new | `.gitlab/ci/backend.yml`, `frontend.yml`, `changelog.yml` | Lint, test, i18n, changelog checks |
| new | `.gitlab/ci/deploy.yml` | Image builds and the swarm deploy |
| replaced | `devops/stacks/stack.yml` | Instead of `devops/stacks/<hostname>.yml`: no own Traefik, every host-specific value a variable |
| rewritten | `devops/README-GITLAB.md` | The CI/CD reference |
| extended | `repository.toml` | `[deployment]`, `[deployment.local]`, `[deployment.traefik]` — every host-specific value, once |
| extended | `Makefile`s | `debug-settings`, `release-tag`, targets reading `[deployment]` |
| extended | `backend/Dockerfile`, `frontend/Dockerfile` | A `MAINTAINER` build argument |
| extended | `docker-compose.yml` | The local stack, from `[deployment.local]` |
| removed | `.github/workflows/` | |

Chapter 2 of the documentation walks through each change.

## Deploying a copy

A copy of this repository in another GitLab project of the same group gets the runner and the CI/CD
variables from the group, but must describe its own deployment first: until `gitlab_project` in
`repository.toml` `[deployment]` matches the new project, the pipeline refuses to build or deploy, so
the copy cannot replace this project's stack. Chapter 6 of the documentation lists what to change,
and the two one-off steps on the cluster — the data directory, and creating the Plone site.

---

# The generated project README

What follows is the README that cookieplone generates for a Plone 6 project: how to install, run and
check it locally. It is kept as generated, apart from the clone URL and the descriptions of
`devops/` and `docs/`, which were updated to match this repository.

## Quick Start 🏁

### Prerequisites ✅

-   An [operating system](https://6.docs.plone.org/install/create-project-cookieplone.html#prerequisites-for-installation) that runs all the requirements mentioned.
-   [uv](https://6.docs.plone.org/install/create-project-cookieplone.html#uv)
-   [nvm](https://6.docs.plone.org/install/create-project-cookieplone.html#nvm)
-   [Node.js and pnpm](https://6.docs.plone.org/install/create-project.html#node-js) 24
-   [Make](https://6.docs.plone.org/install/create-project-cookieplone.html#make)
-   [Git](https://6.docs.plone.org/install/create-project-cookieplone.html#git)
-   [Docker](https://docs.docker.com/get-started/get-docker/) (optional)


### Installation 🔧

1.  Clone this repository, then change your working directory.

    ```shell
    git clone git@gitlab.com:plone-training1/training-deployment-gitlabdeploy.git
    cd training-deployment-gitlabdeploy
    ```

2.  Install this code base.

    ```shell
    make install
    ```


### Fire Up the Servers 🔥

1.  Create a new Plone site on your first run.

    ```shell
    make backend-create-site
    ```

2.  Start the backend at http://localhost:8080/.

    ```shell
    make backend-start
    ```

3.  In a new shell session, start the frontend at http://localhost:3000/.

    ```shell
    make frontend-start
    ```

Voila! Your Plone site should be live and kicking! 🎉

### Local Stack Deployment 📦

Deploy a local Docker Compose environment that includes the following.

- Docker images for Backend and Frontend 🖼️
- A stack with a Traefik router and a PostgreSQL database 🗃️
- Accessible at [http://playcluster-demo.localhost](http://playcluster-demo.localhost) 🌐

Run the following commands in a shell session.

```shell
make stack-create-site
make stack-start
```

And... you're all set! Your Plone site is up and running locally! 🚀

## Project structure 🏗️

This monorepo consists of the following distinct sections:

- **backend**: Houses the API and Plone installation, utilizing pip instead of buildout, and includes a policy package named playclusterdemo.
- **frontend**: Contains the React (Volto) package.
- **devops**: The Docker Swarm stack file, and `README-GITLAB.md`, the CI/CD reference.
- **docs**: The documentation, in Markdown; `make export-training` copies it into the Plone training.

### Why this structure? 🤔

- All necessary codebases to run the site are contained within the repository (excluding existing add-ons for Plone and React).
- Specific GitLab CI/CD jobs are triggered based on changes in each codebase (refer to .gitlab/ci, and to devops/README-GITLAB.md).
- Simplifies the creation of Docker images for each codebase.
- Demonstrates Plone installation/setup without buildout.

## Code quality assurance 🧐

To check your code against quality standards, run the following shell command.

```shell
make check
```

### Format the codebase

To format and rewrite the code base, ensuring it adheres to quality standards, run the following shell command.

```shell
make format
```

| Section | Tool | Description | Configuration |
| --- | --- | --- | --- |
| backend | Ruff | Python code formatting, imports sorting  | [`backend/pyproject.toml`](./backend/pyproject.toml) |
| backend | `zpretty` | XML and ZCML formatting  | -- |
| frontend | ESLint | Fixes most common frontend issues | [`frontend/.eslintrc.js`](.frontend/.eslintrc.js) |
| frontend | prettier | Format JS and Typescript code  | [`frontend/.prettierrc`](.frontend/.prettierrc) |
| frontend | Stylelint | Format Styles (css, less, sass)  | [`frontend/.stylelintrc`](.frontend/.stylelintrc) |

Formatters can also be run within the `backend` or `frontend` folders.

### Linting the codebase
or `lint`:

 ```shell
make lint
```

| Section | Tool | Description | Configuration |
| --- | --- | --- | --- |
| backend | Ruff | Checks code formatting, imports sorting  | [`backend/pyproject.toml`](./backend/pyproject.toml) |
| backend | Pyroma | Checks Python package metadata  | -- |
| backend | check-python-versions | Checks Python version information  | -- |
| backend | `zpretty` | Checks XML and ZCML formatting  | -- |
| frontend | ESLint | Checks JS / Typescript lint | [`frontend/.eslintrc.js`](.frontend/.eslintrc.js) |
| frontend | prettier | Check JS / Typescript formatting  | [`frontend/.prettierrc`](.frontend/.prettierrc) |
| frontend | Stylelint | Check Styles (css, less, sass) formatting  | [`frontend/.stylelintrc`](.frontend/.stylelintrc) |

Linters can be run individually within the `backend` or `frontend` folders.

## Internationalization 🌐

Generate translation files for Plone and Volto with ease:

```shell
make i18n
```

## Credits and acknowledgements 🙏

Generated using [Cookieplone (2.0.0b3)](https://github.com/plone/cookieplone) and [cookieplone-templates (7fe2f1a)](https://github.com/plone/cookieplone-templates/commit/7fe2f1ac3a094f51fd63b6d50bc168771ceb7abe) on 2026-08-08 21:35:33.910112. A special thanks to all contributors and supporters!
