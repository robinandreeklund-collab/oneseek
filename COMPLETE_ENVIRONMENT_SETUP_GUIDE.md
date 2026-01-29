# Complete Environment Setup Guide

## Svar på Dina Tre Frågor

### 1. Ska jag installera npm i den lokala venv miljön?

**Svar: NEJ**

npm är en Node.js package manager och hör inte hemma i en Python virtual environment. Håll dem separerade:

- **Python venv** = Python-paket (pytest, Flask, pandas, etc.)
- **npm/Node.js** = JavaScript-paket (Next.js, React, etc.)

**Varför separat?**
- Olika ekosystem med olika verktyg
- Standard practice i industrin
- Enklare att underhålla
- Mindre förvirring

### 2. Ska jag installera Next.js i venv?

**Svar: NEJ**

Next.js är ett JavaScript framework som installeras med npm, inte i Python venv.

**Rätt sätt:**
```bash
# För JavaScript/Next.js projekt:
npm install next react react-dom

# INTE i Python venv!
```

### 3. Integrera Python i Next.js med Pyodide?

**Svar: JA! Detta är en bra idé.**

Pyodide låter dig köra Python-kod direkt i browsern via WebAssembly. Perfekt för demos och interaktiva Python-exempel.

---

## Fullständig Miljö Översikt

### Python Environment (Virtual Environment)

**Location**: `{CODE_WORKSPACE_ROOT}/workspace_venv/`

**Innehåll** (från `workspace_requirements.txt`):
```txt
# Testing Framework
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-mock>=3.11.1

# Code Quality & Linting
pylint>=3.0.0
flake8>=6.1.0
black>=23.7.0
isort>=5.12.0

# Type Checking
mypy>=1.5.0

# Code Coverage
coverage>=7.3.0

# Web Frameworks
flask>=3.0.0
flask-restful>=0.3.10

# Common Dependencies
requests>=2.31.0
python-dotenv>=1.0.0
pandas>=2.0.0
numpy>=1.24.0
```

**Användning**:
```python
# Modellen använder:
import os
workspace_root = os.getenv("CODE_WORKSPACE_ROOT", "/tmp/oneseek_workspace")
venv_python = f"{workspace_root}/workspace_venv/bin/python"  # Linux/Mac
# eller
venv_python = f"{workspace_root}\\workspace_venv\\Scripts\\python.exe"  # Windows

# Kör kod:
subprocess.run([venv_python, "script.py"])
```

### JavaScript/Node.js Environment

**Location**: Global eller per-projekt

**Installation**:
```bash
# 1. Installera Node.js (om inte redan gjort)
# Windows: Ladda ner från https://nodejs.org
# Linux: sudo apt install nodejs npm
# Mac: brew install node

# 2. Verifiera installation
node --version  # v18.x eller senare
npm --version   # 9.x eller senare
```

**För Next.js projekt**:
```bash
cd frontend  # eller ditt projekt directory

# Installera Next.js och beroenden
npm install next@latest react@latest react-dom@latest

# För TypeScript (rekommenderat)
npm install --save-dev typescript @types/react @types/node
```

---

## Pyodide Integration i Next.js

### Vad är Pyodide?

Pyodide är Python som körs i browsern via WebAssembly. Det låter dig:
- Köra Python-kod direkt i webbläsaren
- Ingen backend behövs för enkla Python-operationer
- Perfekt för demos, tutorials och interaktiva exempel

### Installation

```bash
cd frontend  # Ditt Next.js projekt
npm install pyodide
```

### Implementering

#### 1. Skapa Python Runner Component

**`components/PythonRunner.tsx`**:
```typescript
'use client';

import { useEffect, useState } from 'react';
import { loadPyodide, PyodideInterface } from 'pyodide';

export function PythonRunner() {
  const [pyodide, setPyodide] = useState<PyodideInterface | null>(null);
  const [code, setCode] = useState<string>('print("Hello from Python!")');
  const [output, setOutput] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    async function loadPyodideInstance() {
      try {
        setLoading(true);
        const pyodideInstance = await loadPyodide({
          indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.24.1/full/',
        });
        setPyodide(pyodideInstance);
        setLoading(false);
      } catch (err) {
        setError('Failed to load Pyodide: ' + err);
        setLoading(false);
      }
    }
    loadPyodideInstance();
  }, []);

  const runPythonCode = async () => {
    if (!pyodide) return;

    try {
      setError('');
      // Omdirigera stdout
      await pyodide.runPythonAsync(`
