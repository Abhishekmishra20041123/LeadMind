const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";

export async function getSmartUploadSchema() {
    const token = localStorage.getItem("access_token");

    const res = await fetch(`${API}/smart-upload/schema`, {
        method: "GET",
        headers: {
            "Authorization": `Bearer ${token}`,
        }
    });

    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to fetch schema");
    }

    return res.json();
}

export async function analyzeCsv(file, fileType) {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("file_type", fileType); // "leads" or "emails"

    const token = localStorage.getItem("access_token");

    const res = await fetch(`${API}/smart-upload/analyze`, {
        method: "POST",
        headers: {
            "Authorization": `Bearer ${token}`,
        },
        body: formData,
    });

    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Analysis rejected by server");
    }

    return res.json();
}
