# Temporary public HTTPS preview

The user selected a free temporary link. This exposes the actual local FastAPI website through Pinggy SSH forwarding; it does not move Kafka, Spark or MongoDB to a cloud host. [Official Pinggy HTTP tunnel documentation](https://pinggy.io/docs/http_tunnels/) describes the SSH443 endpoint used here.

From PowerShell7 in the project:

```powershell
.\scripts\Start-Project.ps1
.\scripts\Start-SharePreview.ps1
```

Use the HTTPS URL printed by the second command. It is also saved in ignored `.runtime/public-preview.json`. The actual free session reports a **60-minute expiry**. After expiry, rerun the command to start a new session and URL. Visitors see Pinggy's screening page on their first visit; click **Enter site** to open the app. Health probes use an application User-Agent and must match the actual ScholarshipMap health marker; browser QA clicks the screening button normally.

Keep the computer awake, internet connected, project services running and the background SSH process alive. Closing the browser is fine. This is a demonstration link, not independent permanent hosting or an uptime guarantee. The collector starts with the project, then runs every6 hours; the next collection time and connection heartbeat are visible in the website. Public viewers use the same stored catalogue as local viewers.

```powershell
# Stop only the public link
.\scripts\Stop-PublicPreview.ps1
# Stop link and project services, retaining data/checkpoints
.\scripts\Stop-Project.ps1
```

Only HTTP port8000 is forwarded. Kafka and MongoDB remain on loopback. SSH uses a dedicated ignored project key, dedicated known-hosts file, no personal SSH configuration and no personal agent identities. Logs are `.runtime/logs/share-preview.out.log` and `.runtime/logs/share-preview.err.log`. Scripts validate owned processes before stopping a former provider. Do not share private keys or runtime folders.

Cloudflare Quick Tunnel was attempted with an official digest-verified cloudflared binary, but its provisioning endpoint timed out/returned503 and later429. localhost.run provided public health access but its free bandwidth throttling prevented reliable full-page loading; it also rotated the domain during testing. It remains an optional fallback via `Start-SharePreview.ps1 -Provider localhost.run`: rerun that command to read and verify the latest rotated address, since old addresses can return `502 no tunnel`.

Pinggy is the verified browser-tested default. The prepared Docker Compose configuration remains unexecuted on this host because Docker is absent; a permanent cloud deployment would require a separate host and resource setup.
