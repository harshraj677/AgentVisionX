import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export default function ChatPanel({
  response,
  isTyping,
  thinkingMessage,
  apiError,
  model,
  provider,
  tokens,
  thinkingSteps,
}) {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [response, thinkingMessage]);

  return (
    <div className="glass-card h-full flex flex-col overflow-hidden" style={{ borderRadius: '14px' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-av-border shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-av-success/60" />
          <span className="text-xs font-semibold uppercase tracking-wider text-av-muted">
            AI Response
          </span>
          {model && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-av-primary/10 text-av-primary font-mono">
              {provider ? `${provider} / ${model}` : model}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {tokens > 0 && (
            <span className="text-[10px] text-av-muted font-mono">{tokens} tokens</span>
          )}
          {isTyping && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex items-center gap-1.5"
            >
              <div className="flex gap-1">
                {[0, 1, 2].map((i) => (
                  <motion.div
                    key={i}
                    className="w-1.5 h-1.5 rounded-full bg-av-primary"
                    animate={{ y: [0, -4, 0] }}
                    transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15 }}
                  />
                ))}
              </div>
              <span className="text-[10px] text-av-primary">thinking...</span>
            </motion.div>
          )}
        </div>
      </div>

      {/* Chat content */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4">
        <AnimatePresence>
          {/* Error State */}
          {apiError && !response && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex gap-3"
            >
              <div className="shrink-0 w-7 h-7 rounded-lg bg-av-error/20 flex items-center justify-center mt-0.5">
                <span className="text-sm">⚠</span>
              </div>
              <div className="flex-1 glass-card-sm p-4 border border-av-error/20">
                <div className="text-sm font-semibold text-av-error mb-2">API Error</div>
                <div className="text-xs text-av-text/80 font-mono break-all">{apiError}</div>
                <div className="text-[10px] text-av-muted mt-3">
                  {apiError.includes('Puter') 
                    ? 'Check browser console for Puter.js details'
                    : 'Check your API key or switch to ✨ Puter.js (Free) in the model selector'}
                </div>
              </div>
            </motion.div>
          )}

          {/* ═══ JUDGE SHOCK MODE — Live AI Thinking Animation ═══ */}
          {isTyping && !response && !apiError && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-4"
            >
              {/* Brain animation header */}
              <motion.div
                className="flex items-center gap-3 px-4 py-3 rounded-xl bg-gradient-to-r from-av-primary/10 to-purple-500/10 border border-av-primary/20"
                animate={{ borderColor: ['rgba(99,102,241,0.2)', 'rgba(139,92,246,0.3)', 'rgba(99,102,241,0.2)'] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                <motion.div
                  className="text-2xl"
                  animate={{ scale: [1, 1.2, 1], rotate: [0, 5, -5, 0] }}
                  transition={{ duration: 2, repeat: Infinity }}
                >
                  🧠
                </motion.div>
                <div>
                  <div className="text-sm font-semibold text-white">AI is thinking...</div>
                  <div className="text-[10px] text-av-muted">
                    Processing your query...
                  </div>
                </div>
              </motion.div>

              {/* Live thinking steps */}
              {thinkingSteps && thinkingSteps.length > 0 && (
                <div className="space-y-1.5 px-2">
                  {thinkingSteps.map((step, i) => (
                    <motion.div
                      key={`think-${i}`}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="flex items-center gap-2 py-1"
                    >
                      <motion.div
                        className={`w-2 h-2 rounded-full ${i === thinkingSteps.length - 1 ? 'bg-av-primary' : 'bg-av-success'}`}
                        animate={i === thinkingSteps.length - 1 ? { scale: [1, 1.5, 1], opacity: [0.5, 1, 0.5] } : {}}
                        transition={{ duration: 1.2, repeat: Infinity }}
                      />
                      <span className={`text-xs ${i === thinkingSteps.length - 1 ? 'text-av-primary' : 'text-av-muted'}`}>
                        {step}
                      </span>
                      {i < thinkingSteps.length - 1 && (
                        <span className="text-[10px] text-av-success">✓</span>
                      )}
                    </motion.div>
                  ))}
                </div>
              )}

              {/* Current thinking message */}
              {thinkingMessage && (
                <motion.div
                  key={thinkingMessage}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="flex items-center gap-3 px-3 py-2 rounded-lg bg-av-primary/5 border border-av-primary/10"
                >
                  <motion.div
                    className="w-2 h-2 rounded-full bg-av-primary"
                    animate={{ scale: [1, 1.5, 1], opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 1.2, repeat: Infinity }}
                  />
                  <span className="text-xs text-av-primary/80">{thinkingMessage}</span>
                </motion.div>
              )}

              {/* Loading skeleton bars */}
              <div className="space-y-3 mt-4">
                {[100, 85, 92, 60, 78].map((w, i) => (
                  <motion.div
                    key={i}
                    className="h-3 rounded bg-white/[0.04]"
                    style={{ width: `${w}%` }}
                    animate={{ opacity: [0.3, 0.6, 0.3] }}
                    transition={{ duration: 1.5, repeat: Infinity, delay: i * 0.15 }}
                  />
                ))}
              </div>
            </motion.div>
          )}

          {/* ═══ TEXT RESPONSE ═══ */}
          {response && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className="prose prose-invert max-w-none"
            >
              <div className="flex gap-3">
                <div className="shrink-0 w-7 h-7 rounded-lg bg-av-primary/20 flex items-center justify-center mt-0.5">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#6366F1" strokeWidth="2">
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                  </svg>
                </div>
                <div className="flex-1 glass-card-sm p-4">
                  <div className={`text-sm text-av-text leading-relaxed whitespace-pre-wrap ${isTyping ? 'typing-cursor' : ''}`}>
                    {formatResponse(response)}
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* Empty state */}
          {!response && !isTyping && !apiError && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex items-center justify-center h-full text-av-muted text-sm"
            >
              <div className="text-center">
                <div className="text-3xl mb-2 opacity-20">💬</div>
                <div>AI response will appear here</div>
                <div className="text-xs font-semibold text-av-primary mb-2">Powered by Puter.js ✨ / Gemini / Groq</div>
                <div className="text-[10px] text-av-muted">Select a model above and run a query</div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

function formatResponse(text) {
  if (!text) return '';

  const lines = text.split('\n');
  const result = [];
  let inCodeBlock = false;
  let codeLines = [];
  let codeLang = '';

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.startsWith('```')) {
      if (!inCodeBlock) {
        inCodeBlock = true;
        codeLang = line.slice(3).trim();
        codeLines = [];
        continue;
      } else {
        inCodeBlock = false;
        result.push(
          <div key={`code-${i}`} className="my-3 rounded-lg overflow-hidden border border-white/5">
            {codeLang && (
              <div className="text-[10px] text-av-muted px-3 py-1.5 bg-white/[0.03] border-b border-white/5 font-mono uppercase">
                {codeLang}
              </div>
            )}
            <pre className="bg-[#0d1117] p-3 overflow-x-auto text-xs font-mono text-green-300/90 leading-relaxed">
              {codeLines.join('\n')}
            </pre>
          </div>
        );
        continue;
      }
    }

    if (inCodeBlock) {
      codeLines.push(line);
      continue;
    }

    if (line.startsWith('## ')) {
      result.push(
        <h3 key={i} className="text-base font-semibold text-white mt-4 mb-2">
          {line.replace('## ', '')}
        </h3>
      );
    } else if (line.startsWith('### ')) {
      result.push(
        <h4 key={i} className="text-sm font-semibold text-av-primary mt-3 mb-1.5">
          {line.replace('### ', '')}
        </h4>
      );
    } else if (line.startsWith('**') && line.endsWith('**')) {
      result.push(
        <p key={i} className="font-semibold text-white mt-2 mb-1">
          {line.replace(/\*\*/g, '')}
        </p>
      );
    } else if (line.startsWith('- ') || line.startsWith('* ')) {
      result.push(
        <div key={i} className="flex gap-2 ml-2 my-0.5">
          <span className="text-av-primary mt-0.5">•</span>
          <span>{renderInlineMarkdown(line.replace(/^[-*]\s/, ''))}</span>
        </div>
      );
    } else if (line.match(/^\d+\.\s/)) {
      result.push(
        <div key={i} className="flex gap-2 ml-2 my-0.5">
          <span className="text-av-primary font-mono text-xs mt-0.5">{line.match(/^\d+/)[0]}.</span>
          <span>{renderInlineMarkdown(line.replace(/^\d+\.\s/, ''))}</span>
        </div>
      );
    } else if (line.startsWith('|')) {
      result.push(
        <div key={i} className="font-mono text-xs text-av-muted my-0.5 overflow-x-auto">
          {line}
        </div>
      );
    } else if (line.trim() === '') {
      result.push(<div key={i} className="h-2" />);
    } else {
      result.push(<p key={i} className="my-0.5">{renderInlineMarkdown(line)}</p>);
    }
  }

  return result;
}

function renderInlineMarkdown(text) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} className="text-white font-semibold">{part.slice(2, -2)}</strong>;
    }
    const codeParts = part.split(/(`[^`]+`)/g);
    return codeParts.map((cp, j) => {
      if (cp.startsWith('`') && cp.endsWith('`')) {
        return (
          <code key={`${i}-${j}`} className="text-av-primary bg-av-primary/10 px-1 py-0.5 rounded text-xs font-mono">
            {cp.slice(1, -1)}
          </code>
        );
      }
      return cp;
    });
  });
}
