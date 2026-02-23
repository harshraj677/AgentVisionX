import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const levelConfig = {
  INFO: { color: '#6366F1', icon: 'ℹ' },
  STEP: { color: '#22C55E', icon: '►' },
  WARNING: { color: '#F59E0B', icon: '⚠' },
  ERROR: { color: '#EF4444', icon: '✖' },
  SUCCESS: { color: '#22C55E', icon: '✔' },
};

export default function LogsConsole({ logs }) {
  const scrollRef = useRef(null);
  const autoScroll = useRef(true);

  useEffect(() => {
    if (scrollRef.current && autoScroll.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    autoScroll.current = scrollHeight - scrollTop - clientHeight < 50;
  };

  const formatTimestamp = (ts) => {
    if (!ts) return new Date().toLocaleTimeString('en-US', { hour12: false });
    const d = typeof ts === 'number' ? new Date(ts) : new Date();
    return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
      + '.' + String(d.getMilliseconds()).padStart(3, '0');
  };

  return (
    <div className="glass-card h-full flex flex-col overflow-hidden" style={{ borderRadius: '14px' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-av-border shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-av-primary/40" />
          <span className="text-xs font-semibold uppercase tracking-wider text-av-muted">
            Live Console
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-av-muted">{logs.length} entries</span>
          <div className="flex gap-1">
            {['INFO', 'STEP', 'WARNING', 'ERROR'].map((level) => {
              const count = logs.filter((l) => l.level === level).length;
              if (count === 0) return null;
              return (
                <span
                  key={level}
                  className="text-[9px] px-1.5 py-0.5 rounded font-mono"
                  style={{
                    color: levelConfig[level].color,
                    backgroundColor: `${levelConfig[level].color}15`,
                  }}
                >
                  {count}
                </span>
              );
            })}
          </div>
        </div>
      </div>

      {/* Log entries */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto font-mono text-xs"
        style={{ background: 'rgba(0,0,0,0.2)' }}
      >
        {logs.length === 0 ? (
          <div className="flex items-center justify-center h-full text-av-muted text-xs">
            Waiting for execution logs...
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {logs.map((log, i) => {
              const lc = levelConfig[log.level] || levelConfig.INFO;
              return (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.15 }}
                  className={`log-entry log-${log.level} flex items-start gap-2 py-1`}
                >
                  <span className="text-av-muted/60 shrink-0 w-20 text-[10px]">
                    {formatTimestamp(log.timestamp)}
                  </span>
                  <span
                    className="shrink-0 font-bold w-14 text-[10px] uppercase"
                    style={{ color: lc.color }}
                  >
                    [{log.level}]
                  </span>
                  <span className="text-av-text flex-1">{log.message}</span>
                  {log.step && (
                    <span className="text-av-muted/50 shrink-0 text-[10px]">{log.step}</span>
                  )}
                </motion.div>
              );
            })}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
