import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

export default function TimelineReplay({ steps, onSeek }) {
  const [position, setPosition] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const totalSteps = steps?.length || 0;

  useEffect(() => {
    if (!isPlaying || totalSteps === 0) return;

    const timer = setInterval(() => {
      setPosition((prev) => {
        if (prev >= totalSteps - 1) {
          setIsPlaying(false);
          return prev;
        }
        const next = prev + 1;
        onSeek?.(next);
        return next;
      });
    }, 1500);

    return () => clearInterval(timer);
  }, [isPlaying, totalSteps, onSeek]);

  useEffect(() => {
    // Update position when steps complete
    if (steps) {
      const lastComplete = steps.reduce((acc, s, i) => 
        s.status === 'success' || s.status === 'error' ? i : acc, -1);
      if (lastComplete >= 0) setPosition(lastComplete);
    }
  }, [steps]);

  const handleSliderChange = (e) => {
    const val = parseInt(e.target.value, 10);
    setPosition(val);
    onSeek?.(val);
  };

  if (!steps || steps.length === 0) return null;

  const currentStep = steps[position];
  const progress = totalSteps > 1 ? (position / (totalSteps - 1)) * 100 : 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card px-4 py-2.5 mx-3 mb-2 flex items-center gap-4"
      style={{ borderRadius: '14px' }}
    >
      {/* Play/Pause */}
      <button
        onClick={() => setIsPlaying(!isPlaying)}
        className="w-7 h-7 rounded-full bg-av-primary/20 text-av-primary flex items-center justify-center hover:bg-av-primary/30 transition-all text-xs shrink-0"
      >
        {isPlaying ? '⏸' : '▶'}
      </button>

      {/* Timeline label */}
      <div className="shrink-0">
        <span className="text-[10px] text-av-muted uppercase tracking-wider">Timeline</span>
      </div>

      {/* Slider */}
      <div className="flex-1 relative">
        <div className="relative h-2 bg-av-bg/60 rounded-full overflow-hidden">
          <motion.div
            className="absolute h-full rounded-full bg-gradient-to-r from-av-primary to-av-primary/60"
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
        <input
          type="range"
          min="0"
          max={Math.max(totalSteps - 1, 0)}
          value={position}
          onChange={handleSliderChange}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />
        {/* Step markers */}
        <div className="flex justify-between mt-1">
          {steps.map((s, i) => (
            <div
              key={i}
              className={`w-1.5 h-1.5 rounded-full transition-all ${
                i <= position ? 'bg-av-primary' : 'bg-av-border'
              } ${i === position ? 'scale-150' : ''}`}
            />
          ))}
        </div>
      </div>

      {/* Current step info */}
      <div className="shrink-0 text-right min-w-[120px]">
        <div className="text-xs font-medium text-white truncate">
          {currentStep?.name || '—'}
        </div>
        <div className="text-[10px] text-av-muted">
          Step {position + 1} of {totalSteps}
        </div>
      </div>
    </motion.div>
  );
}
