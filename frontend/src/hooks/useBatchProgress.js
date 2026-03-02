import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";

export function useBatchProgress(batchId) {
    const [data, setData] = useState(null);

    useEffect(() => {
        if (!batchId) return;

        let isMounted = true;

        async function poll() {
            try {
                const token = localStorage.getItem("access_token");
                const res = await fetch(`${API}/batch/${batchId}/progress`, {
                    headers: { "Authorization": `Bearer ${token}` }
                });
                if (!res.ok) {
                    if (res.status !== 404) console.error("Failed to fetch progress");
                    return;
                }
                const json = await res.json();
                if (isMounted) setData(json);
            } catch (e) {
                console.error(e);
            }
        }

        poll();
        const intervalId = setInterval(poll, 1500); // Poll every 1.5s for snappy UX
        return () => {
            isMounted = false;
            clearInterval(intervalId);
        };
    }, [batchId]);

    return data;
}