import sys
from io import StringIO
sys.stdout = StringIO()
      `);

      // Kör användarens kod
      await pyodide.runPythonAsync(code);

      // Hämta output
      const stdout = await pyodide.runPythonAsync('sys.stdout.getvalue()');
      setOutput(stdout as string);
    } catch (err: any) {
      setError('Python Error: ' + err.message);
    }
  };

  if (loading) {
    return <div className="p-4">Loading Python environment...</div>;
  }

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-2xl font-bold">Python in Browser</h2>
      
      <div>
        <label className="block text-sm font-medium mb-2">Python Code:</label>
        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          className="w-full h-32 p-2 border rounded font-mono"
          placeholder="Enter Python code..."
        />
      </div>

      <button
        onClick={runPythonCode}
        className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
      >
        Run Python
      </button>

      {error && (
        <div className="p-3 bg-red-100 border border-red-400 rounded">
          <pre className="text-red-700 text-sm">{error}</pre>
        </div>
      )}

      {output && (
        <div className="p-3 bg-gray-100 border rounded">
          <label className="block text-sm font-medium mb-2">Output:</label>
          <pre className="text-sm">{output}</pre>
        </div>
      )}
    </div>
  );
}
```

#### 2. Använd Component i Din App

**`app/python-demo/page.tsx`**:
```typescript
import { PythonRunner } from '@/components/PythonRunner';

export default function PythonDemoPage() {
  return (
    <div className="container mx-auto py-8">
      <h1 className="text-3xl font-bold mb-6">Python Demo</h1>
      <PythonRunner />
    </div>
  );
}
```

#### 3. Pyodide API Exempel

```typescript
// Ladda Python-paket
await pyodide.loadPackage('numpy');
await pyodide.loadPackage('pandas');

// Kör Python-kod
const result = await pyodide.runPythonAsync(`
import numpy as np
arr = np.array([1, 2, 3, 4, 5])
arr.mean()
`);

// Konvertera Python-objekt till JavaScript
const pythonDict = await pyodide.runPythonAsync(`
{"name": "John", "age": 30}
`);
const jsObject = pythonDict.toJs();

// Anropa Python-funktioner från JavaScript
await pyodide.runPythonAsync(`
def greet(name):
    return f"Hello, {name}!"
`);
const greet = pyodide.globals.get('greet');
const greeting = greet('World');
```

---

## När Modellen Använder Vad

### För Python-Kod

**Använd Python venv**:
```python
import os
import subprocess

workspace_root = os.getenv("CODE_WORKSPACE_ROOT", "/tmp/oneseek_workspace")
venv_python = f"{workspace_root}/workspace_venv/bin/python"

# Kör Python-script
subprocess.run([venv_python, "my_script.py"])

# Kör pytest
subprocess.run([venv_python, "-m", "pytest", "test_file.py"])

# Kör pylint
subprocess.run([venv_python, "-m", "pylint", "module.py"])
```

### För JavaScript/Next.js Kod

**Använd npm och node**:
```bash
# Installera beroenden
npm install

# Kör Next.js dev server
npm run dev

# Bygg för produktion
npm run build

# Kör tests
npm test
```

### För Python i Browser (Demo)

**Använd Pyodide**:
```typescript
// I React component
const pyodide = await loadPyodide();
const result = await pyodide.runPythonAsync(`
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

fibonacci(10)
`);
```

---

## Fullständig Setup Checklista

### Python Environment ✅

- [x] Python venv skapad i workspace
- [x] Location: `{CODE_WORKSPACE_ROOT}/workspace_venv/`
- [x] Alla testing tools installerade (pytest, pylint, mypy)
- [x] Web frameworks installerade (Flask)
- [x] Common libraries installerade (requests, pandas, numpy)
- [x] Modellen vet var venv finns
- [x] Ingen installation behövs under körning

### JavaScript Environment ✅

