import React, { useState } from 'react';
import { motion } from 'framer-motion';

export default function Navbar({
  onRunQuery,
  onSimulateFailure,
  status,
  totalTokens,
  promptTokens,
  completionTokens,
  totalCost,
  executionTime,
  isRunning,
  connected,
  apiModel,
  apiProvider,
  thinkingMessage,
}) {
  const [query, setQuery] = useState('');

  const handleRun = () => {
    if (query.trim() && !isRunning) {
      onRunQuery(query.trim());
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleRun();
  };

  return (
    <motion.nav
      initial={{ y: -60, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
      className="glass-card flex items-center gap-3 px-4 py-2.5 mx-3 mt-3 mb-2"
      style={{ borderRadius: '14px' }}
    >
      {/* Logo */}
      <div className="flex items-center gap-2 mr-2 shrink-0">
        <div className="w-8 h-8 rounded-lg bg-av-primary flex items-center justify-center glow-primary">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round">
            <circle cx="12" cy="12" r="3"/>
            <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/>
          </svg>
        </div>
        <span className="text-base font-semibold text-white tracking-tight whitespace-nowrap">
          AgentVision <span className="text-av-primary">X</span>
        </span>
      </div>

      {/* Query Input */}
      <div className="flex-1 relative">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything... (e.g., Explain quantum computing)"
          className="w-full bg-av-bg/60 border border-av-border rounded-lg px-4 py-2 text-sm text-av-text placeholder-av-muted focus:outline-none focus:border-av-primary/50 focus:ring-1 focus:ring-av-primary/30 transition-all"
        />
        {/* Live thinking message under input */}
        {isRunning && thinkingMessage && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="absolute -bottom-5 left-1 text-[10px] text-av-primary/70 truncate max-w-full"
          >
            💭 {thinkingMessage}
          </motion.div>
        )}
      </div>

      {/* Run Button */}
      <motion.button
        whileHover={{ scale: 1.03, y: -1 }}
        whileTap={{ scale: 0.97 }}
        onClick={handleRun}
        disabled={isRunning || !query.trim()}
        className={`px-5 py-2 rounded-lg text-sm font-medium transition-all shrink-0 ${
          isRunning
            ? 'bg-av-warning/20 text-av-warning cursor-wait'
            : 'bg-av-primary text-white hover:bg-av-primary/90 glow-primary'
        } disabled:opacity-50 disabled:cursor-not-allowed`}
      >
        {isRunning ? (
          <span className="flex items-center gap-2">
            <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" fill="none" opacity="0.3"/>
              <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" fill="none" strokeLinecap="round"/>
            </svg>
            Running…
          </span>
        ) : (
          '▶ Run Agent'
        )}
      </motion.button>

      {/* Simulate Failure */}
      <motion.button
        whileHover={{ scale: 1.03, y: -1 }}
        whileTap={{ scale: 0.97 }}
        onClick={onSimulateFailure}
        disabled={isRunning}
        className="px-3 py-2 rounded-lg text-xs font-medium bg-av-error/15 text-av-error border border-av-error/20 hover:bg-av-error/25 transition-all shrink-0 disabled:opacity-40"
      >
        ⚡ Simulate Failure
      </motion.button>

      {/* Divider */}
      <div className="w-px h-8 bg-av-border shrink-0" />

      {/* Status */}
      <div className="flex items-center gap-1.5 shrink-0">
        <div className={`w-2 h-2 rounded-full ${
          isRunning ? 'bg-av-warning animate-pulse' :
          connected ? 'bg-av-success' : 'bg-av-error'
        }`} />
        <span className="text-xs text-av-muted whitespace-nowrap">
          {isRunning ? 'Agent Active' : connected ? 'Connected' : 'Offline'}
        </span>
      </div>

      {/* Model badge */}
      {apiModel && (
        <div className="shrink-0 px-2 py-0.5 rounded bg-av-primary/10 border border-av-primary/20 flex items-center gap-1.5">
          {apiProvider && (
            <span className="text-[10px] font-mono text-av-muted">{apiProvider} /</span>
          )}
          <span className="text-[10px] font-mono text-av-primary">{apiModel}</span>
        </div>
      )}

      {/* Metrics — REAL values from API */}
      <div className="flex items-center gap-3 shrink-0">
        <div className="text-center" title={`Prompt: ${promptTokens} | Completion: ${completionTokens}`}>
          <div className="text-[10px] text-av-muted uppercase tracking-wider">Tokens</div>
          <div className="text-xs font-mono text-av-text">{totalTokens.toLocaleString()}</div>
        </div>
        <div className="text-center">
          <div className="text-[10px] text-av-muted uppercase tracking-wider">Cost</div>
          <div className="text-xs font-mono text-av-success">${totalCost.toFixed(6)}</div>
        </div>
        <div className="text-center">
          <div className="text-[10px] text-av-muted uppercase tracking-wider">Time</div>
          <div className="text-xs font-mono text-av-text">{executionTime.toFixed(1)}s</div>
        </div>
      </div>
    </motion.nav>
  );
}
