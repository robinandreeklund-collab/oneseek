# 🚀 OneSeek.ai – Snabbstartsguide (Steg-för-Steg)

Denna guide tar dig genom hela installationen från början till slut. Följ varje steg noggrant!

## 📋 Innan du börjar

### Vad du behöver:
- [ ] **Dator med NVIDIA GPU** (minst 24 GB VRAM, t.ex. RTX 5090, RTX 4090, eller RTX 3090)
- [ ] **Windows, Linux eller macOS**
- [ ] **Internetanslutning** för nedladdningar
- [ ] **~30-60 minuter** för första gången

### Vad du kommer att installera:
1. Python 3.11+
2. Node.js 18+
3. Git
4. vLLM (för lokal AI)
5. OneSeek backend och frontend

---

## 📦 Steg 1: Installera grundläggande verktyg

### Windows:

#### 1.1 Installera Python
1. Gå till https://www.python.org/downloads/
2. Ladda ner Python 3.11 eller senare
3. **VIKTIGT:** Kryssa i "Add Python to PATH" under installationen
4. Verifiera:
   ```cmd
   python --version
   ```
   Du ska se något som `Python 3.11.x`

#### 1.2 Installera Node.js
1. Gå till https://nodejs.org/
2. Ladda ner LTS-versionen (20.x rekommenderas)
3. Installera med standard-inställningar
4. Verifiera:
   ```cmd
   node --version
   npm --version
   ```

#### 1.3 Installera Git
1. Gå till https://git-scm.com/download/win
2. Ladda ner och installera
3. Verifiera:
   ```cmd
   git --version
   ```

### Linux (Ubuntu/Debian):

```bash
# Uppdatera paketlistan
sudo apt update

# Installera Python 3.11+
sudo apt install python3.11 python3.11-venv python3-pip

# Installera Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install nodejs

# Installera Git
sudo apt install git

# Verifiera installationer
python3.11 --version
node --version
git --version
```

### macOS:

```bash
# Installera Homebrew om du inte har det
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Installera Python
brew install python@3.11

# Installera Node.js
brew install node@20

# Installera Git
brew install git

# Verifiera
python3.11 --version
node --version
git --version
```

---

## 🔧 Steg 2: Klona och förbered projektet

### 2.1 Klona repot

```bash
# Gå till en mapp där du vill ha projektet, t.ex.:
cd ~/Documents  # Linux/Mac
# eller
cd C:\Users\DittNamn\Documents  # Windows

# Klona projektet
git clone https://github.com/robinandreeklund-collab/oneseek.git
cd oneseek
```

**Förväntat resultat:** Du har nu en `oneseek` mapp med alla filer.

### 2.2 Kör setup-scriptet (rekommenderat)

**Linux/macOS:**
```bash
chmod +x setup.sh
./setup.sh
```

**Windows (Git Bash):**
```bash
bash setup.sh
```

**Windows (manuell setup – följ steg 3-5 nedan istället)**

---

## 🐍 Steg 3: Setup Backend (Python)

### 3.1 Skapa Python virtual environment

```bash
cd backend

# Skapa venv
python3 -m venv venv

# Aktivera venv
# Linux/macOS:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

**Förväntat resultat:** Du ska se `(venv)` före din prompt.

### 3.2 Installera Python-paket

```bash
# Uppgradera pip först
pip install --upgrade pip

# Installera alla dependencies
pip install -r requirements.txt
```

**Detta tar 2-5 minuter.** Du ska se meddelanden om nedladdning och installation.

### 3.3 Skapa konfigurationsfil

```bash
# Kopiera exempel-filen
cp .env.example .env

# Öppna .env i en textredigerare
# Windows: notepad .env
# Linux: nano .env
# macOS: open -e .env
```

**Redigera `.env` – fyll i dessa värden:**

```bash
# vLLM (kommer att köras i steg 5)
VLLM_URL=http://localhost:8000/v1
VLLM_MODEL=Qwen/Qwen2.5-14B-Instruct-AWQ

