import React, { useCallback, useEffect } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  useReactFlow,
  ReactFlowProvider,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { motion } from 'framer-motion';

/* ─── Custom Node ─── */
function AgentNode({ data }) {
  const statusColors = {
    waiting: { bg: '#1F2937', border: '#374151', glow: 'none', text: '#9CA3AF' },
    running: { bg: '#78350F', border: '#F59E0B', glow: '0 0 20px rgba(245,158,11,0.5)', text: '#FDE68A' },
    success: { bg: '#064E3B', border: '#22C55E', glow: '0 0 20px rgba(34,197,94,0.4)', text: '#BBF7D0' },
    error: { bg: '#7F1D1D', border: '#EF4444', glow: '0 0 20px rgba(239,68,68,0.5)', text: '#FECACA' },
  };

  const c = statusColors[data.status] || statusColors.waiting;

  return (
    <motion.div
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      onClick={() => data.onSelect?.(data.stepData)}
      className={`cursor-pointer ${data.status === 'running' ? 'node-running' : ''} ${data.status === 'error' ? 'node-error' : ''}`}
      style={{
        background: c.bg,
        border: `2px solid ${c.border}`,
        borderRadius: '12px',
        padding: '12px 18px',
        minWidth: '160px',
        boxShadow: c.glow,
        transition: 'all 0.3s ease',
      }}
    >
      <div className="flex items-center gap-2 mb-1">
        <div
          className={`w-2.5 h-2.5 rounded-full ${data.status === 'running' ? 'animate-pulse' : ''}`}
          style={{ backgroundColor: c.border }}
        />
        <span className="text-xs font-semibold tracking-wide uppercase" style={{ color: c.text }}>
          {data.status}
        </span>
      </div>
      <div className="text-sm font-medium text-white">{data.label}</div>
      {data.stepData?.execution_time > 0 && (
        <div className="text-[10px] mt-1" style={{ color: c.text }}>
          {data.stepData.execution_time.toFixed(1)}s · {data.stepData.tokens} tokens
        </div>
      )}
    </motion.div>
  );
}

const nodeTypes = { agentNode: AgentNode };

/* ─── Inner canvas — must live inside ReactFlowProvider to use useReactFlow ─── */
function FlowCanvas({ steps, onSelectStep }) {
  const { fitView } = useReactFlow();

  const buildNodes = useCallback(() => {
    if (!steps || steps.length === 0) return [];
    const horizontalSpace = 220;
    const verticalCenter = 100;
    return steps.map((step, i) => ({
      id: step.id,
      type: 'agentNode',
      position: { x: i * horizontalSpace + 30, y: verticalCenter },
      data: {
        label: step.name,
        status: step.status,
        stepData: step,
        onSelect: onSelectStep,
      },
    }));
  }, [steps, onSelectStep]);

  const buildEdges = useCallback(() => {
    if (!steps || steps.length < 2) return [];
    return steps.slice(1).map((step, i) => {
      const sourceStep = steps[i];
      const isActive = step.status === 'running' || sourceStep.status === 'success';
      return {
        id: `e-${sourceStep.id}-${step.id}`,
        source: sourceStep.id,
        target: step.id,
        animated: isActive,
        style: {
          stroke: sourceStep.status === 'success' ? '#22C55E' :
                  sourceStep.status === 'error' ? '#EF4444' :
                  step.status === 'running' ? '#F59E0B' : '#374151',
          strokeWidth: isActive ? 2.5 : 1.5,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: sourceStep.status === 'success' ? '#22C55E' : '#374151',
        },
      };
    });
  }, [steps]);

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  useEffect(() => {
    const newNodes = buildNodes();
    setNodes(newNodes);
    setEdges(buildEdges());
    // Re-fit every time nodes change so all steps are always visible
    if (newNodes.length > 0) {
      setTimeout(() => fitView({ padding: 0.18, duration: 350, includeHiddenNodes: true }), 60);
    }
  }, [steps, buildNodes, buildEdges, setNodes, setEdges, fitView]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      nodeTypes={nodeTypes}
      minZoom={0.05}
      maxZoom={2}
      attributionPosition="bottom-left"
    >
      <Background color="#1E293B" gap={20} size={1} />
      <Controls
        style={{
          background: 'rgba(17,24,39,0.9)',
          border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: '8px',
        }}
      />
      <MiniMap
        nodeColor={(node) => {
          const s = node.data?.status;
          if (s === 'success') return '#22C55E';
          if (s === 'running') return '#F59E0B';
          if (s === 'error') return '#EF4444';
          return '#374151';
        }}
        style={{
          background: 'rgba(11,16,32,0.9)',
          border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: '8px',
        }}
        maskColor="rgba(11,16,32,0.7)"
      />
    </ReactFlow>
  );
}

/* ─── Graph Component ─── */
export default function ExecutionGraph({ steps, onSelectStep }) {
  return (
    <div className="glass-card h-full w-full overflow-hidden relative" style={{ borderRadius: '14px' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-av-border">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-av-primary/60" />
          <span className="text-xs font-semibold uppercase tracking-wider text-av-muted">
            Execution Graph
          </span>
        </div>
        <span className="text-[10px] text-av-muted">
          {steps?.length || 0} steps
        </span>
      </div>

      {/* Graph canvas */}
      <div className="w-full" style={{ height: 'calc(100% - 40px)' }}>
        {steps && steps.length > 0 ? (
          <ReactFlowProvider>
            <FlowCanvas steps={steps} onSelectStep={onSelectStep} />
          </ReactFlowProvider>
        ) : (
          <div className="flex items-center justify-center h-full text-av-muted text-sm">
            <div className="text-center">
              <div className="text-4xl mb-3 opacity-20">◇</div>
              <div>Run an agent to see the execution graph</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
