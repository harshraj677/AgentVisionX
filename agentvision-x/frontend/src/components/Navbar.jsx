import React, { useState } from 'react';
import { motion } from 'framer-motion';

const MODEL_OPTIONS = [
  { value: 'puter',        label: '✨ Puter.js (Free)',          sub: 'GPT-4o Mini • No key needed' },
  { value: 'sambanova',    label: '🧠 DeepSeek R1 70B',        sub: 'SambaNova • Free & fast' },
  { value: 'openrouter',   label: '🌐 OpenRouter',              sub: 'DeepSeek Chat • Configurable' },
  { value: 'gemini-flash', label: '🔵 Gemini Flash',            sub: 'Requires GEMINI_API_KEY' },
  { value: 'groq',         label: '⚡ Groq — LLaMA 3.3',        sub: 'Requires GROQ_API_KEY' },
];

export default function Navbar({
  onRunQuery,
  onSimulateFailure,
  status,
  totalTokens,
  promptTokens,
  completionTokens,
  thinkingTokens = 0,
  totalCost,
  executionTime,
  isRunning,
  connected,
  apiModel,
  apiProvider,
  thinkingMessage,
}) {
  const [query, setQuery] = useState('');
  const [selectedModel, setSelectedModel] = useState('puter');
  const [showModelMenu, setShowModelMenu] = useState(false);

  const currentModel = MODEL_OPTIONS.find(m => m.value === selectedModel) || MODEL_OPTIONS[0];

  const handleRun = () => {
    if (query.trim() && !isRunning) {
      onRunQuery(query.trim(), selectedModel);
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
      className="glass-card flex items-center gap-2 px-4 py-2.5 mx-3 mt-3 mb-2 relative z-50"
      style={{ borderRadius: '14px' }}
    >
      {/* Logo */}
      <div className="flex items-center gap-2 shrink-0">
        <div className="w-8 h-8 rounded-lg bg-av-primary flex items-center justify-center glow-primary">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round">
            <circle cx="12" cy="12" r="3"/>
            <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/>
          </svg>
        </div>
        <span className="text-sm font-semibold text-white tracking-tight whitespace-nowrap hidden xl:inline">
          AgentVision <span className="text-av-primary">X</span>
        </span>
      </div>

      {/* Model Selector */}
      <div className="relative shrink-0">
        <button
          onClick={() => setShowModelMenu(v => !v)}
          className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-xs font-medium bg-av-bg/60 border border-av-border hover:border-av-primary/50 transition-all"
        >
          <span className="whitespace-nowrap">{currentModel.label}</span>
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M6 9l6 6 6-6"/>
          </svg>
        </button>
        {showModelMenu && (
          <div
            className="absolute top-full left-0 mt-1 w-52 rounded-xl bg-[#0f1117] border border-av-border shadow-2xl z-[999]"
            onMouseLeave={() => setShowModelMenu(false)}
          >
            {MODEL_OPTIONS.map(opt => (
              <button
                key={opt.value}
                onClick={() => { setSelectedModel(opt.value); setShowModelMenu(false); }}
                className={`w-full text-left px-3 py-2.5 text-xs transition-colors hover:bg-av-primary/10 ${
                  opt.value === selectedModel ? 'text-av-primary bg-av-primary/5' : 'text-av-text'
                } first:rounded-t-xl last:rounded-b-xl`}
              >
                <div className="font-medium">{opt.label}</div>
                <div className="text-[10px] text-av-muted mt-0.5">{opt.sub}</div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Query Input — guaranteed minimum width so it never collapses */}
      <div className="flex-1 min-w-[180px] relative">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything... (e.g., What is the full form of ROM?)"
          className="w-full bg-av-bg/60 border border-av-border rounded-lg px-3 py-2 text-sm text-av-text placeholder-av-muted focus:outline-none focus:border-av-primary/50 focus:ring-1 focus:ring-av-primary/30 transition-all"
        />
      </div>

      {/* Run Button */}
      <motion.button
        whileHover={{ scale: 1.03, y: -1 }}
        whileTap={{ scale: 0.97 }}
        onClick={handleRun}
        disabled={isRunning || !query.trim()}
        className={`px-4 py-2 rounded-lg text-sm font-medium transition-all shrink-0 ${
          isRunning
            ? 'bg-av-warning/20 text-av-warning cursor-wait'
            : 'bg-av-primary text-white hover:bg-av-primary/90 glow-primary'
        } disabled:opacity-50 disabled:cursor-not-allowed`}
      >
        {isRunning ? (
          <span className="flex items-center gap-1.5">
            <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" fill="none" opacity="0.3"/>
              <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" fill="none" strokeLinecap="round"/>
            </svg>
            Running…
          </span>
        ) : (
          '▶ Run'
        )}
      </motion.button>

      {/* Simulate Failure — hide when running to save space */}
      {!isRunning && (
        <motion.button
          whileHover={{ scale: 1.03, y: -1 }}
          whileTap={{ scale: 0.97 }}
          onClick={onSimulateFailure}
          className="px-2.5 py-2 rounded-lg text-xs font-medium bg-av-error/15 text-av-error border border-av-error/20 hover:bg-av-error/25 transition-all shrink-0"
        >
          ⚡ Failure
        </motion.button>
      )}

      {/* Divider */}
      <div className="w-px h-7 bg-av-border shrink-0" />

      {/* Status dot */}
      <div className="flex items-center gap-1 shrink-0">
        <div className={`w-2 h-2 rounded-full ${
          isRunning ? 'bg-av-warning animate-pulse' :
          connected ? 'bg-av-success' : 'bg-av-error'
        }`} />
        <span className="text-[10px] text-av-muted whitespace-nowrap">
          {isRunning ? 'Active' : connected ? 'OK' : 'Off'}
        </span>
      </div>

      {/* Compact Metrics — always visible */}
      <div className="flex items-center gap-2 shrink-0">
        {apiModel && (
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-av-primary/10 text-av-primary font-mono border border-av-primary/20 whitespace-nowrap max-w-[120px] truncate">
            {apiProvider ? `${apiProvider}/` : ''}{apiModel}
          </span>
        )}
        <div className="text-center" title={`Input: ${promptTokens} | Output: ${completionTokens}${thinkingTokens > 0 ? ` | Thinking: ${thinkingTokens}` : ''}`}>
          <div className="text-[9px] text-av-muted uppercase">Tokens</div>
          <div className="text-[11px] font-mono text-av-text">{totalTokens.toLocaleString()}</div>
        </div>
        <div className="text-center">
          <div className="text-[9px] text-av-muted uppercase">Cost</div>
          <div className="text-[11px] font-mono text-av-success">${totalCost.toFixed(4)}</div>
        </div>
        <div className="text-center">
          <div className="text-[9px] text-av-muted uppercase">Time</div>
          <div className="text-[11px] font-mono text-av-text">{executionTime.toFixed(1)}s</div>
        </div>
      </div>

      {/* Thinking message — positioned below navbar */}
      {isRunning && thinkingMessage && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="absolute -bottom-4 left-6 text-[10px] text-av-primary/70 truncate"
          style={{ maxWidth: 'calc(100% - 48px)' }}
        >
          💭 {thinkingMessage}
        </motion.div>
      )}
    </motion.nav>
  );
}
