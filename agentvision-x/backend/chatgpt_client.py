"""
AgentVision X — Multi-Provider AI Client
=========================================
Priority: Gemini → OpenAI → Groq (free) → Knowledge Base fallback

Handles: retry logic, query extraction, provider failover.
"""
import os
import re
import httpx
import asyncio

# ─── API Configuration ───
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

SYSTEM_PROMPT = (
    "You are a highly knowledgeable AI assistant. "
    "Give clear, accurate, detailed, well-structured answers. "
    "Use markdown: ## headers, ### subheaders, **bold**, bullet points, numbered lists, code blocks with language tags. "
    "Be comprehensive. Always answer the user's actual question directly and accurately."
)


def _extract_user_query(prompt: str) -> str:
    """Strip planner wrapper prompts to get the raw user question."""
    patterns = [
        r"Generate a comprehensive response for:\s*(.+)",
        r"Synthesize findings for:\s*(.+)",
        r"Analyze the following query.*?:\s*(.+)",
        r"Gather context relevant to:\s*(.+)",
        r"Decompose the concept in:\s*(.+)",
        r"Retrieve knowledge for:\s*(.+)",
        r"Collect data for:\s*(.+)",
        r"Analyze market for:\s*(.+)",
        r"Detect trends for:\s*(.+)",
        r"Analyze requirements for:\s*(.+)",
        r"Plan structure for:\s*(.+)",
        r"Brainstorm ideas for:\s*(.+)",
        r"Evaluate ideas for:\s*(.+)",
        r"Deep analyze:\s*(.+)",
    ]
    for p in patterns:
        m = re.search(p, prompt, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return prompt


# ═══════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════

async def call_chatgpt(prompt: str, system_prompt: str = "", model: str = "gpt-4o-mini",
                        max_tokens: int = 1500, temperature: float = 0.7) -> dict:
    """
    Try providers in order: Gemini → OpenAI → Groq → Knowledge Base.
    Returns dict with content, tokens, model.
    """
    user_query = _extract_user_query(prompt)
    sys_prompt = system_prompt or SYSTEM_PROMPT

    # 1) Try Gemini (primary)
    if GEMINI_API_KEY:
        result = await _call_gemini(user_query, sys_prompt, max_tokens, temperature)
        if result:
            print(f"[AI] Gemini success — {result['tokens']} tokens")
            return result
        print("[AI] Gemini failed, trying OpenAI...")

    # 2) Try OpenAI
    if OPENAI_API_KEY:
        result = await _call_openai(user_query, sys_prompt, model, max_tokens, temperature)
        if result:
            print(f"[AI] OpenAI success — {result['tokens']} tokens")
            return result
        print("[AI] OpenAI failed, trying Groq...")

    # 3) Try Groq (free tier)
    if GROQ_API_KEY:
        result = await _call_groq(user_query, sys_prompt, max_tokens, temperature)
        if result:
            print(f"[AI] Groq success — {result['tokens']} tokens")
            return result
        print("[AI] Groq failed, using knowledge base...")

    # 4) Knowledge Base fallback
    print(f"[AI] Using knowledge base for: {user_query[:60]}...")
    return _knowledge_base_response(user_query)


# ═══════════════════════════════════════════════════════════════
# PROVIDER: Gemini (Primary — Google)
# ═══════════════════════════════════════════════════════════════

async def _call_gemini(query: str, system_prompt: str,
                        max_tokens: int, temperature: float) -> dict | None:
    """Call Google Gemini API via REST. Returns None on failure."""
    url = f"{GEMINI_URL}?key={GEMINI_API_KEY}"
    payload = {
        "contents": [
            {"parts": [{"text": query}]}
        ],
        "systemInstruction": {
            "parts": [{"text": system_prompt}]
        },
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            "topP": 0.95,
            "topK": 40,
        }
    }

    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(url, json=payload)
                if r.status_code == 429:
                    wait = int(r.headers.get("Retry-After", 10))
                    print(f"[Gemini] Rate limited, waiting {wait}s (attempt {attempt+1})")
                    await asyncio.sleep(wait)
                    continue
                r.raise_for_status()
                data = r.json()

                # Extract content
                content = ""
                if "candidates" in data and data["candidates"]:
                    parts = data["candidates"][0].get("content", {}).get("parts", [])
                    content = "".join(p.get("text", "") for p in parts)

                # Extract real token counts from usageMetadata
                usage = data.get("usageMetadata", {})
                prompt_tokens = usage.get("promptTokenCount", 0)
                completion_tokens = usage.get("candidatesTokenCount", 0)
                total_tokens = usage.get("totalTokenCount", 0)

                return {
                    "content": content,
                    "tokens": total_tokens,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "model": "gemini-2.5-flash",
                }
        except Exception as e:
            print(f"[Gemini] Error (attempt {attempt+1}): {e}")
            if attempt == 0:
                await asyncio.sleep(2)
    return None


# ═══════════════════════════════════════════════════════════════
# PROVIDER: OpenAI
# ═══════════════════════════════════════════════════════════════

