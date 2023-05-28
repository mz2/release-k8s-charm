# release-k8s-charm

A quick and dirty charmhub release creation utility for Kubernetes operator charms: packs the charm, uploads the OCI images, uploads the charm, then releases.

```bash
❯ release-k8s-charm --help
usage: release-k8s-charm [-h] --charm-metadata CHARM_METADATA

options:
  -h, --help            show this help message and exit
  --charm-metadata CHARM_METADATA
                        Path to charm's metadata.yaml
```