# Vespa (lämna tomma för nu – ska fyllas i steg 6)
# VESPA_URL=
# VESPA_CERT_PATH=
# VESPA_KEY_PATH=

# Valfria inställningar
MODEL_TEMPERATURE=0.7
MAX_TOKENS=2048
```

**Spara och stäng filen.**

### 3.4 Testa backend

```bash
# Kör test-scriptet
python test_setup.py
```

**Förväntat resultat:** Du ska se gröna checkmarks (✓) för alla importer och moduler.

---

## 🌐 Steg 4: Setup Frontend (Node.js)

### 4.1 Öppna ny terminal

**VIKTIGT:** Öppna en **ny terminal/kommandotolk** så att backend-terminalen kan fortsätta köra senare.

```bash
# Gå till frontend-mappen
cd /path/to/oneseek/frontend
```

### 4.2 Installera npm-paket

```bash
npm install
```

**Detta tar 3-7 minuter.** Du kommer se många paket installeras.

### 4.3 Skapa frontend-konfiguration

```bash
# Kopiera exempel-filen
cp .env.local.example .env.local

# Öppna .env.local i textredigerare
# Windows: notepad .env.local
# Linux: nano .env.local
# macOS: open -e .env.local
```

**Innehåll i `.env.local`:**

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8001
```

**Spara och stäng.**

---

## 🤖 Steg 5: Starta vLLM (Lokal AI)

Detta är den viktigaste delen – här startar du den lokala AI-modellen.

### 5.1 Öppna en tredje terminal

**Du ska nu ha 3 terminaler:**
1. Backend-terminal (från steg 3)
2. Frontend-terminal (från steg 4)  
3. **NY terminal för vLLM** ← vi ska använda denna nu

### 5.2 Installera vLLM

**I den nya terminalen:**

```bash
# Skapa separat venv för vLLM (rekommenderas)
python3 -m venv ~/vllm-env

# Aktivera
# Linux/macOS:
source ~/vllm-env/bin/activate

# Windows:
~/vllm-env/Scripts/activate

# Installera vLLM
pip install vllm
```

**Detta kan ta 10-15 minuter** första gången.

### 5.3 Starta vLLM-servern

**För RTX 5090 / RTX 4090 (24 GB VRAM):**

```bash
vllm serve Qwen/Qwen2.5-14B-Instruct-AWQ \
  --dtype auto \
  --quantization awq \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.92 \
  --host 0.0.0.0 \
  --port 8000
```

**För mindre GPU (t.ex. RTX 3090 med 24 GB):**

```bash
vllm serve meta-llama/Llama-3.1-8B-Instruct \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.85 \
  --port 8000
```

**För CPU-testning (väldigt långsamt):**

```bash
vllm serve meta-llama/Llama-3.1-8B-Instruct \
  --device cpu \
  --max-model-len 2048 \
  --port 8000
```

### 5.4 Vänta tills modellen är laddad

**Du kommer att se:**
```
INFO: Loading model...
INFO: Model loaded successfully
INFO: Uvicorn running on http://0.0.0.0:8000
```

**Detta kan ta:**
- **Första gången:** 5-10 minuter (modellen laddas ner från Hugging Face)
- **Efterföljande gånger:** 30-60 sekunder

**LÄMNA DENNA TERMINAL ÖPPEN** – vLLM måste köra hela tiden.

---

## 🔌 Steg 6: Setup Vespa Cloud (Valfritt men rekommenderat)

RAG-funktionen kräver Vespa Cloud. Du kan hoppa över detta för att testa utan RAG först.

### 6.1 Skapa Vespa Cloud-konto

1. Gå till https://console.vespa-cloud.com
2. Klicka "Sign up" och registrera dig (Google/GitHub fungerar)
3. Skapa en **tenant** (t.ex. "oneseek-demo")
4. **Ingen kreditkort krävs** – du får $300 i gratiskredit

### 6.2 Hämta säkerhetscertifikat