async def _call_openai(query: str, system_prompt: str, model: str,
                        max_tokens: int, temperature: float) -> dict | None:
    """Call OpenAI API with 2 retries. Returns None on failure."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query},
    ]
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}

    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                r = await client.post(OPENAI_URL, json=payload, headers=headers)
                if r.status_code == 429:
                    err = r.json().get("error", {})
                    code = err.get("code", "")
                    if code == "insufficient_quota":
                        print(f"[OpenAI] No credits on account — skipping retries")
                        return None
                    wait = int(r.headers.get("Retry-After", 5))
                    print(f"[OpenAI] Rate limited, waiting {wait}s (attempt {attempt+1})")
                    await asyncio.sleep(wait)
                    continue
                r.raise_for_status()
                data = r.json()
                usage = data.get("usage", {})
                return {
                    "content": data["choices"][0]["message"]["content"],
                    "tokens": usage.get("total_tokens", 0),
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "model": model,
                }
        except Exception as e:
            print(f"[OpenAI] Error (attempt {attempt+1}): {e}")
            if attempt == 0:
                await asyncio.sleep(2)
    return None


# ═══════════════════════════════════════════════════════════════
# PROVIDER: Groq (Free API)
# ═══════════════════════════════════════════════════════════════

async def _call_groq(query: str, system_prompt: str,
                      max_tokens: int, temperature: float) -> dict | None:
    """Call Groq API (free, fast). Returns None on failure."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query},
    ]
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-70b-versatile",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                r = await client.post(GROQ_URL, json=payload, headers=headers)
                if r.status_code == 429:
                    wait = int(r.headers.get("Retry-After", 10))
                    print(f"[Groq] Rate limited, waiting {wait}s")
                    await asyncio.sleep(wait)
                    continue
                r.raise_for_status()
                data = r.json()
                usage = data.get("usage", {})
                return {
                    "content": data["choices"][0]["message"]["content"],
                    "tokens": usage.get("total_tokens", 0),
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "model": "groq-llama-3.1-70b",
                }
        except Exception as e:
            print(f"[Groq] Error (attempt {attempt+1}): {e}")
            if attempt == 0:
                await asyncio.sleep(2)
    return None


# ═══════════════════════════════════════════════════════════════
# KNOWLEDGE BASE — Comprehensive accurate answers
# ═══════════════════════════════════════════════════════════════

KB = {}

KB["python"] = """## What is Python?

**Python** is a high-level, interpreted, general-purpose programming language created by **Guido van Rossum** and first released in **1991**.

### Key Features
- **Easy to Learn** — Clean, readable syntax resembling English
- **Interpreted** — Runs line-by-line, no compilation needed
- **Dynamically Typed** — No need to declare variable types
- **Cross-Platform** — Runs on Windows, macOS, Linux
- **Huge Ecosystem** — 400,000+ packages on PyPI

### What is Python Used For?
1. **Web Development** — Django, Flask, FastAPI
2. **Data Science & Analytics** — Pandas, NumPy, Matplotlib
3. **Machine Learning & AI** — TensorFlow, PyTorch, scikit-learn
4. **Automation & Scripting** — File processing, task automation
5. **Desktop Applications** — Tkinter, PyQt
6. **Game Development** — Pygame
7. **DevOps & Cloud** — AWS SDK, Docker automation

### Python Code Example
```python
# Hello World
print("Hello, World!")

# Variables
name = "Python"
version = 3.12

# List comprehension
squares = [x**2 for x in range(10)]
print(squares)  # [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]

# Function
def greet(name):
    return f"Hello, {name}!"

# Class
class Animal:
    def __init__(self, name):
        self.name = name
    def speak(self):
        return f"{self.name} makes a sound"
```

### Why Python is #1
| Feature | Benefit |
|---------|---------|
| Simple syntax | Fast development |
| Large community | Great support |
| Rich libraries | Less code to write |
| Versatile | One language, many domains |

### Companies Using Python
Google, Netflix, Instagram, Spotify, Uber, Dropbox, Reddit, NASA.

Python is **#1 most popular programming language** worldwide (TIOBE Index, Stack Overflow Survey)."""