- [ ] Node.js installerat (v18+ rekommenderat)
- [ ] npm installerat (9+ rekommenderat)
- [ ] Next.js projekt setup (om du har frontend)
- [ ] TypeScript konfigurerat (rekommenderat)
- [ ] Pyodide installerat (om du vill ha Python i browser)

### Dokumentation ✅

- [x] Python venv guide
- [x] JavaScript setup guide
- [x] Pyodide integration guide
- [x] När man använder vad
- [x] Exempel för alla scenarios

---

## Varför Denna Setup?

### Fördelar med Separation

**Python venv (Separate)**:
- ✅ Isolerad Python miljö
- ✅ Inga konflikter med system Python
- ✅ Reproducerbar environment
- ✅ Standard practice

**npm/Node.js (Separate)**:
- ✅ Standard JavaScript ekosystem
- ✅ Millioner av paket tillgängliga
- ✅ Etablerade verktyg och workflows
- ✅ Industry standard

**Pyodide (In Browser)**:
- ✅ Python utan backend
- ✅ Perfekt för demos
- ✅ Instant execution
- ✅ Säkert (sandboxed)

### Vad Modellen Får

1. **Python venv** - Alla Python verktyg redo att användas
2. **npm/node** - Standard JavaScript tools (om installerade)
3. **Pyodide** - Python i browser för demos (om installerat)
4. **Dokumentation** - Exakt vad som finns var

**Resultat**: Inga installationsfel, snabbare execution, tydlig struktur.

---

## Vanliga Användningsfall

### Användningsfall 1: Python Backend

```python
# Modellen skapar Flask API
# Använder: Python venv

import os
workspace_root = os.getenv("CODE_WORKSPACE_ROOT")
venv_python = f"{workspace_root}/workspace_venv/bin/python"

# Skapa app.py
# Kör: python app.py
subprocess.run([venv_python, "app.py"])

# Testa: pytest
subprocess.run([venv_python, "-m", "pytest"])
```

### Användningsfall 2: Next.js Frontend

```bash
# Modellen skapar Next.js komponenter
# Använder: npm/node

# Kör dev server
npm run dev

# Bygg
npm run build
```

### Användningsfall 3: Python Demo i UI

```typescript
// Modellen skapar interaktiv Python demo
// Använder: Pyodide

const pyodide = await loadPyodide();
const result = await pyodide.runPythonAsync(userCode);
```

---

## Troubleshooting

### Python venv fungerar inte

**Problem**: "python not found"

**Lösning**:
```bash
# Verifiera venv finns
ls {CODE_WORKSPACE_ROOT}/workspace_venv/

# Verifiera Python finns i venv
ls {CODE_WORKSPACE_ROOT}/workspace_venv/bin/python  # Linux/Mac
dir {CODE_WORKSPACE_ROOT}\workspace_venv\Scripts\python.exe  # Windows
```

### npm fungerar inte

**Problem**: "npm command not found"

**Lösning**:
```bash
# Installera Node.js från nodejs.org
# Eller via package manager:
# Windows: choco install nodejs
# Linux: sudo apt install nodejs npm
# Mac: brew install node

# Verifiera:
node --version
npm --version
```

### Pyodide laddar inte

**Problem**: "Failed to load Pyodide"

**Lösning**:
```typescript
// Använd specifik version
const pyodide = await loadPyodide({
  indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.24.1/full/',
});

// Eller lokal installation
npm install pyodide
```

---

## Sammanfattning

### Svar på Dina Frågor

1. **npm i venv?** → **NEJ** - Håll separat (npm är för JavaScript)
2. **Next.js i venv?** → **NEJ** - Installera via npm (JavaScript framework)
3. **Pyodide integration?** → **JA** - Guide och exempel ovan

### Rätt Setup

```
Workspace:
├── Python venv (Python tools) ✓
├── npm/Node.js (JavaScript tools) ✓
└── Pyodide (Python in browser) ✓

Alla tre kompletta, inga installationer under körning! ✓
```

### Modellen Förstår

- Python kod → Python venv
- JavaScript kod → npm/node
- Python demos → Pyodide
- Allt förkonfigurerat!

**Resultat**: Snabbare utveckling, färre fel, tydligare struktur! 🎉
