#!/usr/bin/env bash

docker run --name api-poc-postgres --rm -e POSTGRES_PASSWORD=pillar -p 5432:5432/tcp postgres