KB["dbms"] = """## What is DBMS?

**DBMS (Database Management System)** is software that manages databases — it allows users to **create, read, update, and delete (CRUD)** data efficiently and securely.

### Key Functions of DBMS
1. **Data Storage Management** — Organizes data in structured format
2. **Data Retrieval** — Query data using SQL or other languages
3. **Data Security** — Access control, authentication, encryption
4. **Concurrency Control** — Multiple users accessing data simultaneously
5. **Backup & Recovery** — Protect data against loss
6. **Data Integrity** — Enforce rules to maintain accuracy

### Types of DBMS

| Type | Description | Examples |
|------|-------------|----------|
| **Relational (RDBMS)** | Tables with rows & columns, uses SQL | MySQL, PostgreSQL, Oracle, SQL Server |
| **NoSQL** | Flexible schemas for unstructured data | MongoDB, Cassandra, Redis |
| **Hierarchical** | Tree-like parent-child structure | IBM IMS |
| **Network** | Graph structure with many-to-many relations | IDS, IDMS |
| **Object-Oriented** | Stores data as objects | db4o, ObjectDB |

### RDBMS Key Concepts
- **Table (Relation)** — Collection of rows and columns
- **Primary Key** — Unique identifier for each row
- **Foreign Key** — Links two tables together
- **Index** — Speeds up data retrieval
- **View** — Virtual table from a query
- **Stored Procedure** — Saved SQL code for reuse

### SQL Examples
```sql
-- Create a table
CREATE TABLE students (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    age INT,
    grade VARCHAR(10),
    email VARCHAR(255) UNIQUE
);

-- Insert data
INSERT INTO students (name, age, grade, email)
VALUES ('Alice', 20, 'A', 'alice@email.com');

-- Query data
SELECT name, grade FROM students WHERE age > 18 ORDER BY name;

-- Join tables
SELECT s.name, c.course_name
FROM students s
JOIN enrollments e ON s.id = e.student_id
JOIN courses c ON e.course_id = c.id;

-- Aggregate functions
SELECT grade, COUNT(*) as total, AVG(age) as avg_age
FROM students
GROUP BY grade;
```

### ACID Properties
| Property | Meaning |
|----------|---------|
| **Atomicity** | Transaction is all-or-nothing |
| **Consistency** | Data remains valid after transaction |
| **Isolation** | Transactions don't interfere with each other |
| **Durability** | Committed data persists even after crash |

### Normalization
- **1NF** — No repeating groups, atomic values
- **2NF** — No partial dependencies on composite key
- **3NF** — No transitive dependencies
- **BCNF** — Every determinant is a candidate key

### Popular DBMS Software
1. **MySQL** — Most popular open-source RDBMS (used by Facebook, Twitter)
2. **PostgreSQL** — Advanced open-source DB (used by Instagram, Uber)
3. **Oracle Database** — Enterprise standard (used by banks, governments)
4. **Microsoft SQL Server** — Enterprise DB for Windows ecosystem
5. **MongoDB** — Leading NoSQL document database
6. **SQLite** — Lightweight embedded database (used in mobile apps)
7. **Redis** — In-memory key-value store (caching, sessions)

### DBMS vs File System
| Feature | DBMS | File System |
|---------|------|-------------|
| Data Redundancy | Minimal | High |
| Data Consistency | Enforced | Not guaranteed |
| Security | Role-based access | Basic file permissions |
| Concurrent Access | Supported | Limited |
| Backup/Recovery | Built-in | Manual |
| Query Language | SQL | None |"""

KB["database"] = KB["dbms"]

KB["sql"] = """## What is SQL?

**SQL (Structured Query Language)** is the standard language for managing and querying **relational databases**.

### SQL Command Categories
| Category | Commands | Purpose |
|----------|----------|---------|
| **DDL** (Data Definition) | CREATE, ALTER, DROP, TRUNCATE | Define database structure |
| **DML** (Data Manipulation) | SELECT, INSERT, UPDATE, DELETE | Manipulate data |
| **DCL** (Data Control) | GRANT, REVOKE | Control access |
| **TCL** (Transaction Control) | COMMIT, ROLLBACK, SAVEPOINT | Manage transactions |

### SQL Examples
```sql
-- Create table
CREATE TABLE employees (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100),
    department VARCHAR(50),
    salary DECIMAL(10,2),
    hire_date DATE
);

-- Insert data
INSERT INTO employees (name, department, salary, hire_date)
VALUES ('John', 'Engineering', 95000, '2024-01-15');

-- Select with conditions
SELECT name, salary FROM employees
WHERE department = 'Engineering' AND salary > 80000
ORDER BY salary DESC;

-- Aggregate functions
SELECT department, COUNT(*) as count, AVG(salary) as avg_salary
FROM employees GROUP BY department HAVING COUNT(*) > 5;

-- JOIN example
SELECT e.name, d.department_name, e.salary
FROM employees e
INNER JOIN departments d ON e.department_id = d.id
WHERE d.location = 'New York';

-- Subquery
SELECT name FROM employees
WHERE salary > (SELECT AVG(salary) FROM employees);
```

### Key Concepts
- **Primary Key** — Unique row identifier
- **Foreign Key** — Links tables together
- **INDEX** — Speeds up queries
- **VIEW** — Virtual table from query
- **JOIN** — Combine data from multiple tables (INNER, LEFT, RIGHT, FULL)

### Popular SQL Databases
- **MySQL** — Most popular open-source (Facebook, Twitter)
- **PostgreSQL** — Advanced features (Instagram, Uber)
- **SQLite** — Lightweight embedded DB
- **SQL Server** — Microsoft enterprise
- **Oracle** — Enterprise standard"""

