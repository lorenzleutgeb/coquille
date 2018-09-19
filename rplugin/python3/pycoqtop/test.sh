#!/bin/env sh

for version in 8.6 8.7 8.8; do
    if guix environment --ad-hoc python-pytest coq@${version} -- py.test; then
        printf "Success with coq ${version}\n"
    else
        printf "Error while running tests with coq ${version}\n";
        exit 1
    fi
done
