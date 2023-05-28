# release-k8s-charm

A quick and dirty charmhub release creation utility for Kubernetes operator charms: packs the charm, uploads the OCI images, uploads the charm, then releases.

```bash
❯ sudo snap install release-k8s-charm
❯ release-k8s-charm --help
usage: release-k8s-charm [-h] --charm-metadata CHARM_METADATA

options:
  -h, --help            show this help message and exit
  --charm-metadata CHARM_METADATA
                        Path to charm's metadata.yaml
  --channel CHANNEL     Channel to release the packed, uploaded charm on
```

**_NOTE:_** If you have GitHub for source control and CI, you should probably use the [canonical/charming-actions GitHub actions](https://github.com/canonical/charming-actions) instead of this tool.