KB["javascript"] = """## What is JavaScript?

**JavaScript (JS)** is a high-level, dynamic programming language — one of the **three core web technologies** (HTML, CSS, JavaScript).

### Key Features
- **Client & Server Side** — Runs in browsers and on servers (Node.js)
- **Event-Driven** — Responds to user interactions in real-time
- **First-Class Functions** — Functions are values, can be passed around
- **Prototype-Based OOP** — Flexible object system
- **Asynchronous** — Non-blocking I/O with Promises and async/await
- **Dynamic Typing** — Types determined at runtime

### JavaScript Example
```javascript
// Variables
const name = "JavaScript";
let count = 0;

// Arrow function
const add = (a, b) => a + b;
console.log(add(5, 3)); // 8

// Array methods
const nums = [1, 2, 3, 4, 5];
const doubled = nums.map(n => n * 2);      // [2,4,6,8,10]
const evens = nums.filter(n => n % 2 === 0); // [2,4]

// Async/await
async function fetchData(url) {
    const response = await fetch(url);
    const data = await response.json();
    return data;
}

// DOM manipulation
document.getElementById('btn').addEventListener('click', () => {
    alert('Button clicked!');
});
```

### What JavaScript is Used For
1. **Frontend Web** — React, Vue.js, Angular, Svelte
2. **Backend** — Node.js, Express, Deno, Bun
3. **Mobile Apps** — React Native, Ionic
4. **Desktop Apps** — Electron (VS Code, Discord)
5. **Games** — Phaser, Three.js
6. **APIs** — REST, GraphQL

JavaScript powers **98% of all websites** and is the world's most widely used programming language."""

KB["react"] = """## What is React?

**React** (React.js) is an open-source **JavaScript library** for building user interfaces, created by **Meta (Facebook)** in 2013.

### Key Features
- **Component-Based** — Reusable, isolated UI components
- **Virtual DOM** — Efficient rendering without full page reloads
- **JSX** — Write HTML-like code inside JavaScript
- **Hooks** — useState, useEffect, useContext for state and side effects
- **One-Way Data Flow** — Predictable state management

### React Example
```jsx
import { useState, useEffect } from 'react';

function TodoApp() {
    const [todos, setTodos] = useState([]);
    const [input, setInput] = useState('');

    const addTodo = () => {
        setTodos([...todos, { text: input, done: false }]);
        setInput('');
    };

    return (
        <div>
            <h1>Todo List ({todos.length})</h1>
            <input value={input} onChange={e => setInput(e.target.value)} />
            <button onClick={addTodo}>Add</button>
            <ul>
                {todos.map((t, i) => (
                    <li key={i}>{t.text}</li>
                ))}
            </ul>
        </div>
    );
}
```

### React Ecosystem
- **Next.js** — Full-stack framework (SSR, SSG, API routes)
- **React Router** — Client-side routing
- **Redux / Zustand** — State management
- **React Query / TanStack** — Server state
- **Tailwind CSS** — Utility-first styling

Used by **Facebook, Instagram, Netflix, Airbnb, Uber, Twitter**."""

KB["ai"] = """## What is Artificial Intelligence (AI)?

**Artificial Intelligence (AI)** is the simulation of human intelligence by computer systems — learning, reasoning, problem-solving, perception, and decision-making.

### Types of AI
1. **Narrow AI (ANI)** — Specific tasks (ChatGPT, Siri, image recognition)
2. **General AI (AGI)** — Human-level intelligence across all domains (theoretical)
3. **Super AI (ASI)** — Beyond human intelligence (hypothetical)

### Key Subfields
- **Machine Learning (ML)** — Systems that learn from data
- **Deep Learning (DL)** — Neural networks with many layers
- **Natural Language Processing (NLP)** — Understanding human language (GPT, BERT)
- **Computer Vision** — Understanding images and video
- **Robotics** — Physical AI systems
- **Reinforcement Learning** — Learning through trial and error

### AI Tools & Frameworks
| Tool | Purpose | Creator |
|------|---------|---------|
| TensorFlow | Deep learning | Google |
| PyTorch | ML research & production | Meta |
| GPT-4 / ChatGPT | Language models | OpenAI |
| Stable Diffusion | Image generation | Stability AI |
| LangChain | LLM applications | Community |
| Hugging Face | Model hub | Community |

### Industry Impact
- **Healthcare** — diagnosis, drug discovery
- **Finance** — fraud detection, trading
- **Transportation** — self-driving cars
- **Education** — personalized learning
- **Entertainment** — recommendations

AI is projected to add **$15.7 trillion** to the global economy by 2030."""

KB["machine learning"] = """## What is Machine Learning?

**Machine Learning (ML)** is a subset of AI that enables systems to **learn and improve from experience** without explicit programming.

### Types of ML
1. **Supervised Learning** — Learns from labeled data
   - Classification: spam detection, image recognition
   - Regression: price prediction, forecasting

2. **Unsupervised Learning** — Finds patterns in unlabeled data
   - Clustering: customer segmentation
   - Dimensionality reduction: PCA, t-SNE

3. **Reinforcement Learning** — Learns through rewards/penalties
   - Game AI (AlphaGo), robotics, autonomous vehicles

### Popular Algorithms
- Linear / Logistic Regression
- Decision Trees & Random Forests
- Support Vector Machines (SVM)
- Neural Networks & Deep Learning
- K-Means Clustering
- Gradient Boosting (XGBoost, LightGBM)

### ML Workflow
```
Data Collection → Preprocessing → Feature Engineering → Model Training → Evaluation → Deployment
```

### Key Libraries
| Library | Use |
|---------|-----|
| scikit-learn | Classical ML algorithms |
| TensorFlow | Deep Learning (Google) |
| PyTorch | Research & production ML (Meta) |
| Keras | High-level neural networks |
| XGBoost | Gradient Boosting |
| Pandas | Data manipulation |"""

