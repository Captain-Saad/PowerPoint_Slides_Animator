import { Settings2 } from 'lucide-react';

interface ProfileSelectorProps {
    profile: string;
    setProfile: (profile: string) => void;
    disabled: boolean;
}

const PROFILES = [
    { id: 'subtle', name: 'Subtle', desc: 'Minimal fades, professional and formal.' },
    { id: 'balanced', name: 'Balanced', desc: 'Wipes and fades. The safest default.' },
    { id: 'dynamic', name: 'Dynamic', desc: 'Fast, energetic, high impact.' },
];

export default function ProfileSelector({ profile, setProfile, disabled }: ProfileSelectorProps) {
    return (
        <div className="w-full mt-8">
            <div className="flex items-center space-x-2 mb-4">
                <Settings2 className="w-5 h-5 text-primary" />
                <h3 className="text-lg font-semibold text-white/90">Animation Profile</h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {PROFILES.map((p) => (
                    <button
                        key={p.id}
                        disabled={disabled}
                        onClick={() => setProfile(p.id)}
                        className={`relative p-4 rounded-2xl border text-left transition-all duration-300 ${profile === p.id
                                ? 'bg-primary/20 border-primary shadow-[0_0_15px_rgba(79,70,229,0.3)]'
                                : 'bg-white/5 border-white/10 hover:border-white/30 cursor-pointer'
                            } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                        {profile === p.id && (
                            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary to-pink-500 rounded-t-2xl"></div>
                        )}
                        <h4 className={`font-bold mb-1 ${profile === p.id ? 'text-white' : 'text-white/70'}`}>
                            {p.name}
                        </h4>
                        <p className="text-xs text-textMuted leading-relaxed">
                            {p.desc}
                        </p>
                    </button>
                ))}
            </div>
        </div>
    );
}
