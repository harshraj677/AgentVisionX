import React, { useState, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Navbar from './components/Navbar';
import ExecutionGraph from './components/ExecutionGraph';
import ChatPanel from './components/ChatPanel';
import StepInspector from './components/StepInspector';
import LogsConsole from './components/LogsConsole';
import TimelineReplay from './components/TimelineReplay';
import TokenAnalytics from './components/TokenAnalytics';
import useWebSocket from './hooks/useWebSocket';

const API_BASE = 'http://localhost:8000';

export default function App() {
  // ─── State ───
  const [steps, setSteps] = useState([]);
  const [logs, setLogs] = useState([]);
  const [response, setResponse] = useState('');
  const [selectedStep, setSelectedStep] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [totalTokens, setTotalTokens] = useState(0);
  const [totalCost, setTotalCost] = useState(0);
  const [executionTime, setExecutionTime] = useState(0);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [rightTab, setRightTab] = useState('chat');
  const [thinkingMessage, setThinkingMessage] = useState('');
  const [apiModel, setApiModel] = useState('');
  const [promptTokens, setPromptTokens] = useState(0);
  const [completionTokens, setCompletionTokens] = useState(0);
  const [apiError, setApiError] = useState('');
  const [usageBreakdown, setUsageBreakdown] = useState(null);
  const [apiProvider, setApiProvider] = useState('');
  const [thinkingTokens, setThinkingTokens] = useState(0);

  const timerRef = useRef(null);
  const startTimeRef = useRef(null);

  // ─── Timer ───
  const startTimer = () => {
    startTimeRef.current = Date.now();
    timerRef.current = setInterval(() => {
      setExecutionTime((Date.now() - startTimeRef.current) / 1000);
    }, 100);
  };

  const stopTimer = () => {
    clearInterval(timerRef.current);
  };

  // ─── WebSocket Handler ───
  const handleWSMessage = useCallback((msg) => {
    switch (msg.type) {
      case 'plan':
        setSteps(msg.data.steps || []);
        setResponse('');
        setIsRunning(true);
        setIsTyping(true);
        setApiError('');
        setThinkingMessage('');
        setApiModel('');
        setPromptTokens(0);
        setCompletionTokens(0);
        setUsageBreakdown(null);
        setThinkingTokens(0);
        startTimer();
        break;

      case 'step_update':
        setSteps((prev) =>
          prev.map((s) => (s.id === msg.data.id ? { ...s, ...msg.data } : s))
        );
        break;

      case 'thinking':
        setThinkingMessage(msg.data.message || '');
        break;

      case 'log':
        setLogs((prev) => [...prev, { ...msg.data, timestamp: Date.now() }]);
        break;

      case 'response_chunk':
        setResponse((prev) => prev + msg.data.chunk);
        break;

      case 'complete':
        setIsRunning(false);
        setIsTyping(false);
        setThinkingMessage('');
        setTotalTokens(msg.data.total_tokens || 0);
        setTotalCost(msg.data.total_cost || 0);
        setPromptTokens(msg.data.total_prompt_tokens || 0);
        setCompletionTokens(msg.data.total_completion_tokens || 0);
        setThinkingTokens(msg.data.total_thinking_tokens || 0);
        setApiModel(msg.data.model || '');
        setApiProvider(msg.data.provider || '');
        setUsageBreakdown(msg.data.usage || null);
        if (msg.data.final_response) {
          setResponse(msg.data.final_response);
        }
        if (msg.data.error) {
          setApiError(msg.data.error);
        }
        stopTimer();
        if (msg.data.status !== 'error') {
          setShowAnalytics(true);
        }
        break;

      case 'error':
        setSteps((prev) =>
          prev.map((s) =>
            s.id === msg.data.step_id
              ? { ...s, status: 'error', output_data: msg.data.error }
              : s
          )
        );
        setApiError(msg.data.error || 'Unknown error');
        break;

      default:
        break;
    }
  }, []);

  const { connected } = useWebSocket(handleWSMessage);

  // ─── Actions ───
  const runQuery = async (query) => {
    setSteps([]);
    setLogs([]);
    setResponse('');
    setSelectedStep(null);
    setTotalTokens(0);
    setTotalCost(0);
    setExecutionTime(0);
    setShowAnalytics(false);
    setRightTab('chat');
    setIsTyping(true);
    setApiError('');
    setThinkingMessage('');
    setApiModel('');
    setPromptTokens(0);
    setCompletionTokens(0);
    setThinkingTokens(0);
    setUsageBreakdown(null);

    try {
      await fetch(`${API_BASE}/api/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });
    } catch (err) {
      setLogs((prev) => [
        ...prev,
        { level: 'ERROR', message: `Connection failed: ${err.message}`, timestamp: Date.now() },
      ]);
      setIsRunning(false);
      setIsTyping(false);
      setApiError(err.message);
    }
  };

  const simulateFailure = async () => {
    if (steps.length === 0) {
      setLogs((prev) => [
        ...prev,
        { level: 'WARNING', message: 'Run a query first, then simulate failure', timestamp: Date.now() },
      ]);
      return;
    }
    const midIndex = Math.floor(steps.length / 2);
    const failStepId = steps[midIndex]?.id;

    setSteps([]);
    setLogs([]);
    setResponse('');
    setSelectedStep(null);
    setTotalTokens(0);
    setTotalCost(0);
    setExecutionTime(0);
    setShowAnalytics(false);
    setApiError('');

    try {
      // FIXED: Send step_id in request body
      await fetch(`${API_BASE}/api/execute-with-failure`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query: 'Demonstrate failure simulation in the AI pipeline',
          step_id: failStepId 
        }),
      });
    } catch (err) {
      setLogs((prev) => [
        ...prev,
        { level: 'ERROR', message: `Connection failed: ${err.message}`, timestamp: Date.now() },
      ]);
    }
  };

  const rerunStep = async (stepId) => {
    try {
      await fetch(`${API_BASE}/api/rerun-step/${stepId}`, { method: 'POST' });
      setLogs((prev) => [
        ...prev,
        { level: 'INFO', message: `Re-running step ${stepId}...`, timestamp: Date.now() },
      ]);
    } catch (err) {
      setLogs((prev) => [
        ...prev,
        { level: 'ERROR', message: `Re-run failed: ${err.message}`, timestamp: Date.now() },
      ]);
    }
  };

  const selectStep = (step) => {
    setSelectedStep(step);
    setRightTab('inspector');
  };

  const handleTimelineSeek = (index) => {
    if (steps[index]) {
      setSelectedStep(steps[index]);
    }
  };

  return (
    <div className="h-screen flex flex-col bg-av-bg overflow-hidden">
      {/* TOP NAVBAR */}
      <Navbar
        onRunQuery={runQuery}
        onSimulateFailure={simulateFailure}
        status={isRunning ? 'running' : 'idle'}
        totalTokens={totalTokens}
        promptTokens={promptTokens}
        completionTokens={completionTokens}
        totalCost={totalCost}
        executionTime={executionTime}
        isRunning={isRunning}
        connected={connected}
        apiModel={apiModel}
        apiProvider={apiProvider}
        thinkingMessage={thinkingMessage}
      />

      {/* TIMELINE REPLAY */}
      <AnimatePresence>
        {steps.length > 0 && <TimelineReplay steps={steps} onSeek={handleTimelineSeek} />}
      </AnimatePresence>

      {/* MAIN CONTENT — LEFT 60% | RIGHT 40% */}
      <div className="flex-1 flex gap-2 px-3 pb-2 min-h-0">
        {/* LEFT — Execution Graph */}
        <div className="w-[60%] flex flex-col gap-2 min-h-0">
          <div className="flex-1 min-h-0">
            <ExecutionGraph steps={steps} onSelectStep={selectStep} />
          </div>

          {/* Token Analytics (collapsible) */}
          <AnimatePresence>
            {showAnalytics && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.3 }}
                className="shrink-0"
              >
                <TokenAnalytics
                  steps={steps}
                  totalTokens={totalTokens}
                  promptTokens={promptTokens}
                  completionTokens={completionTokens}
                  thinkingTokens={thinkingTokens}
                  totalCost={totalCost}
                  totalTime={executionTime}
                  model={apiModel}
                  usage={usageBreakdown}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* RIGHT — Chat + Inspector */}
        <div className="w-[40%] flex flex-col gap-2 min-h-0">
          {/* Tab switcher */}
          <div className="flex gap-1 shrink-0">
            <button
              onClick={() => setRightTab('chat')}
              className={`flex-1 text-xs py-1.5 rounded-lg font-medium transition-all ${
                rightTab === 'chat'
                  ? 'bg-av-primary/20 text-av-primary border border-av-primary/30'
                  : 'text-av-muted hover:text-white hover:bg-white/5'
              }`}
            >
              💬 Chat Response
            </button>
            <button
              onClick={() => setRightTab('inspector')}
              className={`flex-1 text-xs py-1.5 rounded-lg font-medium transition-all ${
                rightTab === 'inspector'
                  ? 'bg-av-primary/20 text-av-primary border border-av-primary/30'
                  : 'text-av-muted hover:text-white hover:bg-white/5'
              }`}
            >
              🔍 Inspector {selectedStep ? `— ${selectedStep.name}` : ''}
            </button>
          </div>

          {/* Tab content */}
          <div className="flex-1 min-h-0">
            <AnimatePresence mode="wait">
              {rightTab === 'chat' ? (
                <motion.div
                  key="chat"
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                  transition={{ duration: 0.2 }}
                  className="h-full"
                >
                  <ChatPanel
                    response={response}
                    isTyping={isTyping}
                    thinkingMessage={thinkingMessage}
                    apiError={apiError}
                    model={apiModel}
                    provider={apiProvider}
                    tokens={totalTokens}
                  />
                </motion.div>
              ) : (
                <motion.div
                  key="inspector"
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                  transition={{ duration: 0.2 }}
                  className="h-full"
                >
                  <StepInspector
                    step={selectedStep}
                    onRerunStep={rerunStep}
                    onClose={() => {
                      setSelectedStep(null);
                      setRightTab('chat');
                    }}
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* BOTTOM — Live Log Console */}
      <div className="h-[180px] px-3 pb-3 shrink-0">
        <LogsConsole logs={logs} />
      </div>
    </div>
  );
}