KB["html"] = """## What is HTML?

**HTML (HyperText Markup Language)** is the standard markup language for creating web pages. It defines the **structure and content** of a webpage.

### Key Elements
- **Headings** — `<h1>` to `<h6>`
- **Paragraphs** — `<p>`
- **Links** — `<a href="url">text</a>`
- **Images** — `<img src="url" alt="description">`
- **Lists** — `<ul>`, `<ol>`, `<li>`
- **Divs** — `<div>` container
- **Forms** — `<form>`, `<input>`, `<button>`

### HTML Example
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Website</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <header>
        <h1>Welcome to My Site</h1>
        <nav>
            <a href="/">Home</a>
            <a href="/about">About</a>
        </nav>
    </header>
    <main>
        <p>This is a paragraph.</p>
        <img src="photo.jpg" alt="A beautiful photo">
        <form>
            <input type="text" placeholder="Your name">
            <button type="submit">Submit</button>
        </form>
    </main>
    <footer>
        <p>&copy; 2026 My Website</p>
    </footer>
</body>
</html>
```

### HTML5 Features
- `<video>` and `<audio>` tags
- `<canvas>` for graphics
- Semantic tags: `<header>`, `<nav>`, `<main>`, `<article>`, `<footer>`
- Local Storage & Session Storage
- Geolocation, Drag & Drop APIs

HTML + **CSS** (styling) + **JavaScript** (interactivity) = modern web pages."""

KB["css"] = """## What is CSS?

**CSS (Cascading Style Sheets)** controls the **visual presentation** of HTML — colors, layouts, fonts, spacing, animations.

### Key Concepts
- **Selectors** — `.class`, `#id`, `element`, `[attr]`
- **Box Model** — margin > border > padding > content
- **Flexbox** — 1D layout (row or column)
- **CSS Grid** — 2D layout (rows + columns)
- **Media Queries** — Responsive design
- **Animations** — `@keyframes`, `transition`, `transform`

### CSS Example
```css
/* Modern dark card */
.card {
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 12px;
    padding: 24px;
    transition: all 0.3s ease;
}

.card:hover {
    transform: translateY(-4px);
    box-shadow: 0 0 20px rgba(99,102,241,0.35);
}

/* Flexbox layout */
.container {
    display: flex;
    gap: 16px;
    justify-content: center;
    align-items: center;
}

/* Grid layout */
.grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
}

/* Responsive */
@media (max-width: 768px) {
    .grid { grid-template-columns: 1fr; }
}
```

### Modern CSS Features
- CSS Variables: `--primary: #6366F1;`
- Container Queries
- CSS Nesting (native)
- `:has()` parent selector
- View Transitions API"""

KB["fastapi"] = """## What is FastAPI?

**FastAPI** is a modern, high-performance **Python web framework** for building APIs, created by **Sebastian Ramirez** in 2018.

### Key Features
- **Fastest Python framework** — on par with Node.js and Go
- **Auto API docs** — Swagger UI + ReDoc built-in
- **Type hints** — Python annotations for validation
- **Async support** — Native async/await
- **Pydantic** — Automatic data validation
- **WebSocket** — Real-time communication

### FastAPI Example
```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float
    in_stock: bool = True

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/items/")
async def create_item(item: Item):
    return {"item": item, "total": item.price * 1.1}

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    return {"item_id": item_id}
```

### Run It
```bash
pip install fastapi uvicorn
uvicorn main:app --reload
```

Visit `http://localhost:8000/docs` for interactive API docs.

Used by **Microsoft, Uber, Netflix** for production APIs."""

KB["java"] = """## What is Java?

**Java** is a high-level, object-oriented programming language released by **Sun Microsystems** in **1995** (now owned by **Oracle**).

### Key Features
- **Write Once, Run Anywhere** — JVM runs on all platforms
- **Object-Oriented** — Classes, inheritance, polymorphism
- **Strongly Typed** — Strict type checking
- **Garbage Collection** — Automatic memory management
- **Multi-threaded** — Built-in concurrency
- **Enterprise Standard** — Backbone of business software

### Java Example
```java
import java.util.ArrayList;
import java.util.List;

public class Main {
    public static void main(String[] args) {
        System.out.println("Hello, World!");

        List<String> languages = new ArrayList<>();
        languages.add("Java");
        languages.add("Python");
        languages.add("JavaScript");

        for (String lang : languages) {
            System.out.println(lang);
        }
    }
}
```

### Java Ecosystem
- **Spring Boot** — Enterprise web framework
- **Android** — Mobile development
- **Hibernate** — ORM
- **Maven / Gradle** — Build tools
- **Apache Kafka** — Distributed streaming

Used by **Google, Amazon, Netflix, LinkedIn, banks worldwide**. 9M+ developers."""

KB["node"] = """## What is Node.js?

**Node.js** is an open-source **JavaScript runtime** built on Chrome's V8 engine for running JS on the server.

### Key Features
- **Non-Blocking I/O** — Handles thousands of connections
- **Event-Driven** — Event loop for async operations
- **NPM** — 2M+ packages (largest registry)
- **Single Language** — JS for frontend + backend
- **Fast** — V8 compiles to machine code

### Node.js Example
```javascript
const express = require('express');
const app = express();

app.get('/', (req, res) => {
    res.json({ message: 'Hello from Node.js!' });
});

app.get('/users/:id', (req, res) => {
    res.json({ userId: req.params.id });
});

app.listen(3000, () => {
    console.log('Server running on port 3000');
});
```

### Frameworks
- **Express.js** — Minimal web framework
- **Next.js** — Full-stack React framework
- **NestJS** — Enterprise TypeScript framework
- **Fastify** — High-performance

Used by **Netflix, PayPal, LinkedIn, NASA, Walmart**."""

