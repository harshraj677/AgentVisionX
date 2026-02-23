import React from 'react';
import { motion } from 'framer-motion';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  PieChart, Pie, Legend,
} from 'recharts';

export default function TokenAnalytics({
  steps,
  totalTokens: totalTokensRaw,
  promptTokens: promptTokensRaw,
  completionTokens: completionTokensRaw,
  thinkingTokens: thinkingTokensProp,
  totalCost: totalCostRaw,
  totalTime: totalTimeRaw,
  model,
  usage,
}) {
  // ── Safe fallbacks: never show NaN or undefined ──
  const promptTokens = Number(promptTokensRaw) || 0;
  const completionTokens = Number(completionTokensRaw) || 0;
  const totalCost = Number(totalCostRaw) || 0;
  const totalTime = Number(totalTimeRaw) || 0;
  // Total tokens: prefer explicit value, else derive from prompt + completion
  const totalTokens = Number(totalTokensRaw) || (promptTokens + completionTokens) || 0;
  // ── Build time chart data from usage steps (all have execution_time) ──
  const usageSteps = usage?.steps || [];
  const timeChartData = usageSteps.map((s, i) => ({
    name: s.step_name?.length > 14 ? s.step_name.slice(0, 14) + '…' : s.step_name,
    fullName: s.step_name,
    time: parseFloat((s.execution_time || 0).toFixed(2)),
    tokens: s.total_tokens || 0,
    model: s.model || 'local',
  }));

  // Fallback: build from steps prop if usage not available yet
  const fallbackChartData = (steps || [])
    .filter((s) => s.status === 'success' || s.status === 'error')
    .map((s) => ({
      name: s.name?.length > 14 ? s.name.slice(0, 14) + '…' : s.name,
      fullName: s.name,
      time: parseFloat((s.execution_time || 0).toFixed(2)),
      tokens: s.tokens || 0,
      model: '',
    }));

  const chartData = timeChartData.length > 0 ? timeChartData : fallbackChartData;

  // ── Token pie data ──
  // IMPORTANT: thinking_tokens is a SUBSET of completion_tokens (not additive).
  // Net output = completion_tokens - thinking_tokens
  const thinkingTokens = Math.min(thinkingTokensProp || 0, completionTokens);
  const netOutputTokens = completionTokens - thinkingTokens;
  const tokenPieData = [
    { name: 'Prompt (Input)', value: promptTokens, fill: '#38BDF8' },
    { name: 'Output (Net)', value: netOutputTokens, fill: '#22C55E' },
  ];
  if (thinkingTokens > 0) {
    tokenPieData.push({ name: 'Thinking/Reasoning', value: thinkingTokens, fill: '#A78BFA' });
  }
  // Total for pie percentage — prompt + netOutput + thinking = prompt + completion = totalTokens
  const pieTotal = totalTokens || (promptTokens + completionTokens) || 1;

  const stepColors = [
    '#6366F1', '#8B5CF6', '#EC4899', '#F59E0B', '#22C55E',
    '#38BDF8', '#14B8A6', '#F43F5E', '#A78BFA', '#FB923C',
  ];

  // ── Cost display ──
  const isFree = totalCost === 0;
  const costDisplay = isFree ? 'FREE' : `$${totalCost.toFixed(6)}`;
  const avgTimePerStep = chartData.length > 0
    ? (totalTime / chartData.length).toFixed(2)
    : '0';
  const actualTotalTime = totalTime || (chartData.length > 0
    ? chartData.reduce((a, d) => a + d.time, 0)
    : 0);
  const tokensPerSec = actualTotalTime > 0 ? Math.round((promptTokens + completionTokens) / actualTotalTime) : 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card p-4"
      style={{ borderRadius: '14px' }}
    >
      {/* ── Header ── */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-av-warning/60" />
          <span className="text-xs font-semibold uppercase tracking-wider text-av-muted">
            Token & Cost Analytics
          </span>
        </div>
        <div className="flex items-center gap-2">
          {model && (
            <span className="text-[10px] px-2 py-0.5 rounded bg-av-primary/10 text-av-primary font-mono border border-av-primary/20">
              {model}
            </span>
          )}
          <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-mono border border-emerald-500/20">
            {chartData.length} steps
          </span>
        </div>
      </div>

      {/* ── Summary Cards — 5 columns ── */}
      <div className="grid grid-cols-5 gap-2 mb-3">
        <div className="glass-card-sm p-2.5 text-center">
          <div className="text-[10px] text-av-muted uppercase">Total Tokens</div>
          <div className="text-lg font-mono font-bold text-av-primary">{totalTokens.toLocaleString()}</div>
          <div className="text-[9px] text-av-muted mt-0.5 font-mono">
            {promptTokens > 0 && <span className="text-sky-400">↑{promptTokens}</span>}
            {netOutputTokens > 0 && <span className="text-emerald-400 ml-1">↓{netOutputTokens}</span>}
            {thinkingTokens > 0 && <span className="text-purple-400 ml-1">🧠{thinkingTokens}</span>}
          </div>
          <div className="text-[8px] text-av-muted/60 mt-0.5">from API response</div>
        </div>
        <div className="glass-card-sm p-2.5 text-center" title="Includes your query + the hidden system instruction sent to the AI. This is the real token count from the API, not a word count.">
          <div className="text-[10px] text-av-muted uppercase">Input</div>
          <div className="text-lg font-mono font-bold text-sky-400">{promptTokens.toLocaleString()}</div>
          <div className="text-[9px] text-av-muted mt-0.5">query + system prompt</div>
        </div>
        <div className="glass-card-sm p-2.5 text-center">
          <div className="text-[10px] text-av-muted uppercase">Output</div>
          <div className="text-lg font-mono font-bold text-emerald-400">{netOutputTokens.toLocaleString()}</div>
          <div className="text-[9px] text-av-muted mt-0.5">
            {thinkingTokens > 0 ? 'net response' : 'response tokens'}
          </div>
          {thinkingTokens > 0 && (
            <div className="text-[9px] text-purple-400 mt-0.5 font-mono">
              +🧠{thinkingTokens.toLocaleString()}
            </div>
          )}
        </div>
        <div className="glass-card-sm p-2.5 text-center">
          <div className="text-[10px] text-av-muted uppercase">Total Time</div>
          <div className="text-lg font-mono font-bold text-av-warning">{actualTotalTime.toFixed(1)}s</div>
          <div className="text-[9px] text-av-muted mt-0.5">avg {avgTimePerStep}s/step</div>
        </div>
        <div className="glass-card-sm p-2.5 text-center">
          <div className="text-[10px] text-av-muted uppercase">API Cost</div>
          <div className={`text-lg font-mono font-bold ${isFree ? 'text-emerald-400' : 'text-av-success'}`}>
            {costDisplay}
          </div>
          <div className="text-[9px] text-av-muted mt-0.5">
            {isFree ? 'free tier' : 'from API'}
          </div>
        </div>
      </div>

      {/* ── Charts Row: Time per Step + Token Breakdown ── */}
      <div className="grid grid-cols-3 gap-3 mb-3">
        {/* Time per Step Bar Chart — 2/3 width */}
        {chartData.length > 0 && (
          <div className="col-span-2">
            <div className="text-[10px] text-av-muted uppercase tracking-wider mb-1.5 font-semibold flex items-center gap-1">
              <span>⏱</span> Time per Step (seconds)
            </div>
            <div className="h-36">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 8, fill: '#9CA3AF' }}
                    axisLine={{ stroke: '#374151' }}
                    tickLine={false}
                    interval={0}
                    angle={-15}
                    textAnchor="end"
                    height={38}
                  />
                  <YAxis
                    tick={{ fontSize: 9, fill: '#9CA3AF' }}
                    axisLine={{ stroke: '#374151' }}
                    tickLine={false}
                    width={30}
                    tickFormatter={(v) => `${v}s`}
                  />
                  <Tooltip
                    contentStyle={{
                      background: '#111827',
                      border: '1px solid rgba(255,255,255,0.15)',
                      borderRadius: '8px',
                      fontSize: '11px',
                      color: '#E5E7EB',
                      padding: '8px 12px',
                    }}
                    formatter={(value, name) => {
                      if (name === 'time') return [`${value}s`, 'Time'];
                      return [value, name];
                    }}
                    labelFormatter={(label) => {
                      const item = chartData.find(d => d.name === label);
                      return item?.fullName || label;
                    }}
                    cursor={{ fill: 'rgba(99,102,241,0.1)' }}
                  />
                  <Bar dataKey="time" radius={[4, 4, 0, 0]} maxBarSize={50}>
                    {chartData.map((entry, index) => (
                      <Cell
                        key={index}
                        fill={stepColors[index % stepColors.length]}
                        fillOpacity={0.85}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Token Breakdown Pie Chart — 1/3 width */}
        {totalTokens > 0 && (
          <div className="col-span-1">
            <div className="text-[10px] text-av-muted uppercase tracking-wider mb-1.5 font-semibold flex items-center gap-1">
              <span>🔤</span> Token Breakdown
            </div>
            <div className="h-36">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={tokenPieData}
                    cx="50%"
                    cy="45%"
                    innerRadius={25}
                    outerRadius={45}
                    paddingAngle={3}
                    dataKey="value"
                    stroke="none"
                  >
                    {tokenPieData.map((entry, index) => (
                      <Cell key={index} fill={entry.fill} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: '#111827',
                      border: '1px solid rgba(255,255,255,0.15)',
                      borderRadius: '8px',
                      fontSize: '11px',
                      color: '#E5E7EB',
                      padding: '8px 12px',
                    }}
                    formatter={(value, name) => [
                      `${value.toLocaleString()} (${((value / pieTotal) * 100).toFixed(1)}%)`,
                      name,
                    ]}
                  />
                  <Legend
                    verticalAlign="bottom"
                    iconSize={8}
                    wrapperStyle={{ fontSize: '9px', color: '#9CA3AF' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </div>

      {/* ── Per-Step Breakdown Table ── */}
      {usageSteps.length > 0 && (
        <div>
          <div className="text-[10px] text-av-muted uppercase tracking-wider mb-1.5 font-semibold flex items-center gap-1">
            <span>📊</span> Per-Step Breakdown
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-[10px]">
              <thead>
                <tr className="text-av-muted border-b border-av-border">
                  <th className="text-left py-1 px-1.5 font-medium">Step</th>
                  <th className="text-right py-1 px-1.5 font-medium">Time</th>
                  <th className="text-right py-1 px-1.5 font-medium">Tokens</th>
                  <th className="text-right py-1 px-1.5 font-medium">Prompt</th>
                  <th className="text-right py-1 px-1.5 font-medium">Completion</th>
                  <th className="text-right py-1 px-1.5 font-medium">Model</th>
                </tr>
              </thead>
              <tbody>
                {usageSteps.map((s, i) => (
                  <tr key={i} className="border-b border-av-border/30 hover:bg-white/[0.02]">
                    <td className="py-1 px-1.5 text-white font-medium">
                      <div className="flex items-center gap-1.5">
                        <div
                          className="w-2 h-2 rounded-full shrink-0"
                          style={{ backgroundColor: stepColors[i % stepColors.length] }}
                        />
                        {s.step_name}
                      </div>
                    </td>
                    <td className="text-right py-1 px-1.5 font-mono text-av-warning">
                      {s.execution_time.toFixed(2)}s
                    </td>
                    <td className="text-right py-1 px-1.5 font-mono text-av-primary">
                      {s.total_tokens > 0 ? s.total_tokens.toLocaleString() : '—'}
                    </td>
                    <td className="text-right py-1 px-1.5 font-mono text-sky-400">
                      {s.prompt_tokens > 0 ? s.prompt_tokens.toLocaleString() : '—'}
                    </td>
                    <td className="text-right py-1 px-1.5 font-mono text-emerald-400">
                      {s.completion_tokens > 0 ? s.completion_tokens.toLocaleString() : '—'}
                    </td>
                    <td className="text-right py-1 px-1.5 font-mono text-av-muted">
                      {s.model === 'local' ? '🧠 local' : s.model || '—'}
                    </td>
                  </tr>
                ))}
                {/* Totals row */}
                <tr className="border-t border-av-border text-white font-semibold">
                  <td className="py-1 px-1.5">Total</td>
                  <td className="text-right py-1 px-1.5 font-mono text-av-warning">
                    {usageSteps.reduce((a, s) => a + s.execution_time, 0).toFixed(2)}s
                  </td>
                  <td className="text-right py-1 px-1.5 font-mono text-av-primary">
                    {totalTokens.toLocaleString()}
                  </td>
                  <td className="text-right py-1 px-1.5 font-mono text-sky-400">
                    {promptTokens.toLocaleString()}
                  </td>
                  <td className="text-right py-1 px-1.5 font-mono text-emerald-400">
                    {completionTokens.toLocaleString()}
                  </td>
                  <td className="text-right py-1 px-1.5 font-mono text-av-muted">
                    {tokensPerSec > 0 ? `${tokensPerSec} tok/s` : '—'}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}
    </motion.div>
  );
}
