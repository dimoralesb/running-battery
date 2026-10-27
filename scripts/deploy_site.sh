#!/usr/bin/env bash
# The public overlay: app/ built as static files and
# deployed to Azure Static Web Apps, Free plan. The demo data in app/public/data/ is committed
# from the machine that made the feeds (the same seed gives a different match elsewhere), so this
# script never regenerates it. Settings come from .env; az login is the only credential, and the
# deployment token is read at deploy time, never stored.
#
#   scripts/deploy_site.sh            # create the site if needed, build, deploy, print the URL
#
# Free plan: no charge (100 GB bandwidth a month, 250 MB per app). The resource group is never
# deleted: it also holds Foundry.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a
# shellcheck disable=SC1091
source .env
set +a

SUB=$AZURE_SUBSCRIPTION_ID
RG=$AZURE_RESOURCE_GROUP
LOC=$AZURE_LOCATION  # Free plan regions include eastus2
SITE=swa-secondwind
AZ=(--subscription "$SUB" --resource-group "$RG" --only-show-errors)

az provider register --namespace Microsoft.Web --subscription "$SUB" --wait
if ! az staticwebapp show --name "$SITE" "${AZ[@]}" --output none 2>/dev/null; then
  az staticwebapp create --name "$SITE" "${AZ[@]}" --location "$LOC" --sku Free --output none
fi

(cd app && npm ci && npm run build)
TOKEN=$(az staticwebapp secrets list --name "$SITE" "${AZ[@]}" \
  --query properties.apiKey --output tsv)
npx --yes @azure/static-web-apps-cli@2.0.10 deploy app/dist \
  --deployment-token "$TOKEN" --env production
unset TOKEN

HOST=$(az staticwebapp show --name "$SITE" "${AZ[@]}" --query defaultHostname --output tsv)
echo "site: https://$HOST"
for f in "" data/story/match.json data/story/positions.bin data/natural/feed.json; do
  curl --silent --show-error --output /dev/null --retry 5 --retry-delay 5 --retry-all-errors \
    --write-out "HTTP %{http_code} %{content_type} /$f\n" "https://$HOST/$f"
done
