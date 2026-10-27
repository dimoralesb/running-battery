#!/usr/bin/env bash
# Azure test deployment ("Fri 16"): an empty Container App and a Basic Event Hub,
# to find free-trial limits early. Settings come from .env (see .env.example); auth is keyless
# (az login), and the Event Hubs namespace has local (key) auth switched off.
#
#   scripts/azure_test_deploy.sh           # create, then print the app URL and its HTTP status
#   scripts/azure_test_deploy.sh --delete  # remove only what this script created
#
# This creates billed resources. The resource group is not deleted: it also holds Foundry.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a
# shellcheck disable=SC1091
source .env
set +a

SUB=$AZURE_SUBSCRIPTION_ID
RG=$AZURE_RESOURCE_GROUP
LOC=$AZURE_LOCATION
SUFFIX=${RG##*-}
ENV_NAME=cae-secondwind
APP=ca-secondwind-test
EHNS=ehns-secondwind-$SUFFIX  # namespace names are global
HUB=match-stream
AZ=(--subscription "$SUB" --resource-group "$RG" --only-show-errors)

if [[ ${1:-} == "--delete" ]]; then
  az containerapp delete --name "$APP" "${AZ[@]}" --yes
  az containerapp env delete --name "$ENV_NAME" "${AZ[@]}" --yes
  az eventhubs namespace delete --name "$EHNS" "${AZ[@]}"
  exit 0
fi

az extension add --name containerapp --upgrade --only-show-errors
az provider register --namespace Microsoft.App --subscription "$SUB" --wait
az provider register --namespace Microsoft.EventHub --subscription "$SUB" --wait

# Container Apps: consumption plan, scale to zero, no Log Analytics workspace.
az containerapp env create --name "$ENV_NAME" --location "$LOC" "${AZ[@]}" \
  --logs-destination none
az containerapp create --name "$APP" "${AZ[@]}" --environment "$ENV_NAME" \
  --image mcr.microsoft.com/k8se/quickstart:latest \
  --ingress external --target-port 80 \
  --min-replicas 0 --max-replicas 1 --cpu 0.25 --memory 0.5Gi

# Event Hubs: Basic tier, one throughput unit, keyless.
az eventhubs namespace create --name "$EHNS" --location "$LOC" "${AZ[@]}" \
  --sku Basic --capacity 1 --disable-local-auth true
az eventhubs eventhub create --name "$HUB" --namespace-name "$EHNS" "${AZ[@]}" \
  --partition-count 2 --retention-time-in-hours 1 --cleanup-policy Delete
# Keyless sending: the signed-in user may send to this namespace (and nothing else).
ME=$(az ad signed-in-user show --query id --output tsv)
NS_ID=$(az eventhubs namespace show --name "$EHNS" "${AZ[@]}" --query id --output tsv)
az role assignment create --assignee-object-id "$ME" --assignee-principal-type User \
  --role "Azure Event Hubs Data Sender" --scope "$NS_ID" --subscription "$SUB" --output none

FQDN=$(az containerapp show --name "$APP" "${AZ[@]}" \
  --query properties.configuration.ingress.fqdn --output tsv)
echo "app: https://$FQDN"
curl --silent --show-error --output /dev/null --write-out "HTTP %{http_code}\n" \
  --retry 5 --retry-delay 10 --retry-all-errors "https://$FQDN"
