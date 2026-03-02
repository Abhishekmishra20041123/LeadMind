const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export async function fetchLeads(page = 1, pageSize = 25, params = {}) {
    const query = new URLSearchParams({
        page,
        page_size: pageSize
    });

    if (params.batchId) query.append('batch_id', params.batchId);
    if (params.search) query.append('search', params.search);
    if (params.minScore) query.append('min_score', params.minScore);
    if (params.maxScore) query.append('max_score', params.maxScore);

    const token = localStorage.getItem("access_token");
    const res = await fetch(`${API}/leads?${query.toString()}`, {
        headers: {
            "Authorization": `Bearer ${token}`
        }
    });
    if (!res.ok) throw new Error("Failed to fetch leads");
    return res.json();
}
