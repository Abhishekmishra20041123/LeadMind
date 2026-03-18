const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";

export async function uploadBatch(filesArray, startIndex = null, endIndex = null) {
    const formData = new FormData();

    if (filesArray && filesArray.length > 0) {
        filesArray.forEach((file) => formData.append("files", file));
    }

    // Add optional range parameters
    if (startIndex !== null && startIndex !== "") formData.append("start_index", startIndex);
    if (endIndex !== null && endIndex !== "") formData.append("end_index", endIndex);

    const token = localStorage.getItem("access_token");

    const res = await fetch(`${API}/batch/upload`, {
        method: "POST",
        headers: {
            "Authorization": `Bearer ${token}`,
        },
        body: formData,
    });

    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Upload rejected by server");
    }

    return res.json();
}