KB["git"] = """## What is Git?

**Git** is a free **distributed version control system** created by **Linus Torvalds** in 2005 for tracking code changes.

### Essential Git Commands
```bash
# Setup
git init                          # Initialize repository
git clone <url>                   # Clone remote repo

# Daily workflow
git status                        # Check status
git add .                         # Stage all changes
git commit -m "message"           # Commit changes
git push origin main              # Push to remote

# Branching
git branch feature-login          # Create branch
git checkout feature-login        # Switch branch
git merge feature-login           # Merge branch

# History
git log --oneline                 # View commit history
git diff                          # See changes
```

### Key Concepts
- **Repository** — Project tracked by Git
- **Commit** — Snapshot of changes
- **Branch** — Independent development line
- **Merge** — Combine branches
- **Pull Request** — Code review before merge
- **Clone / Fork** — Copy repository

### Platforms
- **GitHub** — 100M+ developers
- **GitLab** — DevOps + CI/CD
- **Bitbucket** — Atlassian ecosystem"""

KB["docker"] = """## What is Docker?

**Docker** is a platform for running applications in **containers** — lightweight, portable, isolated environments.

### Key Concepts
- **Image** — Blueprint for a container
- **Container** — Running instance of an image
- **Dockerfile** — Instructions to build image
- **Docker Compose** — Multi-container apps
- **Docker Hub** — Image registry

### Dockerfile Example
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]
```

### Docker Commands
```bash
docker build -t myapp .           # Build image
docker run -p 8000:8000 myapp     # Run container
docker ps                          # List containers
docker-compose up                  # Start multi-container
docker images                      # List images
docker stop <id>                   # Stop container
```

Used by **80%+ of organizations** for deployments."""

KB["api"] = """## What is an API?

**API (Application Programming Interface)** allows different software to **communicate with each other** through defined rules.

### Types of APIs
1. **REST** — HTTP methods (GET, POST, PUT, DELETE) — most common
2. **GraphQL** — Query language for APIs (Facebook)
3. **WebSocket** — Real-time bidirectional communication
4. **gRPC** — High-performance RPC (Google)
5. **SOAP** — XML-based enterprise protocol

### REST API Example
```
GET    /api/users          → List all users
GET    /api/users/1        → Get user by ID
POST   /api/users          → Create new user
PUT    /api/users/1        → Update user
DELETE /api/users/1        → Delete user
```

### HTTP Status Codes
| Code | Meaning |
|------|---------|
| 200 | OK — Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 404 | Not Found |
| 429 | Rate Limited |
| 500 | Server Error |

APIs power everything from weather apps to payment systems to social media."""

KB["typescript"] = """## What is TypeScript?

**TypeScript** is a **strongly-typed superset of JavaScript** from **Microsoft** (2012). It compiles to plain JavaScript.

### Key Features
- **Static Types** — Catch errors at compile time
- **Interfaces** — Define object shapes
- **Generics** — Reusable type-safe code
- **Enums** — Named constants
- **Full JS Compatibility** — Any JS is valid TS

### TypeScript Example
```typescript
// Type annotations
let name: string = "TypeScript";
let version: number = 5.3;

// Interface
interface User {
    id: number;
    name: string;
    email: string;
    age?: number; // optional
}

// Typed function
function getUser(id: number): User {
    return { id, name: "Alice", email: "alice@mail.com" };
}

// Generics
function first<T>(arr: T[]): T {
    return arr[0];
}
```

Used by **Angular, Next.js, VS Code, Deno** and most enterprise JS projects."""

KB["cloud"] = """## What is Cloud Computing?

**Cloud Computing** delivers computing services (servers, storage, databases, networking, software) over the **internet**.

### Service Models
| Model | What You Get | Examples |
|-------|-------------|----------|
| **IaaS** | Virtual machines, storage | AWS EC2, Azure VMs |
| **PaaS** | App development platform | Heroku, Google App Engine |
| **SaaS** | Ready-to-use software | Gmail, Slack, Salesforce |

### Top Providers
| Provider | Market Share |
|----------|-------------|
| AWS (Amazon) | ~32% |
| Azure (Microsoft) | ~23% |
| Google Cloud | ~11% |

### Key Services
- **Compute** — EC2, Lambda (serverless), Azure Functions
- **Storage** — S3, Azure Blob, Google Cloud Storage
- **Database** — RDS, DynamoDB, Cloud SQL
- **AI/ML** — SageMaker, Vertex AI
- **Containers** — ECS, Kubernetes (EKS, GKE)

Benefits: **Scalability, flexibility, cost savings, global reach**."""

KB["cloud computing"] = KB["cloud"]

