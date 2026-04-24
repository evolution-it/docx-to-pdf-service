# DOCX to PDF service

Flask API that accepts a `.docx` upload and returns a PDF (LibreOffice headless in Docker).

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness / health JSON |
| `POST` | `/convert` | `multipart/form-data` field **`file`** (`.docx` only) → PDF bytes |
| `GET` | `/` | API metadata |


## Run locally (Docker)

From the repository root:

```bash
docker build -t docx-to-pdf:local .
docker run --rm -p 8080:8080 docx-to-pdf:local
```

Check health:

```bash
curl -s http://localhost:8080/health
```

Optional CORS for a separate UI origin (comma-separated list, no spaces unless encoded in URLs):

```bash
docker run --rm -p 8080:8080 -e CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173 docx-to-pdf:local
```

Copy [`.env.example`](.env.example) to `.env` for local non-Docker runs and adjust.

## Connect a UI

1. **API base URL** — e.g. `http://localhost:8080` or `https://<your-container-app>.azurecontainerapps.io` (no trailing slash).
2. **Request:** `POST {base}/convert` with `FormData` and append the Word file under the key **`file`**. Do not set the `Content-Type` header manually (the browser sets the multipart boundary).
3. **Success:** status `200`, body is a PDF blob (`Content-Type: application/pdf`). Use `response.blob()` then `URL.createObjectURL` for download or preview.
4. **Errors:** JSON `{"error":"..."}` with `4xx` / `5xx`.

### Browser demo

Open [`examples/browser-demo.html`](examples/browser-demo.html) in a browser (double-click or any static file server). Set the API base URL if needed; it is stored in `localStorage` as `docxPdfApiBase`.

If the demo page is opened as `file://` and the API is `http://localhost:8080`, some browsers may still restrict `fetch`; use a simple static server for the demo, e.g. `npx serve examples` or your UI dev server.

### CORS

If the UI is served from a **different origin** than the API, set **`CORS_ORIGINS`** to an explicit comma-separated allowlist (your real UI URLs). Do not use `*` in production. Alternatively, put the UI and API behind the same origin (reverse proxy, Front Door, Static Web Apps API routes).

## Azure Container Apps and CI/CD

1. Create a resource group, **Azure Container Registry**, Log Analytics workspace, **Container Apps** environment, and a **Container App** with ingress **external**, target port **8080**, image from ACR. Use **`GET /health`** for probes.
2. Build and push the image (e.g. `az acr build` from the repo root, or push from local Docker after `az acr login`).
3. Enable GitHub Actions: add repository **Secrets** `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` (OIDC app registration) and **Variables** `ACR_NAME`, `RESOURCE_GROUP`, `CONTAINER_APP_NAME`, `IMAGE_NAME` (e.g. `docx-to-pdf`). See [Azure Login with OIDC](https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect).
4. Pushes to **`main`** run [`.github/workflows/deploy-container-apps.yml`](.github/workflows/deploy-container-apps.yml) (`workflow_dispatch` is also available).

## GitHub: first push

If the remote is empty:

```bash
git branch -M main
git remote add origin https://github.com/OWNER/REPO.git
git push -u origin main
```

Use an empty new repo (no README) to avoid merge conflicts on first push.

### Pushing workflow files (PAT scope)

If `git push` is rejected with *refusing to allow a Personal Access Token to create or update workflow … without `workflow` scope*:

- **Classic PAT:** enable the **`workflow`** scope when creating or editing the token.
- **Fine-grained PAT:** under repository permissions, set **Actions** to **Read and write** (or equivalent for workflow updates).

Do **not** embed a PAT in the Git remote URL (e.g. `https://token@github.com/...`). Prefer [Git Credential Manager](https://github.com/git-ecosystem/git-credential-manager), `gh auth login`, or SSH. **Revoke** any token that was ever stored in a URL or committed to history.

## Azure one-time setup and CI variables

The pipeline [`.github/workflows/deploy-container-apps.yml`](.github/workflows/deploy-container-apps.yml) expects Azure resources you create once (portal or CLI): resource group, **Azure Container Registry**, Log Analytics workspace, **Container Apps environment**, and a **Container App** with **external** ingress and target port **8080**, plus **`GET /health`** probes. Register `Microsoft.App` if needed (`az provider register -n Microsoft.App`).

After the app exists and the first image is in ACR, configure GitHub **Actions**:

| Type | Name | Purpose |
|------|------|--------|
| Secret | `AZURE_CLIENT_ID` | Entra app (OIDC) client ID |
| Secret | `AZURE_TENANT_ID` | Directory (tenant) ID |
| Secret | `AZURE_SUBSCRIPTION_ID` | Subscription ID |
| Variable | `ACR_NAME` | Registry name (no `.azurecr.io`) |
| Variable | `RESOURCE_GROUP` | Resource group of ACR and Container App |
| Variable | `CONTAINER_APP_NAME` | Container App resource name |
| Variable | `IMAGE_NAME` | Repository name in ACR (e.g. `docx-to-pdf`) |

Grant the OIDC identity permission to run **`az acr build`** / push and **`az containerapp update`** on those resources (e.g. **Contributor** on the resource group, or narrower roles). Pushes to **`main`** build with `az acr build` and deploy the image tag `${{ github.sha }}`.
