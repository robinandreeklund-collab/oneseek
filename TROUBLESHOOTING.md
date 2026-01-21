# Troubleshooting Guide

Common issues and solutions for OneSeek.ai MVP.

## Backend Issues

### 1. Import Errors

**Problem:** `ModuleNotFoundError: No module named 'fastapi'` or similar

**Solution:**
```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. vLLM Connection Error

**Problem:** `Error during generation: Connection refused` or `Failed to connect to vLLM`

**Solution:**
- Ensure vLLM is running:
  ```bash
  vllm serve Qwen/Qwen2.5-14B-Instruct-AWQ --port 8000
  ```
- Check if port 8000 is in use:
  ```bash
  lsof -i :8000  # or: netstat -ano | findstr :8000 on Windows
  ```
- Verify `VLLM_URL` in `.env`:
  ```
  VLLM_URL=http://localhost:8000/v1
  ```

### 3. Vespa Authentication Error

**Problem:** `401 Unauthorized` or `403 Forbidden` when accessing Vespa

**Solution:**
- Verify certificate and key paths in `.env`:
  ```bash
  ls -l /path/to/certificate.pem
  ls -l /path/to/private-key.pem
  ```
- Ensure files are readable:
  ```bash
  chmod 600 /path/to/certificate.pem
  chmod 600 /path/to/private-key.pem
  ```
- Download fresh certificates from Vespa Console → Security
- Check `VESPA_URL` format:
  ```
  VESPA_URL=https://your-app.your-tenant.vespa-cloud.net
  ```

### 4. No Retrieved Documents

**Problem:** Queries return 0 documents from Vespa

**Solution:**
- Verify documents were fed:
  ```bash
  python deploy_vespa.py
  ```
- Check if data exists:
  ```bash
  # Use Vespa CLI or Console to verify document count
  ```
- Try queries matching the fed data:
  - Example: "AI-risker" (Swedish for "AI risks")
  - The sample data is in Swedish

### 5. Port Already in Use

**Problem:** `Address already in use` when starting FastAPI

**Solution:**
```bash
# Find process using port 8001
lsof -i :8001  # or: netstat -ano | findstr :8001 on Windows

# Kill the process
kill -9 <PID>  # or use Task Manager on Windows

# Or use a different port
uvicorn app:app --port 8002
```

### 6. Environment Variables Not Loading

**Problem:** Backend uses default values instead of `.env` values

**Solution:**
- Ensure `.env` file exists in `backend/` directory:
  ```bash
  ls -la backend/.env
  ```
- Check file format (no spaces around `=`):
  ```
  VLLM_URL=http://localhost:8000/v1  # ✓ Correct
  VLLM_URL = http://localhost:8000/v1  # ✗ Wrong
  ```
- Restart the backend after editing `.env`

## Frontend Issues

### 1. Module Not Found

**Problem:** `Cannot find module '@/components/ChatInterface'`

**Solution:**
```bash
cd frontend
npm install
# or
yarn install
```

### 2. API Connection Error

**Problem:** `Failed to fetch` or CORS errors in browser console

**Solution:**
- Verify backend is running:
  ```bash
  curl http://localhost:8001/health
  ```
- Check `.env.local`:
  ```
  NEXT_PUBLIC_API_BASE_URL=http://localhost:8001
  ```
- Restart Next.js after changing `.env.local`:
  ```bash
  npm run dev
  ```

### 3. Build Errors

**Problem:** `Type error: Cannot find module` during build

**Solution:**
```bash
# Clean and reinstall
rm -rf node_modules .next
npm install
npm run build
```

### 4. Styling Issues

**Problem:** Dark mode not working or styles not applying

**Solution:**
- Check if Tailwind CSS is configured:
  ```bash
  ls tailwind.config.ts postcss.config.js
  ```
- Clear Next.js cache:
  ```bash
  rm -rf .next
  npm run dev
  ```
- Check browser console for CSS errors

### 5. Port 3000 Already in Use

**Problem:** `Port 3000 is already in use`

**Solution:**
```bash
# Kill process on port 3000
lsof -i :3000
kill -9 <PID>

