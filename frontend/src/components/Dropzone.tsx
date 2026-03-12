import { useState, useRef } from 'react';
import { UploadCloud, FileType, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface DropzoneProps {
    onFilesSelected: (files: File[]) => void;
    selectedFiles: File[];
    onRemoveFile: (index: number) => void;
}

export default function Dropzone({ onFilesSelected, selectedFiles, onRemoveFile }: DropzoneProps) {
    const [isDragActive, setIsDragActive] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);

    const handleDrag = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setIsDragActive(true);
        } else if (e.type === 'dragleave') {
            setIsDragActive(false);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragActive(false);

        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            const validFiles = Array.from(e.dataTransfer.files).filter(file => file.name.endsWith('.pptx'));
            if (validFiles.length > 0) {
                onFilesSelected(validFiles);
            }
        }
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        e.preventDefault();
        if (e.target.files && e.target.files.length > 0) {
            const validFiles = Array.from(e.target.files).filter(file => file.name.endsWith('.pptx'));
            if (validFiles.length > 0) {
                onFilesSelected(validFiles);
            }
        }
    };

    return (
        <div className="w-full">
            <div
                className={`relative glass-panel rounded-3xl p-10 flex flex-col items-center justify-center border-2 border-dashed transition-all duration-300 ease-in-out cursor-pointer group ${isDragActive ? 'border-primary bg-primary/10' : 'border-white/20 hover:border-primary/50 hover:bg-white/10'
                    }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => inputRef.current?.click()}
            >
                <input
                    ref={inputRef}
                    type="file"
                    multiple
                    accept=".pptx,application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    onChange={handleChange}
                    className="hidden"
                />

                <div className="bg-primary/20 p-5 rounded-full mb-6 group-hover:scale-110 transition-transform duration-300">
                    <UploadCloud className="w-12 h-12 text-primary drop-shadow-[0_0_15px_rgba(79,70,229,0.8)]" />
                </div>

                <h3 className="text-2xl font-bold mb-2 tracking-tight text-white/90">
                    {isDragActive ? 'Drop files here' : 'Drag & Drop your .pptx files'}
                </h3>
                <p className="text-textMuted text-center max-w-sm">
                    Select one or multiple PowerPoint files to animate them instantly using our intelligent rules engine.
                </p>
            </div>

            <AnimatePresence>
                {selectedFiles.length > 0 && (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mt-6 space-y-3"
                    >
                        <h4 className="text-sm font-semibold uppercase tracking-wider text-textMuted mb-2">Selected Files ({selectedFiles.length})</h4>
                        <div className="max-h-60 overflow-y-auto pr-2 space-y-2">
                            {selectedFiles.map((file, idx) => (
                                <motion.div
                                    key={`${file.name}-${idx}`}
                                    initial={{ opacity: 0, x: -20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: idx * 0.05 }}
                                    className="flex items-center justify-between bg-white/5 border border-white/10 p-3 rounded-xl backdrop-blur-sm hover:bg-white/10 transition-colors"
                                >
                                    <div className="flex items-center space-x-3 truncate">
                                        <div className="bg-blue-500/20 p-2 rounded-lg">
                                            <FileType className="w-5 h-5 text-blue-400" />
                                        </div>
                                        <span className="truncate text-sm font-medium text-white/80">{file.name}</span>
                                    </div>
                                    <button
                                        onClick={(e) => { e.stopPropagation(); onRemoveFile(idx); }}
                                        className="p-1 hover:bg-red-500/20 rounded-md transition-colors group"
                                    >
                                        <X className="w-5 h-5 text-textMuted group-hover:text-red-400" />
                                    </button>
                                </motion.div>
                            ))}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
