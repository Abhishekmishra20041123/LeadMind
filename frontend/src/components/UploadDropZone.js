import { useState } from "react";

export function MultiUploadDropZone({ files, setFiles }) {
    const [dragActive, setDragActive] = useState(false);

    const handleDrag = function (e) {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };

    const handleDrop = function (e) {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            setFiles([...files, ...Array.from(e.dataTransfer.files)]);
        }
    };

    const handleChange = function (e) {
        if (e.target.files && e.target.files.length > 0) {
            setFiles([...files, ...Array.from(e.target.files)]);
        }
    };

    const removeFile = (index) => {
        const newFiles = [...files];
        newFiles.splice(index, 1);
        setFiles(newFiles);
    };

    return (
        <div className="relative group flex flex-col gap-4">
            <div
                className={`h-[150px] w-full border-2 border-dashed ${dragActive ? "border-primary bg-primary/5" : "border-ink/40 bg-mute/50"
                    } relative flex flex-col items-center justify-center transition-all duration-300 hover:border-primary hover:bg-white group-hover:shadow-inner cursor-pointer`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
            >
                {/* Hatch Background Pattern Simulation */}
                <div className="absolute inset-0 opacity-20 pointer-events-none" style={{ backgroundImage: "repeating-linear-gradient(45deg, #0A0A0A 0, #0A0A0A 1px, transparent 0, transparent 10px)" }}></div>

                <div className="flex flex-col items-center justify-center gap-2 bg-paper/90 p-4 border border-ink shadow-sm z-10 backdrop-blur-sm w-full max-w-sm text-center">
                    <span className={`material-symbols-outlined text-3xl ${dragActive ? "text-primary" : "text-ink"}`}>upload_file</span>
                    <h2 className="font-display text-lg font-bold text-ink uppercase tracking-tight">Drop Universal Data (CSV)</h2>
                    <label className="font-mono text-[10px] border border-ink px-3 py-1 hover:bg-ink hover:text-paper transition-colors uppercase cursor-pointer">
                        Select Multiple Files
                        <input
                            type="file"
                            className="hidden"
                            accept=".csv"
                            multiple
                            onChange={handleChange}
                            onClick={(e) => { e.target.value = null; }}
                        />
                    </label>
                </div>
            </div>

            {/* List selected files */}
            {files.length > 0 && (
                <div className="flex flex-col gap-2 mt-4 bg-paper border border-ink p-4">
                    <h3 className="font-mono text-xs font-bold uppercase border-b border-ink pb-2 mb-2">Staged Files ({files.length})</h3>
                    {files.map((f, i) => (
                        <div key={i} className="flex items-center justify-between text-xs font-mono bg-mute/30 p-2 border-l-2 border-primary">
                            <span>{f.name} ({(f.size / 1024).toFixed(1)} KB)</span>
                            <button onClick={() => removeFile(i)} className="text-red-500 hover:text-red-700">
                                <span className="material-symbols-outlined text-[14px]">close</span>
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