KB["data structure"] = """## What are Data Structures?

**Data Structures** are ways of organizing and storing data for efficient access and modification.

### Linear Data Structures
| Structure | Description | Use Case |
|-----------|-------------|----------|
| **Array** | Fixed-size indexed collection | Fast random access |
| **Linked List** | Nodes connected by pointers | Dynamic insertion/deletion |
| **Stack** | LIFO (Last In, First Out) | Undo operations, parsing |
| **Queue** | FIFO (First In, First Out) | Task scheduling, BFS |

### Non-Linear Data Structures
| Structure | Description | Use Case |
|-----------|-------------|----------|
| **Tree** | Hierarchical nodes | File systems, DOM |
| **Binary Search Tree** | Sorted tree | Fast search O(log n) |
| **Heap** | Priority-based tree | Priority queues |
| **Graph** | Nodes + edges | Social networks, maps |
| **Hash Table** | Key-value pairs | Dictionaries, caching |

### Time Complexity
| Operation | Array | Linked List | BST | Hash Table |
|-----------|-------|-------------|-----|------------|
| Access | O(1) | O(n) | O(log n) | O(1) |
| Search | O(n) | O(n) | O(log n) | O(1) |
| Insert | O(n) | O(1) | O(log n) | O(1) |
| Delete | O(n) | O(1) | O(log n) | O(1) |

### Python Example
```python
# Stack
stack = []
stack.append(1)  # push
stack.append(2)
stack.pop()      # returns 2

# Queue
from collections import deque
queue = deque()
queue.append(1)    # enqueue
queue.popleft()    # dequeue

# Dictionary (Hash Table)
cache = {"key1": "value1", "key2": "value2"}
print(cache["key1"])  # O(1) access
```"""

KB["data structures"] = KB["data structure"]
KB["dsa"] = KB["data structure"]

KB["os"] = """## What is an Operating System (OS)?

An **Operating System** is system software that manages **hardware resources** and provides services for applications.

### Key Functions
1. **Process Management** — Creating, scheduling, terminating processes
2. **Memory Management** — RAM allocation, virtual memory, paging
3. **File System** — File creation, deletion, organization
4. **I/O Management** — Device drivers, input/output handling
5. **Security** — User authentication, access control

### Types of OS
| Type | Description | Examples |
|------|-------------|----------|
| **Desktop** | Personal computers | Windows, macOS, Linux |
| **Mobile** | Smartphones/tablets | Android, iOS |
| **Server** | Data centers | Linux (Ubuntu, CentOS), Windows Server |
| **Embedded** | IoT devices | RTOS, Embedded Linux |
| **Real-Time** | Time-critical systems | VxWorks, QNX |

### Key Concepts
- **Process vs Thread** — Process is independent; thread shares process memory
- **Deadlock** — Two+ processes waiting forever for each other's resources
- **Virtual Memory** — Uses disk as extended RAM (paging/swapping)
- **Scheduling** — FCFS, SJF, Round Robin, Priority
- **Semaphore / Mutex** — Synchronization mechanisms

### Popular Operating Systems
- **Windows** — 73% desktop share (Microsoft)
- **macOS** — 15% desktop share (Apple)
- **Linux** — 96% of servers, Android kernel
- **Android** — 72% mobile share (Google)
- **iOS** — 27% mobile share (Apple)"""

KB["operating system"] = KB["os"]

KB["networking"] = """## What is Computer Networking?

**Computer Networking** connects devices to share data and resources through wired or wireless connections.

### OSI Model (7 Layers)
| Layer | Name | Protocol Examples |
|-------|------|-------------------|
| 7 | Application | HTTP, FTP, SMTP, DNS |
| 6 | Presentation | SSL/TLS, JPEG, ASCII |
| 5 | Session | NetBIOS, RPC |
| 4 | Transport | TCP, UDP |
| 3 | Network | IP, ICMP, ARP |
| 2 | Data Link | Ethernet, Wi-Fi, MAC |
| 1 | Physical | Cables, signals |

### TCP/IP Model (4 Layers)
1. **Application** — HTTP, DNS, FTP
2. **Transport** — TCP (reliable), UDP (fast)
3. **Internet** — IP addressing, routing
4. **Network Access** — Physical transmission

### Key Protocols
- **HTTP/HTTPS** — Web browsing (port 80/443)
- **TCP** — Reliable delivery (handshake)
- **UDP** — Fast, unreliable (streaming, gaming)
- **DNS** — Domain name to IP resolution
- **DHCP** — Automatic IP assignment
- **SSH** — Secure remote access (port 22)
- **FTP** — File transfer (port 21)

### IP Addressing
- **IPv4** — 32-bit (e.g., 192.168.1.1)
- **IPv6** — 128-bit (e.g., 2001:db8::1)
- **Subnet Mask** — Defines network/host portions
- **Public IP** — Internet-facing
- **Private IP** — Internal network (192.168.x.x, 10.x.x.x)"""

KB["network"] = KB["networking"]
KB["computer network"] = KB["networking"]

