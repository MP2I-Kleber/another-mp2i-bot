#!/bin/bash

# Pass all arguments to docker compose with both compose.yml and compose.caddy.yml
docker compose -f compose.yml -f compose.caddy.yml "$@"
