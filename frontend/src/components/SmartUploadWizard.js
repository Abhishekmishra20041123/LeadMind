"use client"
import { useState, useRef } from "react"
import { analyzeCsv } from "../api/smart-upload"
import { uploadSmartBatch } from "../api/batch"

export function SmartUploadWizard({ onUploadSuccess }) {
    const [step, setStep] = useState(1) // 1: Files, 2: Mappings, 3: Launch
    const [status, setStatus] = useState("idle") // idle, analyzing, uploading, error
    const [errorMsg, setErrorMsg] = useState("")
    
    // Files
    const [leadsFile, setLeadsFile] = useState(null)
    const [emailsFile, setEmailsFile] = useState(null)
    
    // Limits
    const [startIndex, setStartIndex] = useState("")
    const [endIndex, setEndIndex] = useState("")

    // Mappings
    const leadsInputRef = useRef(null)
    const emailsInputRef = useRef(null)
    
    const [leadsMapping, setLeadsMapping] = useState({})
    const [emailsMapping, setEmailsMapping] = useState({})
    
    const [leadsHeaders, setLeadsHeaders] = useState([])
    const [emailsHeaders, setEmailsHeaders] = useState([])
    
    // Schema Defs for Dropdowns
    const leadsSchemaOpts = [
        "name", "company", "title", "email", "industry", "region", 
        "website_visits", "pages_per_visit", "time_on_site", "content_downloads", 
        "lead_source", "converted", "stage"
    ]
    const emailsSchemaOpts = [
        "subject", "email_text", "opened", "replied", "click_count", 
        "email_type", "response_status"
    ]

    const handleFileChange = (e, type) => {
        const file = e.target.files[0]
        if (type === "leads") setLeadsFile(file)
        if (type === "emails") setEmailsFile(file)
    }

    const doAnalysis = async () => {
        if (!leadsFile) {
            setErrorMsg("Leads Data file is required.")
            return
        }
        
        setErrorMsg("")
        setStatus("analyzing")
        
        try {
            const leadsRes = await analyzeCsv(leadsFile, "leads")
            setLeadsMapping(leadsRes.mapping)
            setLeadsHeaders(leadsRes.headers)
            
            if (emailsFile) {
                const emailsRes = await analyzeCsv(emailsFile, "emails")
                setEmailsMapping(emailsRes.mapping)
                setEmailsHeaders(emailsRes.headers)
            }
            
            setStep(2)
            setStatus("idle")
        } catch (err) {
            setErrorMsg(err.message || "Analysis failed")
            setStatus("error")
        }
    }

    const doUpload = async () => {
        setErrorMsg("")
        setStatus("uploading")
        
        try {
            const result = await uploadSmartBatch(
                leadsFile, leadsMapping,
                emailsFile, emailsMapping,
                startIndex, endIndex
            )
            setStatus("success")
            if(onUploadSuccess) onUploadSuccess(result.batch_id)
        } catch (err) {
            setErrorMsg(err.message || "Upload failed")
            setStatus("error")
        }
    }

    const renderMappingTable = (headers, mapping, setMapping, schemaOpts, title) => (
        <div className="border border-ink p-4 mb-4">
            <h3 className="font-mono text-sm font-bold uppercase mb-4 text-ink border-l-4 border-primary pl-3">
                {title} Mappings
            </h3>
            <div className="grid grid-cols-2 gap-4 border-b border-ink/20 pb-2 mb-2 font-mono text-xs text-ink/60 uppercase font-bold">
                <div>Your Column</div>
                <div>System Field</div>
            </div>
            <div className="max-h-48 overflow-y-auto pr-2 flex flex-col gap-2">
                {headers.map(h => (
                    <div key={h} className="grid grid-cols-2 gap-4 items-center">
                        <div className="font-mono text-sm truncate" title={h}>{h}</div>
                        <select 
                            className="p-1 border border-ink/30 bg-paper font-mono text-xs w-full focus:outline-none focus:border-ink"
                            value={mapping[h] || ""}
                            onChange={(e) => {
                                const val = e.target.value
                                setMapping(prev => {
                                    const next = {...prev}
                                    if(val) next[h] = val
                                    else delete next[h]
                                    return next
                                })
                            }}
                        >
                            <option value="">-- Ignore --</option>
                            {schemaOpts.map(opt => (
                                <option key={opt} value={opt}>{opt}</option>
                            ))}
                        </select>
                    </div>
                ))}
            </div>
        </div>
    )

    return (
        <div className="flex flex-col gap-6">
            
            {/* Steps Guide */}
            <div className="flex items-center gap-2 border-b border-ink/20 pb-4 font-mono text-xs uppercase">
                <div className={`px-2 py-1 ${step >= 1 ? 'bg-primary text-paper' : 'bg-ink/10 text-ink/50'}`}>1. Select Files</div>
                <div className={`px-2 py-1 ${step >= 2 ? 'bg-primary text-paper' : 'bg-ink/10 text-ink/50'}`}>2. Review AI Map</div>
                <div className={`px-2 py-1 ${step >= 3 ? 'bg-primary text-paper' : 'bg-ink/10 text-ink/50'}`}>3. Execute</div>
            </div>

            {errorMsg && (
                <div className="bg-red-100 text-red-800 border border-red-300 p-3 font-mono text-xs">
                    [ERROR]: {errorMsg}
                </div>
            )}

            {step === 1 && (
                <div className="flex flex-col gap-6">
                    <div>
                        <h3 className="font-mono text-sm font-bold uppercase tracking-wider text-ink border-l-4 border-primary pl-3 mb-2">Required: Leads Data</h3>
                        <p className="font-mono text-xs text-ink/60 mb-3">Upload your raw leads CSV. We will map the columns for you.</p>
                        <input type="file" ref={leadsInputRef} accept=".csv" className="hidden" onChange={e => handleFileChange(e, 'leads')} />
                        <button onClick={() => leadsInputRef.current?.click()} className="w-full border-2 border-dashed border-ink/30 p-4 font-mono text-sm hover:border-primary hover:text-primary transition-colors flex items-center gap-3">
                            <span className="material-symbols-outlined">{leadsFile ? 'check_circle' : 'upload_file'}</span>
                            {leadsFile ? leadsFile.name : "Select Leads CSV..."}
                        </button>
                    </div>

                    <div>
                        <h3 className="font-mono text-sm font-bold uppercase tracking-wider text-ink border-l-4 border-primary pl-3 mb-2">Optional: Email History</h3>
                        <p className="font-mono text-xs text-ink/60 mb-3">Upload past email interactions to improve intent scoring & follow-up timing.</p>
                        <input type="file" ref={emailsInputRef} accept=".csv" className="hidden" onChange={e => handleFileChange(e, 'emails')} />
                        <button onClick={() => emailsInputRef.current?.click()} className="w-full border-2 border-dashed border-ink/30 p-4 font-mono text-sm hover:border-primary hover:text-primary transition-colors flex items-center gap-3">
                            <span className="material-symbols-outlined">{emailsFile ? 'check_circle' : 'upload_file'}</span>
                            {emailsFile ? emailsFile.name : "Select Email History CSV (Optional)..."}
                        </button>
                    </div>

                    <button 
                        onClick={doAnalysis}
                        disabled={!leadsFile || status === "analyzing"}
                        className="bg-primary text-paper font-display uppercase font-bold text-lg p-4 flex justify-center items-center gap-2 hover:bg-ink transition-colors disabled:opacity-50 disabled:cursor-not-allowed border-2 border-transparent hover:border-ink"
                    >
                        {status === "analyzing" ? (
                            <><span className="material-symbols-outlined animate-spin">sync</span> Analyzing via Ollama...</>
                        ) : (
                            <>Analyze Columns <span className="material-symbols-outlined">arrow_forward</span></>
                        )}
                    </button>
                </div>
            )}

            {step === 2 && (
                <div className="flex flex-col gap-4">
                    <p className="font-mono text-xs text-ink/60">Ollama has analyzed your CSVs. Please review and adjust the mappings below if needed. Unmapped columns will be ignored.</p>
                    
                    {renderMappingTable(leadsHeaders, leadsMapping, setLeadsMapping, leadsSchemaOpts, "Leads")}
                    
                    {emailsFile && renderMappingTable(emailsHeaders, emailsMapping, setEmailsMapping, emailsSchemaOpts, "Emails")}

                    <div className="flex gap-4">
                        <button onClick={() => setStep(1)} className="border border-ink px-4 py-2 font-mono text-sm uppercase hover:bg-ink hover:text-paper transition-colors">Back</button>
                        <button onClick={() => setStep(3)} className="bg-primary text-paper font-display uppercase font-bold text-lg px-6 py-2 flex-1 hover:bg-ink transition-colors flex justify-center items-center gap-2">Confirm Mappings <span className="material-symbols-outlined">check</span></button>
                    </div>
                </div>
            )}

            {step === 3 && (
                <div className="flex flex-col gap-6">
                    <div>
                        <h3 className="font-mono text-sm font-bold uppercase tracking-wider text-ink border-l-4 border-primary pl-3 mb-2">Optional Range Limits</h3>
                        <p className="font-mono text-xs text-ink/60 mb-3">Limit execution to a subset of the leads database.</p>
                        <div className="flex gap-4">
                            <div className="flex-1 flex flex-col gap-1">
                                <label className="font-mono text-[10px] uppercase font-bold text-ink/60">Start Row</label>
                                <input type="number" value={startIndex} onChange={e => setStartIndex(e.target.value)} className="w-full bg-paper border-b-2 border-ink/20 focus:outline-none focus:border-primary p-2 font-mono text-sm placeholder-ink/30 transition-colors" placeholder="0" />
                            </div>
                            <div className="flex-1 flex flex-col gap-1">
                                <label className="font-mono text-[10px] uppercase font-bold text-ink/60">End Row</label>
                                <input type="number" value={endIndex} onChange={e => setEndIndex(e.target.value)} className="w-full bg-paper border-b-2 border-ink/20 focus:outline-none focus:border-primary p-2 font-mono text-sm placeholder-ink/30 transition-colors" placeholder="All" />
                            </div>
                        </div>
                    </div>

                    <div className="flex gap-4 mt-4">
                        <button onClick={() => setStep(2)} className="border border-ink px-4 py-2 font-mono text-sm uppercase hover:bg-ink hover:text-paper transition-colors" disabled={status === "uploading"}>Back</button>
                        <button 
                            onClick={doUpload}
                            disabled={status === "uploading"}
                            className="bg-primary text-paper font-display uppercase font-bold text-lg px-6 py-3 flex-1 flex justify-center items-center gap-2 hover:bg-ink transition-colors disabled:opacity-50"
                        >
                            {status === "uploading" ? (
                                <><span className="material-symbols-outlined animate-spin">sync</span> Launching Batch Protocol...</>
                            ) : (
                                <>Launch System <span className="material-symbols-outlined">rocket_launch</span></>
                            )}
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}