KB["c++"] = """## What is C++?

**C++** is a high-performance, general-purpose programming language created by **Bjarne Stroustrup** in **1979** as an extension of C.

### Key Features
- **Object-Oriented** — Classes, inheritance, polymorphism
- **Low-Level Access** — Direct memory manipulation (pointers)
- **High Performance** — Compiled to machine code
- **STL** — Standard Template Library (vectors, maps, algorithms)
- **Multi-Paradigm** — OOP, procedural, generic, functional

### C++ Example
```cpp
#include <iostream>
#include <vector>
#include <string>
using namespace std;

class Animal {
public:
    string name;
    Animal(string n) : name(n) {}
    virtual void speak() {
        cout << name << " makes a sound" << endl;
    }
};

class Dog : public Animal {
public:
    Dog(string n) : Animal(n) {}
    void speak() override {
        cout << name << " says Woof!" << endl;
    }
};

int main() {
    vector<int> nums = {1, 2, 3, 4, 5};
    for (int n : nums) cout << n << " ";

    Dog d("Rex");
    d.speak(); // Rex says Woof!
    return 0;
}
```

### Used In
- Game engines (Unreal Engine)
- Operating systems (Windows, Linux kernel modules)
- Browsers (Chrome, Firefox)
- Embedded systems
- Competitive programming"""

KB["c language"] = """## What is C?

**C** is a general-purpose, procedural programming language created by **Dennis Ritchie** at Bell Labs in **1972**.

### Key Features
- **Low-Level** — Direct hardware/memory access
- **Fast** — Compiled to efficient machine code
- **Portable** — Runs on virtually any platform
- **Foundation** — C++, Java, Python all influenced by C
- **Pointers** — Direct memory manipulation

### C Example
```c
#include <stdio.h>
#include <stdlib.h>

int main() {
    printf("Hello, World!\\n");

    // Variables
    int age = 25;
    float gpa = 3.8;
    char grade = 'A';

    // Array
    int nums[] = {10, 20, 30, 40, 50};
    for (int i = 0; i < 5; i++) {
        printf("%d ", nums[i]);
    }

    // Pointer
    int *ptr = &age;
    printf("\\nAge: %d, Address: %p", *ptr, ptr);

    return 0;
}
```

### Used In
- Operating Systems (Linux, Windows kernel)
- Embedded Systems
- Compilers
- Database engines (MySQL, PostgreSQL)
- IoT devices"""

KB["c"] = KB["c language"]


# ═══════════════════════════════════════════════════════════════
# KNOWLEDGE BASE LOOKUP
# ═══════════════════════════════════════════════════════════════

def _knowledge_base_response(query: str) -> dict:
    """Match query against knowledge base for accurate answers."""
    q = query.lower().strip().rstrip("?.,!")

    # Score each KB entry
    best_content = None
    best_score = 0

    for key, content in KB.items():
        score = 0
        # Exact key match in query
        if key in q:
            score += 10 + len(key)
        # Query contained in key
        if q in key:
            score += 8
        # Word-level matching
        for word in key.split():
            if word in q.split():
                score += 3

        if score > best_score:
            best_score = score
            best_content = content

    if best_content and best_score >= 3:
        tokens = len(best_content.split()) * 2
        return {
            "content": best_content,
            "tokens": tokens,
            "prompt_tokens": len(query.split()) * 2,
            "completion_tokens": tokens,
            "model": "knowledge-base",
        }

    # Generic smart response
    content = _generate_smart_answer(query)
    tokens = len(content.split()) * 2
    return {
        "content": content,
        "tokens": tokens,
        "prompt_tokens": len(query.split()) * 2,
        "completion_tokens": tokens,
        "model": "smart-fallback",
    }


def _generate_smart_answer(query: str) -> str:
    """Generate a topic-aware response when no KB match found."""
    stop = {"what", "is", "are", "how", "does", "do", "can", "the", "a", "an", "of",
            "in", "to", "for", "and", "or", "explain", "tell", "me", "about", "please",
            "generate", "create", "make", "give", "describe", "define", "research",
            "analyze", "report", "comprehensive", "response", "this", "that", "it", "its", "why"}

    words = query.lower().split()
    topic_words = [w.strip("?.,!") for w in words if w.strip("?.,!") not in stop and len(w) > 2]
    topic = " ".join(topic_words[:5]) if topic_words else query

    return f"""## {topic.title()}

### Overview
**{topic.title()}** is an important concept in its domain. Here is a comprehensive overview covering key aspects.

### Key Concepts
1. **Definition** — {topic.title()} refers to the fundamental principles and practices in this area
2. **Applications** — Used across multiple industries and real-world scenarios
3. **Core Components** — Consists of several interconnected parts that work together
4. **Best Practices** — Industry standards guide effective implementation
5. **Tools & Technologies** — Various tools and frameworks support working with {topic}

### Why It Matters
- Widely used in professional and academic settings
- Understanding {topic} provides a strong foundation for related fields
- Continuous evolution with new developments and improvements
- Strong community support and extensive documentation available

### Getting Started
1. Study the official documentation and tutorials
2. Take online courses (Coursera, Udemy, freeCodeCamp)
3. Practice with hands-on projects
4. Join communities (Stack Overflow, Reddit, Discord)
5. Build real-world applications to solidify understanding

### Resources
- Official documentation and guides
- YouTube tutorials and conference talks
- Open-source projects on GitHub
- Books and academic papers

*Note: For detailed, real-time AI responses, add OpenAI credits at platform.openai.com/account/billing or set a free Groq API key (groq.com).*"""
