#!/usr/bin/env python3

import argparse
import os
import subprocess

import yaml

parser = argparse.ArgumentParser()
parser.add_argument("--charm-path", required=True)

args = parser.parse_args()

charm_dir = os.path.dirname(args.charm_path)
metadata_path = os.path.join(charm_dir, "metadata.yaml")
charm_name = os.path.basename(args.charm_path).split("_")[0]

with open(metadata_path, "r") as stream:
    try:
        data = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)
        exit(1)

resources = data.get("resources", {})
resource_revisions = []

for resource_name, resource_data in resources.items():
    if resource_data["type"] == "oci-image":
        image = resource_data["upstream-source"]

        pull_command = subprocess.run(["docker", "pull", image], check=True)
        if pull_command.returncode != 0:
            exit(pull_command.returncode)

        image_name, image_tag = image.rsplit(":", 1)

        tag_digest_command = subprocess.run(
            [
                "docker",
                "images",
                "--no-trunc",
                "--filter",
                f"reference={image_name}",
                "--format",
                "{{.Tag}} {{.Digest}}",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        if tag_digest_command.returncode != 0:
            exit(tag_digest_command.returncode)

        output_lines = tag_digest_command.stdout.splitlines()
        digest = None
        for line in output_lines:
            tag, line_digest = line.split()
            if tag == image_tag:
                digest = line_digest
                break

        if digest is None:
            print(f"Could not find tag {image_tag} for image {image_name}")
            exit(1)

        upload_resource_command = subprocess.run(
            [
                "charmcraft",
                "upload-resource",
                "--image",
                digest,
                charm_name,
                resource_name,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        if upload_resource_command.returncode != 0:
            exit(upload_resource_command.returncode)

        output_lines = upload_resource_command.stdout.splitlines()
        for line in output_lines:
            if line.startswith("Revision"):
                resource_revision = line.split()[1]
                print(f"Revision of resource {resource_name}: {resource_revision}")
                resource_revisions.append(f"{resource_name}:{resource_revision}")

upload_charm_command = subprocess.run(
    ["charmcraft", "upload", args.charm_path], check=True, capture_output=True, text=True
)
if upload_charm_command.returncode != 0:
    output_lines = upload_charm_command.stderr.splitlines()
    for line in output_lines:
        if "Revision of the existing package is:" in line:
            charm_revision = line.split(": ")[-1]
else:
    output_lines = upload_charm_command.stdout.splitlines()
    for line in output_lines:
        if "Revision" in line and "created" in line:
            charm_revision = line.split()[1]

release_command = subprocess.run(
    ["charmcraft", "release", charm_name, "--revision", charm_revision, "--channel=beta"]
    + [f"--resource={rr}" for rr in resource_revisions],
    check=True,
)
if release_command.returncode != 0:
    exit(release_command.returncode)
