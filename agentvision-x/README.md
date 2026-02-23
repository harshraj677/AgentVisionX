# AgentVision X — Live AI Thought Process Visualizer

A professional AI debugging platform that visualizes the thought process of autonomous AI agents in real time.

![AgentVision X](https://img.shields.io/badge/AgentVision-X-6366F1?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-FastAPI-22C55E?style=flat-square)
![React](https://img.shields.io/badge/React-Tailwind-38BDF8?style=flat-square)

---

## 🎯 What It Does

AI agents behave like black boxes. This platform makes AI:

- **Transparent** — See every reasoning step live
- **Debuggable** — Inspect prompts, inputs, outputs, tokens
- **Visual** — Dynamic execution graph with animated nodes
- **Controllable** — Re-run steps, simulate failures, replay timelines

## 🖥️ Dashboard Layout

```
┌──────────────────────────────────────────┐
│ TOP NAVBAR (Query Input + Metrics)       │
├──────────────────────────────────────────┤
│ TIMELINE REPLAY SLIDER                   │
├──────────────┬───────────────────────────┤
│ Execution    │ Chat Response / Inspector │
│ Graph (60%)  │ (40%)                     │
├──────────────┴───────────────────────────┤
│ LIVE LOG CONSOLE                         │
└──────────────────────────────────────────┘
```

## ⚙️ Tech Stack

### Backend
- Python + FastAPI
- WebSocket live updates
- ChatGPT API integration (with offline demo mode)
- SQLite + JSON logging
- Modular architecture

### Frontend
- React 18 + Vite
- Tailwind CSS (dark SaaS theme)
- Framer Motion animations
- React Flow graph visualization
- Recharts analytics

## 🚀 Quick Start

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
python main.py
```

Backend runs at `http://localhost:8000`

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`

### 3. (Optional) Set OpenAI API Key

```bash
set OPENAI_API_KEY=sk-your-key-here   # Windows
export OPENAI_API_KEY=sk-your-key-here # macOS/Linux
```

Without an API key, the system runs in **Demo Mode** with simulated AI responses.

## ✨ Features

### Live AI Thinking Mode
The system simulates progressive thinking steps before showing the final answer:
1. Understanding question...
2. Planning response...
3. Reasoning...
4. Generating final answer...

Each step appears live in the execution graph, logs console, and status indicator.

### Execution Graph
- Dynamic nodes with status colors (yellow=running, green=success, red=error, gray=waiting)
- Animated edges and transitions
- Zoom, pan, minimap
- Click any node to inspect

### Step Inspector (Chrome DevTools-style)
- Step name & status
- Prompt used
- Input/Output data
- Reasoning text
- Tokens used
- Execution time

### Live Log Console
Terminal-style logs with levels: `[INFO]`, `[STEP]`, `[WARNING]`, `[ERROR]`

### Simulate Failure
Click "Simulate Failure" to see error handling in action — a node turns red, error appears in logs.

### Re-run Step
Click any step → "Re-run" to execute only that step again.

### Timeline Replay
Slider to replay execution history and inspect past states.

### Token & Cost Analytics
- Total tokens, estimated cost, execution duration
- Bar chart showing token usage per step

## 📂 Project Structure

```
agentvision-x/
├── backend/
│   ├── main.py                 # FastAPI server
│   ├── chatgpt_client.py       # OpenAI API + demo mode
│   ├── planner.py              # Agent step planner
│   ├── live_thinking_engine.py # Progressive thinking simulation
│   ├── executor.py             # Pipeline executor
│   ├── logger.py               # SQLite + JSON logging
│   ├── websocket_manager.py    # WebSocket manager
│   ├── models.py               # Pydantic models
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── index.css
│   │   ├── hooks/
│   │   │   └── useWebSocket.js
│   │   └── components/
│   │       ├── Navbar.jsx
│   │       ├── ExecutionGraph.jsx
│   │       ├── ChatPanel.jsx
│   │       ├── StepInspector.jsx
│   │       ├── LogsConsole.jsx
│   │       ├── TimelineReplay.jsx
│   │       └── TokenAnalytics.jsx
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── postcss.config.js
├── logs/
│   └── execution_history.json
└── README.md
```

## 🎨 Design System

| Element    | Color     |
|------------|-----------|
| Background | `#0B1020` |
| Cards      | `#111827` |
| Primary    | `#6366F1` |
| Success    | `#22C55E` |
| Error      | `#EF4444` |
| Warning    | `#F59E0B` |
| Text       | `#E5E7EB` |

- Glassmorphism cards with `backdrop-filter: blur(12px)`
- Neon glow accents
- Framer Motion micro-animations
- JetBrains Mono for terminal/code
- Inter for UI text

---

Built with ❤️ by AgentVision X
