import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';

interface ProcessingOverlayProps {
    isProcessing: boolean;
}

export default function ProcessingOverlay({ isProcessing }: ProcessingOverlayProps) {
    if (!isProcessing) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-md">
            <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                className="glass-panel p-10 flex flex-col items-center max-w-sm w-full mx-4"
            >
                <div className="relative mb-8">
                    {/* Animated Blob Background */}
                    <div className="absolute -inset-4 bg-primary/30 rounded-full blur-xl animate-pulse-slow"></div>
                    {/* Spinner */}
                    <Loader2 className="w-16 h-16 text-primary animate-spin relative z-10" />
                </div>

                <h3 className="text-2xl font-bold text-white mb-2 text-center">Animating Engine</h3>
                <p className="text-textMuted text-center text-sm">
                    Please wait while PPTX Animator builds the OOXML timeline for your massive decks. This might take a few seconds...
                </p>

                {/* Progress Bar Mock */}
                <div className="w-full h-2 bg-white/10 rounded-full mt-8 overflow-hidden">
                    <motion.div
                        className="h-full bg-gradient-to-r from-primary to-pink-500 rounded-full"
                        initial={{ width: "0%" }}
                        animate={{ width: "90%" }}
                        transition={{ duration: 15, ease: "easeOut" }}
                    />
                </div>
            </motion.div>
        </div>
    );
}