1. I Vespa Console, gå till **Security** (vänster sidofält)
2. Under "Data Plane", klicka **Download**
3. Du får två filer:
   - `data-plane-public-cert.pem` (certifikat)
   - `data-plane-private-key.pem` (privat nyckel)
4. Spara dem på ett säkert ställe, t.ex.:
   - Linux/macOS: `~/vespa-certs/`
   - Windows: `C:\Users\DittNamn\vespa-certs\`

### 6.3 Uppdatera backend/.env

Öppna `backend/.env` igen och lägg till:

```bash
VESPA_URL=https://ditt-app.ditt-tenant.vespa-cloud.net
VESPA_CERT_PATH=/path/to/data-plane-public-cert.pem
VESPA_KEY_PATH=/path/to/data-plane-private-key.pem
```

**Byt ut sökvägar till där du sparade certifikaten!**

### 6.4 Deploya Vespa-applikationen

**I backend-terminalen (med venv aktiverad):**

```bash
cd backend
source venv/bin/activate  # Om inte redan aktiverad

python deploy_vespa.py
```

**Du kommer att bli tillfrågad:**
```
Enter your Vespa Cloud tenant name: 
```
Skriv in tenant-namnet du skapade (t.ex. "oneseek-demo").

```
Enter application name [oneseek-rag]: 
```
Tryck Enter (använd default) eller skriv ett eget namn.

**Detta tar 3-5 minuter.** Du kommer se:
```
✓ Deployment complete!
✓ Successfully fed 15 documents!
```

---

## 🎬 Steg 7: Starta applikationen

Nu är allt installerat! Dags att starta allt.

### 7.1 Kontrollera att vLLM körs

I vLLM-terminalen, kolla att du ser:
```
INFO: Uvicorn running on http://0.0.0.0:8000
```

**Om inte:** Gå tillbaka till Steg 5.3 och starta vLLM.

### 7.2 Starta backend

**I backend-terminalen:**

```bash
cd backend
source venv/bin/activate  # Om inte redan aktiverad

uvicorn app:app --reload --port 8001
```

**Du ska se:**
```
INFO: Uvicorn running on http://127.0.0.1:8001 (Press CTRL+C to quit)
INFO: Application startup complete.
```

### 7.3 Starta frontend

**I frontend-terminalen:**

```bash
cd frontend
npm run dev
```

**Du ska se:**
```
- ready started server on 0.0.0.0:3000, url: http://localhost:3000
```

---

## 🎉 Steg 8: Testa applikationen

### 8.1 Öppna i webbläsaren

Gå till: **http://localhost:3000**

**Du ska nu se:**
- En snygg chat-interface med "OneSeek.ai" i headern
- Ett mörkt/ljust tema (klicka solen/måne-ikonen för att växla)
- En input-fält där du kan skriva frågor

### 8.2 Testa grundläggande chat

**Skriv i chatten:**
```
Hej! Kan du berätta lite om dig själv?
```

**Förväntat resultat:**
- Du ska se svaret dyka upp **token för token** i realtid (streaming)
- En liten cursor (▊) visas under genereringen
- Svaret ska komma från vLLM (lokal AI)

### 8.3 Testa RAG-funktionen (om du setup Vespa)

**Skriv:**
```
Vad är AI-risker enligt experter?
```

eller

```
Berätta om Sverige
```

**Förväntat resultat:**
- Efter några sekunder ska svaret börja streama
- Under svaret finns en **accordion "Källor & Steg"**
- Klicka på den för att se:
  - **Processteg:** "Retrieving...", "Retrieved 6 documents", etc.
  - **Hämtade källor:** Dokument från Vespa med relevans-score

---

## 🔍 Felsökning

### Problem: "Connection refused" till vLLM

**Lösning:**
1. Kontrollera att vLLM körs: `curl http://localhost:8000/health`
2. Kolla `backend/.env` – `VLLM_URL` ska vara `http://localhost:8000/v1`
3. Starta om vLLM (Steg 5.3)

### Problem: "ModuleNotFoundError"

**Lösning:**
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### Problem: Frontend visar felmeddelande

