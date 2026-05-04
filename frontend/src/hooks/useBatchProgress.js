import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";

// Terminal statuses — stop polling once we reach these
const DONE_STATUSES = new Set(["completed", "failed", "error"]);

export function useBatchProgress(batchId) {
    const [data, setData] = useState(null);

    useEffect(() => {
        if (!batchId) return;

        let isMounted = true;
        let intervalId = null;

        async function poll() {
            try {
                const token = localStorage.getItem("access_token");
                const res = await fetch(`${API}/batch/${batchId}/progress`, {
                    headers: { "Authorization": `Bearer ${token}` }
                });

                if (!res.ok) {
                    if (res.status !== 404) console.error("Failed to fetch progress:", res.status);
                    return;
                }

                const json = await res.json();
                if (!isMounted) return;

                setData(json);

                // ── Stop polling once the batch reaches a terminal state ──
                if (DONE_STATUSES.has(json.status)) {
                    clearInterval(intervalId);
                    intervalId = null;
                }
            } catch (e) {
                console.error("[useBatchProgress] Poll error:", e);
            }
        }

        // Immediate first fetch, then every 2s
        poll();
        intervalId = setInterval(poll, 2000);

        // Safety cleanup: always stop on unmount
        return () => {
            isMounted = false;
            if (intervalId) clearInterval(intervalId);
        };
    }, [batchId]);

    return data;
}
