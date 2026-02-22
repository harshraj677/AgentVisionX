import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const statusConfig = {
  waiting: { color: '#9CA3AF', bg: '#374151', label: 'Waiting' },
  running: { color: '#F59E0B', bg: '#78350F', label: 'Running' },
  success: { color: '#22C55E', bg: '#064E3B', label: 'Success' },
  error: { color: '#EF4444', bg: '#7F1D1D', label: 'Error' },
};

export default function StepInspector({ step, onRerunStep, onClose }) {
  if (!step) {
    return (
      <div className="glass-card h-full flex flex-col overflow-hidden" style={{ borderRadius: '14px' }}>
        <div className="flex items-center px-4 py-2.5 border-b border-av-border">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-av-warning/60" />
            <span className="text-xs font-semibold uppercase tracking-wider text-av-muted">
              Step Inspector
            </span>
          </div>
        </div>
        <div className="flex-1 flex items-center justify-center text-av-muted text-sm">
          <div className="text-center">
            <div className="text-3xl mb-2 opacity-20">🔍</div>
            <div>Click a node to inspect</div>
          </div>
        </div>
      </div>
    );
  }

  const sc = statusConfig[step.status] || statusConfig.waiting;

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3 }}
      className="glass-card h-full flex flex-col overflow-hidden"
      style={{ borderRadius: '14px' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-av-border shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: sc.color }} />
          <span className="text-xs font-semibold uppercase tracking-wider text-av-muted">
            Step Inspector
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onRerunStep?.(step.id)}
            className="text-[10px] px-2 py-1 rounded bg-av-primary/20 text-av-primary hover:bg-av-primary/30 transition-all"
          >
            ↻ Re-run
          </button>
          <button
            onClick={onClose}
            className="text-av-muted hover:text-white transition-colors text-sm"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
        {/* Step Name + Status */}
        <div className="glass-card-sm p-3">
          <div className="text-xs text-av-muted mb-1 uppercase tracking-wider">Step Name</div>
          <div className="text-sm font-semibold text-white">{step.name}</div>
          <div className="flex items-center gap-2 mt-2">
            <span
              className="text-[10px] px-2 py-0.5 rounded-full font-medium uppercase"
              style={{ backgroundColor: sc.bg, color: sc.color, border: `1px solid ${sc.color}30` }}
            >
              {sc.label}
            </span>
            {step.order !== undefined && (
              <span className="text-[10px] text-av-muted">Step #{step.order + 1}</span>
            )}
          </div>
        </div>

        {/* Description */}
        {step.description && (
          <div className="glass-card-sm p-3">
            <div className="text-xs text-av-muted mb-1 uppercase tracking-wider">Description</div>
            <div className="text-xs text-av-text">{step.description}</div>
          </div>
        )}

        {/* Prompt */}
        <div className="glass-card-sm p-3">
          <div className="text-xs text-av-muted mb-1 uppercase tracking-wider">Prompt</div>
          <div className="text-xs font-mono text-av-text bg-av-bg/50 rounded p-2 max-h-24 overflow-y-auto">
            {step.prompt || '—'}
          </div>
        </div>

        {/* Input */}
        <div className="glass-card-sm p-3">
          <div className="text-xs text-av-muted mb-1 uppercase tracking-wider">Input</div>
          <div className="text-xs font-mono text-av-text bg-av-bg/50 rounded p-2 max-h-20 overflow-y-auto">
            {step.input_data || '—'}
          </div>
        </div>

        {/* Output */}
        <div className="glass-card-sm p-3">
          <div className="text-xs text-av-muted mb-1 uppercase tracking-wider">Output</div>
          <div className="text-xs font-mono text-av-text bg-av-bg/50 rounded p-2 max-h-32 overflow-y-auto whitespace-pre-wrap">
            {step.output_data || '—'}
          </div>
        </div>

        {/* Reasoning */}
        {step.reasoning && (
          <div className="glass-card-sm p-3">
            <div className="text-xs text-av-muted mb-1 uppercase tracking-wider">Reasoning</div>
            <div className="text-xs text-av-text">{step.reasoning}</div>
          </div>
        )}

        {/* Metrics */}
        <div className="glass-card-sm p-3">
          <div className="text-xs text-av-muted mb-2 uppercase tracking-wider">Metrics</div>
          <div className="grid grid-cols-3 gap-2">
            <div className="text-center p-2 rounded bg-av-bg/50">
              <div className="text-[10px] text-av-muted">Tokens</div>
              <div className="text-sm font-mono font-semibold text-av-primary">{step.tokens || 0}</div>
            </div>
            <div className="text-center p-2 rounded bg-av-bg/50">
              <div className="text-[10px] text-av-muted">Time</div>
              <div className="text-sm font-mono font-semibold text-av-warning">
                {step.execution_time ? `${step.execution_time.toFixed(1)}s` : '—'}
              </div>
            </div>
            <div className="text-center p-2 rounded bg-av-bg/50">
              <div className="text-[10px] text-av-muted">Cost</div>
              <div className="text-sm font-mono font-semibold text-av-success">
                {(() => {
                  if (step.reasoning && step.reasoning.includes('cost=')) {
                    const m = step.reasoning.match(/cost=([\d.]+)/);
                    if (m) return `$${parseFloat(m[1]).toFixed(6)}`;
                  }
                  return step.tokens > 0 ? `$${(step.tokens * 0.0000006).toFixed(6)}` : '$0.000000';
                })()}
              </div>
            </div>
          </div>
        </div>

        {/* Timestamp */}
        <div className="glass-card-sm p-3">
          <div className="text-xs text-av-muted mb-1 uppercase tracking-wider">Timestamp</div>
          <div className="text-xs font-mono text-av-text">{step.timestamp || '—'}</div>
        </div>
      </div>
    </motion.div>
  );
}