**Lösning:**
1. Kontrollera att backend körs: `curl http://localhost:8001/health`
2. Kolla `frontend/.env.local` – ska innehålla `NEXT_PUBLIC_API_BASE_URL=http://localhost:8001`
3. Starta om frontend: `npm run dev`

### Problem: Inga källor visas (tom accordion)

**Lösning:**
- Du har troligen inte setup Vespa (Steg 6)
- Detta är OK! Applikationen fungerar utan RAG, men utan källor
- För att få källor: Gör Steg 6 komplett

### Problem: "Port already in use"

**Lösning:**

**För port 8000 (vLLM):**
```bash
# Linux/macOS
lsof -i :8000
kill -9 <PID>

# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

**För port 8001 (backend):**
```bash
# Linux/macOS
lsof -i :8001
kill -9 <PID>

# Windows
netstat -ano | findstr :8001
taskkill /PID <PID> /F
```

### Problem: vLLM kraschar med "CUDA out of memory"

**Lösning:**
- Använd en mindre modell (Llama-3.1-8B istället för Qwen-14B)
- Minska `--gpu-memory-utilization` till 0.80
- Minska `--max-model-len` till 4096 eller lägre

---

## 📊 Sammanfattning av terminaler

När allt är uppsatt ska du ha **3 terminaler** öppna:

| Terminal | Kör | Port |
|----------|-----|------|
| **1: vLLM** | `vllm serve Qwen/Qwen2.5-14B-Instruct-AWQ --port 8000` | 8000 |
| **2: Backend** | `uvicorn app:app --reload --port 8001` | 8001 |
| **3: Frontend** | `npm run dev` | 3000 |

**Öppna i webbläsare:** http://localhost:3000

---

## 🎯 Nästa steg

Grattis! Du har nu:
- ✅ En fungerande lokal AI-chat
- ✅ Streaming i realtid
- ✅ RAG med Vespa Cloud (om du gjorde Steg 6)
- ✅ Transparent UI som visar källor och steg

### Vad kan du göra nu?

1. **Testa olika modeller:**
   - Byt modell i vLLM-kommandot
   - Uppdatera `VLLM_MODEL` i `backend/.env`

2. **Lägg till mer data i Vespa:**
   - Redigera `backend/deploy_vespa.py`
   - Lägg till egna dokument i `get_sample_documents()`
   - Kör `python deploy_vespa.py` igen

3. **Anpassa frontend:**
   - Redigera `frontend/src/components/ChatInterface.tsx`
   - Ändra färger i `frontend/src/app/globals.css`

4. **Läs mer dokumentation:**
   - `ARCHITECTURE.md` – hur systemet fungerar
   - `SECURITY.md` – säkerhetsdetaljer
   - `TROUBLESHOOTING.md` – mer felsökning

---

## 💬 Få hjälp

**Problem med setup?**
- Öppna ett issue på GitHub: https://github.com/robinandreeklund-collab/oneseek/issues
- Läs `TROUBLESHOOTING.md`
- Kolla GitHub Discussions

**Hittat en bugg?**
- Se `CONTRIBUTING.md` för hur du rapporterar buggar

---

## 📝 Checklista – Har du gjort allt?

Gå igenom denna checklista för att se att allt är klart:

- [ ] Python 3.11+ installerat
- [ ] Node.js 18+ installerat
- [ ] Git installerat
- [ ] Repo klonat
- [ ] Backend venv skapat och paket installerade
- [ ] Backend `.env` konfigurerad
- [ ] Frontend npm-paket installerade
- [ ] Frontend `.env.local` konfigurerad
- [ ] vLLM installerat och startat
- [ ] Vespa Cloud-konto skapat (valfritt)
- [ ] Vespa certifikat nedladdade (valfritt)
- [ ] Vespa app deployad (valfritt)
- [ ] Backend startat (port 8001)
- [ ] Frontend startat (port 3000)
- [ ] Testat chat på http://localhost:3000

**Om alla är checkade: Du är klar! 🎊**

---

Lycka till med OneSeek.ai! 🚀
