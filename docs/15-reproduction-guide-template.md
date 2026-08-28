# Reproduction Guide

Complete this document as implementation becomes runnable.

## Prerequisites

Document:

- Docker/runtime requirements;
- optional local model requirements;
- supported provider credentials;
- expected machine resources.

## Setup

Provide exact clean-environment commands.

```bash
# clone
# copy .env.example -> .env
# configure one provider or Ollama
# start dependencies/app
```

## Load frozen scheme corpus

Document the exact command and expected corpus/version count.

## Run baseline

Provide the exact command and where results are written.

## Run final workflow

Provide the exact command.

## Run evaluation

Provide the exact command that runs the same frozen cases against baseline and final.

## Expected output

Describe generated files and representative metrics without claiming values until measured.

## Runtime and cost

Record approximate local runtime and provider cost under the submission configuration.

## Troubleshooting

Include common issues:

- missing provider key;
- unavailable Ollama model;
- migration/database readiness;
- unsupported provider capability;
- voice device/browser permissions.
