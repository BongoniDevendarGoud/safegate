/**
 * SafeGate Official TypeScript / Node.js SDK.
 * Integrates host applications with SafeGate media-integrity screening API.
 */

import * as crypto from 'node:crypto';

export type FrameColor = 'RED' | 'YELLOW' | 'GREEN';
export type DecisionVerdict = 'ALLOW' | 'BLOCK' | 'HUMAN_REVIEW' | 'PENDING';

export interface UploadResponse {
  upload_id: string;
  tenant_id: string;
  filename: string;
  mime_type: string;
  file_size_bytes: number;
  sha256_hash: string;
  status: string;
  verdict: DecisionVerdict;
  message: string;
}

export interface FrameScoreSummary {
  frame_index: number;
  timestamp_ms: number;
  color: FrameColor;
  deepfake_score: number;
  sensitive_score: number;
  uncertainty_score: number;
}

export interface UploadStatusResponse {
  upload_id: string;
  tenant_id: string;
  filename: string;
  mime_type: string;
  sha256_hash: string;
  status: string;
  verdict: DecisionVerdict;
  total_frames: number;
  red_frames: number;
  yellow_frames: number;
  green_frames: number;
  frames: FrameScoreSummary[];
  published_url: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface WebhookEventPayload<T = Record<string, unknown>> {
  event: string;
  upload_id: string;
  tenant_id: string;
  verdict: DecisionVerdict;
  timestamp: string;
  data: T;
}

/**
 * Validates HMAC-SHA256 signature on incoming SafeGate webhook notifications.
 */
export function verifyWebhookSignature(
  rawPayload: string | Buffer,
  signature: string,
  timestampSec: number,
  secret: string,
  maxDriftSeconds = 300
): boolean {
  const now = Math.floor(Date.now() / 1000);
  if (Math.abs(now - timestampSec) > maxDriftSeconds) {
    return false;
  }

  const payloadBuffer = typeof rawPayload === 'string' ? Buffer.from(rawPayload, 'utf-8') : rawPayload;
  const toSign = Buffer.concat([Buffer.from(`${timestampSec}.`, 'utf-8'), payloadBuffer]);

  const hmac = crypto.createHmac('sha256', secret);
  hmac.update(toSign);
  const expectedSig = hmac.digest('hex');

  return crypto.timingSafeEqual(Buffer.from(expectedSig, 'hex'), Buffer.from(signature, 'hex'));
}

export interface SafeGateClientOptions {
  baseUrl?: string;
  tenantId?: string;
  timeoutMs?: number;
}

export class SafeGateClient {
  private readonly baseUrl: string;
  private readonly tenantId: string;
  private readonly timeoutMs: number;

  constructor(options: SafeGateClientOptions = {}) {
    this.baseUrl = (options.baseUrl || 'http://localhost:8000').replace(/\/+$/, '');
    this.tenantId = options.tenantId || 'default-tenant';
    this.timeoutMs = options.timeoutMs || 30000;
  }

  /**
   * Queries status and verdict for an upload.
   */
  async getStatus(uploadId: string): Promise<UploadStatusResponse> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.timeoutMs);

    try {
      const resp = await fetch(`${this.baseUrl}/v1/media/${uploadId}`, {
        headers: {
          'X-Tenant-ID': this.tenantId,
        },
        signal: controller.signal,
      });

      if (!resp.ok) {
        throw new Error(`SafeGate API error ${resp.status}: ${await resp.text()}`);
      }

      return (await resp.json()) as UploadStatusResponse;
    } finally {
      clearTimeout(timeout);
    }
  }

  /**
   * Polls until processing completes or timeout is exceeded.
   */
  async waitForVerdict(
    uploadId: string,
    pollIntervalMs = 1000,
    maxWaitMs = 60000
  ): Promise<UploadStatusResponse> {
    const deadline = Date.now() + maxWaitMs;

    while (Date.now() < deadline) {
      const status = await this.getStatus(uploadId);
      if (status.status === 'COMPLETED' || status.status === 'FAILED') {
        return status;
      }
      await new Promise((r) => setTimeout(r, pollIntervalMs));
    }

    throw new Error(`Timeout waiting for SafeGate verdict on upload '${uploadId}'`);
  }
}
