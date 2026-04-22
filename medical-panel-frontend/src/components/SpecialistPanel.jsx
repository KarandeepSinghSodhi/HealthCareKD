import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const ICONS = {
    cmo: '🩺',
    cardiologist: '❤️',
    dermatologist: '🌸',
    neurologist: '🧠',
    orthopedist: '🦴',
    gastroenterologist: '🫁',
    pediatrician: '👶',
    psychiatrist: '🧘',
    allergist: '🌿',
};

export default function SpecialistPanel({ specialists }) {
    const displayed = specialists;  // Show all specialists since all respond now
    const specCount = displayed.length;

    return (
        <div className="sidebar">
            {/* Header */}
            <div style={{
                padding: '18px 16px 14px',
                borderBottom: '1px solid rgba(255,255,255,0.06)',
            }}>
                <p style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'rgba(255,255,255,0.28)', marginBottom: 4 }}>
                    Active Panel
                </p>
                <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.18)' }}>
                    {specCount} specialist{specCount !== 1 ? 's' : ''} evaluating
                </p>
            </div>

            {/* Specialist list */}
            <div className="scrollbar-none" style={{ flex: 1, overflowY: 'auto', padding: '10px 8px' }}>
                <AnimatePresence mode="popLayout">
                    {displayed.map((spec) => {
                        return (
                            <motion.div
                                key={spec.id}
                                layout
                                initial={{ opacity: 0, x: -14 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -20, scale: 0.85, filter: 'blur(3px)', transition: { duration: 0.3 } }}
                                transition={{ type: 'spring', stiffness: 280, damping: 26 }}
                                className="accent-transition"
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 10,
                                    padding: '8px 10px',
                                    borderRadius: 12,
                                    marginBottom: 4,
                                    cursor: 'default',
                                    background: 'transparent',
                                }}
                            >
                                {/* Avatar */}
                                <div className="spec-avatar" style={{
                                    background: 'rgba(255,255,255,0.07)',
                                    border: '1px solid rgba(255,255,255,0.08)',
                                }}>
                                    <img
                                        src={`/avatars/${spec.avatar}`}
                                        alt={spec.name}
                                        onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex'; }}
                                    />
                                    <span style={{
                                        display: 'none',
                                        position: 'absolute', inset: 0,
                                        alignItems: 'center', justifyContent: 'center',
                                        fontSize: 16,
                                    }}>
                                        {ICONS[spec.id] || '👨‍⚕️'}
                                    </span>
                                    {/* Online dot */}
                                    <span style={{
                                        position: 'absolute', bottom: 0, right: 0,
                                        width: 9, height: 9, borderRadius: '50%',
                                        background: '#22c55e',
                                        border: '2px solid #111',
                                    }} />
                                </div>

                                {/* Text */}
                                <div style={{ minWidth: 0 }}>
                                    <p className="accent-transition" style={{
                                        fontSize: 13,
                                        fontWeight: 500,
                                        color: 'rgba(255,255,255,0.78)',
                                        overflow: 'hidden',
                                        whiteSpace: 'nowrap',
                                        textOverflow: 'ellipsis',
                                    }}>
                                        {spec.name}
                                    </p>
                                    <p style={{ fontSize: 10, color: 'rgba(255,255,255,0.28)', marginTop: 1 }}>
                                        {spec.id === 'cmo' ? 'Primary Care' : 'Specialist'}
                                    </p>
                                </div>
                            </motion.div>
                        );
                    })}
                </AnimatePresence>
            </div>

            {/* Footer */}
            <div style={{ padding: '12px 16px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                <p style={{ fontSize: 10, color: 'rgba(255,255,255,0.18)', lineHeight: 1.5 }}>
                    Doctors leave as your case narrows.
                </p>
            </div>
        </div>
    );
}
