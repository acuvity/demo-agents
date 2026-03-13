# 🚀 Acuvity AI Security Platform CLI Instructions

Acuvity CLI tool `acuctl` can be used to make configuration changes.

## Make a path for acuctl

   ```bash
   mkdir -p ~/.acuctl
   export PATH=$PATH:~/.acuctl
   ```

## 🌟 Download `acuctl`

### MacOS

- ARM

   ```bash
   curl -o acuctl https://hub.acuvity.ai/stable/cli/darwin/arm64/acuctl
   chmod +x ~/.acuctl/acuctl
   ```

- AMD

   ```bash
   curl -o acuctl https://hub.acuvity.ai/stable/cli/darwin/amd64/acuctl
   chmod +x ~/.acuctl/acuctl
   ```

### Linux

- ARM

   ```bash
   curl -o ~/.acuctl/acuctl https://hub.acuvity.ai/stable/cli/linux/arm64/acuctl
   chmod +x ~/.acuctl/acuctl
   ```

- AMD

   ```bash
   curl -o ~/.acuctl/acuctl https://hub.acuvity.ai/stable/cli/linux/amd64/acuctl
   chmod +x ~/.acuctl/acuctl
   ```


## 🌟 Create a token with `acuctl`


   ```bash
   export ACUCTL_ORG="acuvity.ai"
   acuctl login  -A https://api.acuvity.ai --apps
   export ACUCTL_TOKEN=$(acuctl login -A https://api.acuvity.ai --apps --reinit --print-token)
   echo "Token: ${ACUCTL_TOKEN}"
   ```

## 🌟 Importing a manifest file with `acuctl`

   ```bash
   export ACUVITY_PROJECT=demo-agents
   acuctl import -A https://api.acuvity.ai --namespace /orgs/acuvity.ai/apps/${ACUVITY_PROJECT} manifest.yaml
   ```