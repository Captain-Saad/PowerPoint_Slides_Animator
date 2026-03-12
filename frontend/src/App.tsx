import { useState } from 'react';
import { Sparkles, DownloadCloud, AlertCircle } from 'lucide-react';
import Dropzone from './components/Dropzone';
import ProfileSelector from './components/ProfileSelector';
import ProcessingOverlay from './components/ProcessingOverlay';

function App() {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [profile, setProfile] = useState<string>('balanced');
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFilesSelected = (files: File[]) => {
    // Append new files
    setSelectedFiles(prev => {
      const existingNames = new Set(prev.map(f => f.name));
      const newFiles = files.filter(f => !existingNames.has(f.name));
      return [...prev, ...newFiles];
    });
    setError(null);
  };

  const handleRemoveFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
    if (selectedFiles.length <= 1) setError(null);
  };

  const handleAnimate = async () => {
    if (selectedFiles.length === 0) {
      setError("Please select at least one PowerPoint file.");
      return;
    }

    setIsProcessing(true);
    setError(null);

    const formData = new FormData();
    selectedFiles.forEach(file => {
      formData.append('files', file);
    });
    formData.append('profile', profile);

    try {
      const response = await fetch('http://localhost:5000/api/animate', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        let errMessage = 'An error occurred during animation.';
        try {
          const errData = await response.json();
          if (errData.error) errMessage = errData.error;
        } catch {
          // keep default message
        }
        throw new Error(errMessage);
      }

      // Handle the blob download (can be .pptx or .zip)
      const blob = await response.blob();

      // Determine file name from headers if possible, or default to generic names
      let filename = selectedFiles.length > 1 ? 'animated_presentations.zip' : selectedFiles[0].name.replace('.pptx', '_animated.pptx');
      const disposition = response.headers.get('Content-Disposition');
      if (disposition && disposition.includes('filename=')) {
        filename = disposition.split('filename=')[1].replace(/"/g, '');
      }

      // Trigger download
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();

      // Reset state for next use
      setSelectedFiles([]);
    } catch (err: any) {
      setError(err.message || 'Failed to connect to the backend server.');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="relative min-h-screen pt-20 pb-12 overflow-hidden bg-background">
      {/* Background aesthetic blobs */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-primary/20 rounded-full blur-[120px] mix-blend-screen animate-blob"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-pink-500/20 rounded-full blur-[120px] mix-blend-screen animate-blob animation-delay-2000"></div>
      </div>

      <nav className="fixed top-0 w-full z-40 bg-background/50 backdrop-blur-md border-b border-white/5 py-4">
        <div className="max-w-5xl mx-auto px-6 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="bg-primary/20 p-2 rounded-lg">
              <Sparkles className="w-5 h-5 text-primary" />
            </div>
            <span className="font-bold text-xl tracking-tight text-white">
              PPTX <span className="text-white/50 font-normal">Animator</span>
            </span>
          </div>
          <div className="text-xs font-medium text-white/40 border border-white/10 rounded-full px-3 py-1">
            Engine v1.0
          </div>
        </div>
      </nav>

      <main className="relative z-10 max-w-3xl mx-auto px-6 pt-16">
        <div className="text-center mb-12 animate-fade-in">
          <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight mb-4">
            Breathe life into your
            <span className="block text-transparent bg-clip-text bg-gradient-to-r from-[#4F46E5] to-[#EC4899] drop-shadow-sm mt-1">
              presentations.
            </span>
          </h1>
          <p className="text-lg text-textMuted max-w-xl mx-auto leading-relaxed">
            Upload your decks. We intelligently inject precise, professional OOXML timelines to make your slides animate automatically.
          </p>
        </div>

        <div className="space-y-6 animate-slide-up">
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-center space-x-3 text-red-200 backdrop-blur-sm">
              <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
              <p className="text-sm font-medium">{error}</p>
            </div>
          )}

          <Dropzone
            onFilesSelected={handleFilesSelected}
            selectedFiles={selectedFiles}
            onRemoveFile={handleRemoveFile}
          />

          <ProfileSelector
            profile={profile}
            setProfile={setProfile}
            disabled={isProcessing}
          />

          <div className="pt-8 flex justify-center">
            <button
              onClick={handleAnimate}
              disabled={selectedFiles.length === 0 || isProcessing}
              className="btn-primary w-full md:w-auto md:px-16"
            >
              <DownloadCloud className="w-5 h-5 mr-3" />
              <span className="text-lg tracking-wide">
                {selectedFiles.length > 1 ? `Animate All ${selectedFiles.length} Files` : 'Animate Presentation'}
              </span>
            </button>
          </div>
        </div>
      </main>

      <ProcessingOverlay isProcessing={isProcessing} />
    </div>
  );
}

export default App;
