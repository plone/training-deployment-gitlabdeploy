---
myst:
  html_meta:
    "description": "Documentation for training-deployment-gitlabdeploy, a Plone 6 project that builds, publishes and deploys itself onto the playcluster with GitLab CI/CD."
    "property=og:description": "Documentation for training-deployment-gitlabdeploy, a Plone 6 project that builds, publishes and deploys itself onto the playcluster with GitLab CI/CD."
    "property=og:title": "training-deployment-gitlabdeploy"
    "keywords": "Plone, cookieplone, GitLab CI, Docker Swarm, playcluster"
---

# training-deployment-gitlabdeploy

A Plone 6 project generated with cookieplone, and extended so that it builds,
publishes and deploys itself onto the playcluster with GitLab CI/CD. It is the
reference deployment of the Plone deployment training, served at
<https://playcluster.plone.org>.

It exists to be read as much as run: the pipeline, the container images and the
Docker Swarm stack are all here, and the chapters below explain how they fit
together.

% The chapters are listed here rather than in the overview's own index, so each
% becomes a top-level chapter of the PDF. Nested inside that page they would
% attach to whichever section holds the toctree.

```{toctree}
:caption: From repository to running site
:maxdepth: 1
:hidden: true

tutorials/pipeline/index
tutorials/pipeline/1-project
tutorials/pipeline/2-differences
tutorials/pipeline/3-pipeline
tutorials/pipeline/4-registry
tutorials/pipeline/5-deploy
tutorials/pipeline/6-operating
```

## Elsewhere in the repository

- [`devops/README-GITLAB.md`](https://gitlab.com/plone-training1/training-deployment-gitlabdeploy/-/blob/main/devops/README-GITLAB.md)
  — the reference version of the CI/CD setup, kept next to the code
- `repository.toml` — the `[deployment]` section, where every host-specific
  value lives
- `.gitlab/ci/` — the pipeline, split by area

The [training-deployment-playcluster](https://github.com/plone/training-deployment-playcluster)
repository builds and documents the cluster this project deploys onto.
