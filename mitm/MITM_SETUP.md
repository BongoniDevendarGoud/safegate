# SafeGate — Network Interception Lab Setup Guide (`mitmproxy`)

This guide details how to run the SafeGate `mitmproxy` network interception addon in an isolated laboratory environment to demonstrate real-time video screening before payloads reach upstream servers.

---

> [!CAUTION]
> **LEGAL & ETHICAL LAB NOTICE**
> TLS interception (MITM) requires decrypting encrypted network traffic using a custom Root Certificate Authority (CA). 
> - This setup is **strictly intended for an authorized, consented research or academic laboratory environment**.
> - Never install interception certificates on non-test devices or monitor unauthorized networks without explicit legal authorization.
> - **In Production Environments**: Do **NOT** use TLS interception for upload screening. Modern platforms enforce screening via:
>   1. **API Gateway / Reverse Proxy**: Envoy, Kong, NGINX, or Cloudflare Workers inspecting authorized API routes.
>   2. **Storage Pre-Signed Upload Webhooks**: Direct cloud storage uploads (e.g., AWS S3 Object Lambda, Cloudflare Stream Webhooks, Google Cloud Storage Notifications) triggering an asynchronous fail-closed quarantine queue before publishing.

---

## 1. Prerequisites

1. Python 3.10+ installed.
2. `mitmproxy` installed:
   ```bash
   pip install mitmproxy
   ```
3. SafeGate FastAPI server running:
   ```bash
   # From the safegate project root:
   python -m app.main
   # Gateway active on http://127.0.0.1:8000
   ```

---

## 2. Installing the mitmproxy Lab Certificate

When `mitmproxy` runs for the first time, it generates a custom Root CA certificate in `~/.mitmproxy/` (`%USERPROFILE%\.mitmproxy\` on Windows). To inspect HTTPS traffic from a test browser or client, this lab certificate must be trusted.

### Windows Lab Machine
1. Start `mitmproxy` once to generate certificates:
   ```bash
   mitmdump --version
   ```
2. Press `Win + R`, type `certmgr.msc`, and press **Enter**.
3. Right-click **Trusted Root Certification Authorities** > **All Tasks** > **Import...**
4. Browse to `%USERPROFILE%\.mitmproxy\mitmproxy-ca-cert.p12` (or `.cer`).
5. Complete the wizard and confirm the installation.

### macOS Lab Machine
1. Open **Keychain Access**.
2. Drag `~/.mitmproxy/mitmproxy-ca-cert.pem` into the **System** or **login** keychain.
3. Double-click the imported certificate, expand **Trust**, and select **Always Trust**.

### Linux / Ubuntu Lab Machine
```bash
sudo cp ~/.mitmproxy/mitmproxy-ca-cert.crt /usr/local/share/ca-certificates/mitmproxy.crt
sudo update-ca-certificates
```

### Firefox / Chrome Lab Profile
Alternatively, navigate to `http://mitm.it` while connected through the proxy to download and install the certificate directly for your test browser profile.

---

## 3. Starting the Interceptor

Launch `mitmdump` with the SafeGate addon:

```bash
# Optional: customize SafeGate URL or Client Key if not using defaults
export SAFEGATE_URL="http://127.0.0.1:8000/api/upload"
export SAFEGATE_CLIENT_KEY="dev-client-key-change-in-production-98765"

# Launch mitmdump on port 8080 with the SafeGate interceptor script
mitmdump -s mitm/intercept.py -p 8080
```

On Windows PowerShell:
```powershell
$env:SAFEGATE_URL="http://127.0.0.1:8000/api/upload"
$env:SAFEGATE_CLIENT_KEY="dev-client-key-change-in-production-98765"
mitmdump -s mitm/intercept.py -p 8080
```

---

## 4. Testing Lab Scenarios

### Scenario A: Clean Video Upload (Permitted)
Configure your HTTP client (e.g. `curl`) to use the proxy on port `8080`:

```bash
curl -x http://127.0.0.1:8080 \
     -X POST https://httpbin.org/post \
     -F "file=@tests/sample_clean.mp4" \
     -v
```

**Expected Result:**
1. Proxy intercepts the upload.
2. Forwards media to SafeGate `/api/upload`.
3. SafeGate returns `verdict: "ALLOW"`.
4. Request passes through transparently to `https://httpbin.org/post` with HTTP 200.

---

### Scenario B: Prohibited / Blocked Media (Denied)
Upload a file that triggers a `BLOCK` (e.g. testing with lowered threshold or blocklisted hash):

```bash
curl -x http://127.0.0.1:8080 \
     -X POST https://httpbin.org/post \
     -F "file=@tests/sample_blocked.mp4" \
     -v
```

**Expected Result:**
1. Proxy terminates the connection immediately.
2. Returns **HTTP 403 Forbidden**:
   ```http
   HTTP/1.1 403 Forbidden
   Content-Type: text/plain; charset=utf-8
   X-SafeGate-Verdict: BLOCK

   Blocked by SafeGate: policy violation [BLOCK]
   Reason: Prohibited visual content identified (NSFW score: 0.98 >= 0.85).
   ```
3. The upstream server (`httpbin.org`) **never receives the payload**.

---

### Scenario C: Fail-Closed Gateway Outage Verification
1. Stop the SafeGate FastAPI server (`Ctrl+C` on port 8000).
2. Attempt an upload through the proxy:
   ```bash
   curl -x http://127.0.0.1:8080 \
        -X POST https://httpbin.org/post \
        -F "file=@tests/sample_clean.mp4" \
        -v
   ```

**Expected Result:**
1. Proxy detects SafeGate connection refusal.
2. The proxy **DOES NOT** fail-open.
3. Returns **HTTP 403 Forbidden**:
   ```http
   HTTP/1.1 403 Forbidden
   Content-Type: text/plain; charset=utf-8

   Blocked by SafeGate: policy violation [BLOCK]
   Reason: Fail-closed enforcement: SafeGate gateway is unreachable.
   ```
4. This proves that an attacker cannot bypass screening by disabling or overwhelming the gateway.
