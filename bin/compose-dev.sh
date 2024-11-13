#!/bin/sh

command="docker compose -f ./compose.yml -f ./docker/compose.dev.yml"
if [ -f compose.overwrite.yml ]; then
    command="${command} -f compose.overwrite.yml"
fi

$command "$@"
