#!/usr/bin/env python3

import argparse
import os
import subprocess
import yaml


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--charm-metadata",
        required=True,
        help="Path to charm's metadata.yaml",
    )
    return parser.parse_args()


def load_yaml_file(metadata_path):
    with open(metadata_path, "r") as stream:
        try:
            metadata = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            exit(1)
    return metadata


def get_charm_name(metadata):
    charm_name = metadata.get("name")
    if not charm_name:
        print("Charm name not found in metadata.")
        exit(1)
    return charm_name


def pack_charm(charm_dir):
    pack_command = subprocess.run(
        ["charmcraft", "pack"],
        cwd=charm_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    if pack_command.returncode != 0:
        exit(pack_command.returncode)

    output_lines = pack_command.stdout.splitlines()
    charm_file = None
    for line in output_lines:
        if line.endswith(".charm"):
            charm_file = line.lstrip()
            break

    if charm_file is None:
        print("Evidently failed to pack the charm (or find the packed charm).")
        exit(1)

    return os.path.join(charm_dir, charm_file)


def get_image_digest(image):
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

    return digest


def upload_resource(charm_name, resource_name, digest):
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
            return f"{resource_name}:{resource_revision}"


def process_resources(resources, charm_name):
    resource_revisions = []
    for resource_name, resource_data in resources.items():
        if resource_data["type"] == "oci-image":
            image = resource_data["upstream-source"]
            digest = get_image_digest(image)
            resource_revision = upload_resource(charm_name, resource_name, digest)
            resource_revisions.append(resource_revision)
    return resource_revisions


def upload_charm(charm_path):
    upload_charm_command = subprocess.run(
        ["charmcraft", "upload", charm_path],
        check=True,
        capture_output=True,
        text=True,
    )
    if upload_charm_command.returncode != 0:
        output_lines = upload_charm_command.stderr.splitlines()
        for line in output_lines:
            if "Revision of the existing package is:" in line:
                return line.split(": ")[-1]
        exit(upload_charm_command.returncode)
    else:
        output_lines = upload_charm_command.stdout.splitlines()
        for line in output_lines:
            if "Revision" in line and "created" in line:
                return line.split()[1]


def release_charm(charm_name, charm_revision, resource_revisions):
    release_command = subprocess.run(
        [
            "charmcraft",
            "release",
            charm_name,
            "--revision",
            charm_revision,
            "--channel=beta",
        ]
        + [f"--resource={rr}" for rr in resource_revisions],
        check=True,
    )
    if release_command.returncode != 0:
        exit(release_command.returncode)


def main():
    args = parse_arguments()
    metadata_path = args.charm_metadata
    charm_dir = os.path.dirname(metadata_path)
    metadata = load_yaml_file(metadata_path)
    charm_name = get_charm_name(metadata)
    charm_file = pack_charm(charm_dir)
    resources = metadata.get("resources", {})
    resource_revisions = process_resources(resources, charm_name)
    charm_revision = upload_charm(charm_file)
    release_charm(charm_name, charm_revision, resource_revisions)


if __name__ == "__main__":
    main()
