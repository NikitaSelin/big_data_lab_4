#!/bin/bash
touch ansible-password.txt
echo "$VAULT_CREDS_PSW" > ansible-password.txt
LC_ALL="C.UTF-8" ansible-playbook setup.yml --vault-password-file ansible-password.txt