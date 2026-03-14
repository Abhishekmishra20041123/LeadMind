const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";

export async function uploadBatch(files, startIndex = null, endIndex = null) {
    const formData = new FormData();

    if (files.agentMapping) formData.append("agent_mapping", files.agentMapping);
    if (files.crmPipeline) formData.append("crm_pipeline", files.crmPipeline);
    if (files.emailLogs) formData.append("email_logs", files.emailLogs);
    if (files.leadsData) formData.append("leads_data", files.leadsData);
    if (files.salesPipeline) formData.append("sales_pipeline", files.salesPipeline);

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

export async function uploadSmartBatch(leadsFile, leadsMapping, emailsFile, emailsMapping, startIndex = null, endIndex = null) {
    const formData = new FormData();

    formData.append("leads_file", leadsFile);
    formData.append("leads_mapping", JSON.stringify(leadsMapping));
    
    if (emailsFile && emailsMapping) {
        formData.append("emails_file", emailsFile);
        formData.append("emails_mapping", JSON.stringify(emailsMapping));
    }

    // Add optional range parameters
    if (startIndex !== null && startIndex !== "") formData.append("start_index", startIndex);
    if (endIndex !== null && endIndex !== "") formData.append("end_index", endIndex);

    const token = localStorage.getItem("access_token");

    const res = await fetch(`${API}/batch/upload-smart`, {
        method: "POST",
        headers: {
            "Authorization": `Bearer ${token}`,
        },
        body: formData,
    });

    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Smart Upload rejected by server");
    }

    return res.json();
}
