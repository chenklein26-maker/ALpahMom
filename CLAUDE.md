# CLAUDE.md — AlphaMom Developer Guidelines

Guidelines and commands for developer agents working on the **AlphaMom (宝妈反买量化指数)** project.

---

## 🚀 Frequently Used Commands

### 1. Run Data Pipeline (End-to-End)
Execute these commands in sequence to fetch data, compute the index, and generate reports:
```bash
# Fetch Crypto Sentiment & Market Data
python scripts/fetch_crypto.py --config assets/config_template.json --output data/crypto_raw.json

# Fetch A-Stock Sentiment & Market Data
python scripts/fetch_astock.py --config assets/config_template.json --output data/astock_raw.json

# Compute Mommy Crowding Index (MCI)
python scripts/compute_mci.py --crypto data/crypto_raw.json --astock data/astock_raw.json --output data/mci_result.json

# Generate Satirical Report (review mode)
python scripts/report.py --mci data/mci_result.json --config assets/config_template.json --mode review
```

### 2. Preview Dashboard Web UI
Run a local development web server to host the macOS light/dark-mode dashboard:
```bash
python -m http.server 8000
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser to verify the interactive weight controls and canvas poster generation.

---

## 🎙️ Tone, Style & Persona Guidelines

All user-facing messages, console outputs, and dashboard texts must adhere to the **Cyber Sentiment Radio** persona:
1. **Sarcastic Broadcasting Voice**: Use a dystopian, highly satirical, fast-paced American-radio-show style localized to financial markets.
2. **Playful Retail Address**: Address the retail audience using sarcastic trading terms:
   - `天台VIP们` (Rooftop VIPs - for extreme freeze/fear)
   - `接盘侠们` (Bagholders / Exit Liquidity)
   - `天才交易员们` (Genius Traders / Day Traders)
   - `金融巨鳄们` (Financial Tycoons - for retail FOMO)
   - `韭菜们` (Leeks)
3. **No Game-Specific Lore**: **Never** mention game-specific terms from *Cyberpunk 2077* (such as *Night City*, *Arasaka*, *NCPD*, *Eurodollars/Eddies*, *Blackwall*, *Kabuki*, or characters like *Stanley*). Keep the context 100% focused on real-world assets (Gold, A-shares, Crypto, Moutai, 招商中证白酒) and real-life retail traders/aunts.
4. **LLM Prompts Reference**: Future agents can inspect [assets/mama_quotes.json](file:///c:/Users/v_clulcchen/Desktop/RYu/Coding/宝妈反买/assets/mama_quotes.json) to study the offline fallback templates for tone, sarcasm depth, and copywriting styles when formulating LLM prompts.

---

## 🛠️ Tech Stack & Implementation Rules

1. **LLM Generation with Fallback**:
   - The system uses **DeepSeek API (`deepseek-chat`)** via Open-AI compatible payload formats.
   - Env key: `DEEPSEEK_API_KEY`. Config path: `llm_config.deepseek_api_key`.
   - **Fail-safe fallback**: If the key is missing or API request fails, the report engine must automatically fall back to static templated generation loaded from `assets/mama_quotes.json`.
2. **Dual-Mode Web Dashboard**:
   - Fully client-side responsive macOS layout with segment toggling between **Lite Mode** (action-centric cards, large signal bulbs, poster download) and **Pro Mode** (weights adjust sliders, Z-Score volatility badges, and milestone markers on Chart.js).
   - Dynamic weight calculations must happen 100% locally in `index.html` to avoid API request latencies.
