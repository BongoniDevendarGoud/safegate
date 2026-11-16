import React, { useCallback, useEffect, useState } from "react";
import { AuditActionModal } from "./components/AuditActionModal";
import { ForensicViewer } from "./components/ForensicViewer";
import { ReviewQueue } from "./components/ReviewQueue";
import { WellnessBanner } from "./components/WellnessBanner";
import {
  ReviewPackageResponse,
  ReviewQueueItem,
  ReviewerActionRequest,
} from "./types";

export const App: React.FC = () => {
  const [reviewerId] = useState<string>("mod_alice_security");
  const [queueItems, setQueueItems] = useState<ReviewQueueItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedPackage, setSelectedPackage] = useState<ReviewPackageResponse | null>(null);
  const [isLoadingQueue, setIsLoadingQueue] = useState<boolean>(false);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [isSubmittingAction, setIsSubmittingAction] = useState<boolean>(false);

  const fetchQueue = useCallback(async () => {
    setIsLoadingQueue(true);
    try {
      const resp = await fetch("/v1/moderation/queue");
      if (resp.ok) {
        const data = await resp.json();
        setQueueItems(data.items || []);
        if (data.items.length > 0 && !selectedId) {
          setSelectedId(data.items[0].upload_id);
        }
      }
    } catch (err) {
      console.error("Failed to fetch moderation queue:", err);
    } finally {
      setIsLoadingQueue(false);
    }
  }, [selectedId]);

  const fetchPackage = useCallback(async (uploadId: string) => {
    try {
      const resp = await fetch(`/v1/moderation/${uploadId}`);
      if (resp.ok) {
        const data = await resp.json();
        setSelectedPackage(data);
      }
    } catch (err) {
      console.error(`Failed to fetch forensic package for ${uploadId}:`, err);
    }
  }, []);

  useEffect(() => {
    fetchQueue();
  }, [fetchQueue]);

  useEffect(() => {
    if (selectedId) {
      fetchPackage(selectedId);
    } else {
      setSelectedPackage(null);
    }
  }, [selectedId, fetchPackage]);

  const handleActionSubmit = async (req: ReviewerActionRequest) => {
    if (!selectedId) return;
    setIsSubmittingAction(true);
    try {
      const resp = await fetch(`/v1/moderation/${selectedId}/action`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Tenant-ID": selectedPackage?.tenant_id || "default-tenant",
        },
        body: JSON.stringify(req),
      });

      if (!resp.ok) {
        const errJson = await resp.json().catch(() => ({}));
        throw new Error(errJson.detail || `Action failed with HTTP ${resp.status}`);
      }

      // Remove item from queue and reset selection
      setQueueItems((prev) => prev.filter((i) => i.upload_id !== selectedId));
      setSelectedId(null);
      setSelectedPackage(null);
      await fetchQueue();
    } finally {
      setIsSubmittingAction(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
      <WellnessBanner reviewerId={reviewerId} />

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <ReviewQueue
          items={queueItems}
          selectedId={selectedId}
          onSelect={(id) => setSelectedId(id)}
          isLoading={isLoadingQueue}
          onRefresh={fetchQueue}
        />

        {selectedPackage ? (
          <ForensicViewer
            packageData={selectedPackage}
            onOpenActionModal={() => setIsModalOpen(true)}
          />
        ) : (
          <div
            style={{
              flex: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#64748b",
            }}
          >
            Select an upload from the triage queue to inspect forensic evidence.
          </div>
        )}
      </div>

      {isModalOpen && selectedId && (
        <AuditActionModal
          uploadId={selectedId}
          reviewerId={reviewerId}
          onClose={() => setIsModalOpen(false)}
          onSubmit={handleActionSubmit}
          isSubmitting={isSubmittingAction}
        />
      )}
    </div>
  );
};