# Or use different port
npm run dev -- -p 3001
```

### 6. localStorage Not Persisting

**Problem:** Chat history is lost on refresh

**Solution:**
- Check browser console for errors
- Verify localStorage is enabled (not in private mode)
- Check browser storage quota:
  - Open DevTools → Application → Storage
- Clear and retry:
  ```javascript
  // In browser console
  localStorage.clear()
  ```

## Integration Issues

### 1. Backend Returns Empty Response

**Problem:** Frontend shows empty messages or errors

**Solution:**
- Check backend logs for errors
- Test API directly:
  ```bash
  curl -X POST http://localhost:8001/chat \
    -H "Content-Type: application/json" \
    -d '{"messages": [{"role": "user", "content": "Hello"}]}'
  ```
- Verify response format matches expected schema

### 2. Slow Response Times

**Problem:** Queries take very long (>30 seconds)

**Solution:**
- Check vLLM GPU utilization:
  ```bash
  nvidia-smi
  ```
- Reduce `max_tokens` in backend `.env`:
  ```
  MAX_TOKENS=1024
  ```
- Check Vespa query performance in logs
- Consider using smaller/faster model:
  ```bash
  vllm serve meta-llama/Llama-3.1-8B-Instruct --port 8000
  ```

### 3. Memory Issues

**Problem:** Out of memory errors, GPU OOM

**Solution:**
- Reduce model size or use quantized model (AWQ, GPTQ)
- Adjust GPU memory utilization:
  ```bash
  vllm serve ... --gpu-memory-utilization 0.85
  ```
- Reduce max model length:
  ```bash
  vllm serve ... --max-model-len 4096
  ```
- Close other GPU applications

## Docker Issues

### 1. Docker Compose Fails

**Problem:** `docker-compose up` fails

**Solution:**
- Ensure Docker is running
- Check `.env` file exists in backend:
  ```bash
  ls backend/.env
  ```
- Verify certificate paths are absolute:
  ```
  VESPA_CERT_PATH=/absolute/path/to/cert.pem
  ```
- Check logs:
  ```bash
  docker-compose logs backend
  ```

### 2. Cannot Access vLLM from Docker

**Problem:** Backend in Docker cannot reach vLLM on host

**Solution:**
- Use `host.docker.internal` instead of `localhost`:
  ```
  VLLM_URL=http://host.docker.internal:8000/v1
  ```
- On Linux, add to docker-compose.yml:
  ```yaml
  extra_hosts:
    - "host.docker.internal:host-gateway"
  ```

## Vespa Issues

### 1. Deployment Fails

**Problem:** `deploy_vespa.py` fails with authentication error

**Solution:**
- Verify Vespa Cloud credentials:
  ```bash
  cat $VESPA_CERT_PATH
  cat $VESPA_KEY_PATH
  ```
- Ensure tenant and application names are correct
- Check Vespa Console for deployment status

### 2. Query Returns Errors

**Problem:** Vespa queries fail with 400 Bad Request

**Solution:**
- Check YQL syntax in `agent.py`
- Verify schema matches query fields
- Test query in Vespa Console
- Check if embedding dimension matches (384)

### 3. Slow Indexing

**Problem:** `deploy_vespa.py` takes very long to feed documents

**Solution:**
- Reduce number of sample documents
- Check network connection to Vespa Cloud
- Verify GPU/CPU is not throttled during embedding generation

## General Tips

### Enable Debug Logging

**Backend:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Frontend:**
```typescript
console.log("Debug info:", variable);
```

### Check Service Status

```bash
# Backend
curl http://localhost:8001/health

# Frontend
curl http://localhost:3000

# vLLM
curl http://localhost:8000/v1/models
```

### Reset Everything

```bash
# Backend
cd backend
rm -rf venv __pycache__
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
rm -rf node_modules .next
npm install

# Start fresh
./setup.sh
```

## Getting Help

If you still have issues:

1. Check existing GitHub Issues
2. Create a new issue with:
   - Exact error message
   - Steps to reproduce
   - Environment details (OS, Python/Node version, GPU)
   - Relevant logs
3. Search documentation and README
4. Review ARCHITECTURE.md for system design

## Common Error Messages

| Error | Likely Cause | Solution |
|-------|--------------|----------|
| `Connection refused` | Service not running | Start the service |
| `ModuleNotFoundError` | Missing dependency | `pip install -r requirements.txt` |
| `401 Unauthorized` | Invalid credentials | Check Vespa certs |
| `Port already in use` | Port conflict | Kill process or use different port |
| `Out of memory` | GPU/RAM full | Reduce model size or batch size |
| `CORS error` | Backend not configured | Check CORS middleware in `app.py` |
| `Cannot find module` | Missing npm package | `npm install` |
| `Type error` | TypeScript issue | Check imports and types |

## Performance Tuning

### For RTX 5090 (24GB VRAM)
```bash
vllm serve Qwen/Qwen2.5-14B-Instruct-AWQ \
  --dtype auto \
  --quantization awq \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.92 \
  --tensor-parallel-size 1
```

### For Lower Memory GPUs (<16GB VRAM)
```bash
vllm serve meta-llama/Llama-3.1-8B-Instruct \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.85
```

### For CPU-only Testing (slow)
```bash
# Not recommended for production
vllm serve ... --device cpu
```
