# 🖼️ AiZr Image Classifier TUI 🚀

Inteligentní CLI/TUI nástroj pro automatickou klasifikaci obrázků s podporou více AI providerů, interaktivním režimem a perzistentním ukládáním nastavení.

## ✨ Hlavní Funkce

*   **Pokročilá Klasifikace Obrázků:** Využívá AI modely pro detailní analýzu a zařazení obrázků do definovaných kategorií.
*   **Extrakce Informací:** Kromě kategorií dokáže z obrázků extrahovat textový popis, relevantní tagy a rozpoznaný text.
*   **Textové Uživatelské Rozhraní (TUI):** Pohodlné ovládání a konfigurace pomocí moderního TUI postaveného na knihovně [Textual](https://textual.textualize.io/).
*   **Podpora Více AI Providerů:**
    *   ⚙️ **OpenRouter:** Přístup k široké škále modelů, včetně Google Gemini.
    *   🦙 **Ollama (Lokální):** Možnost využití lokálně běžících modelů (např. LLaVA).
    *    архитектура připravena pro snadné přidání dalších (OpenAI, Anthropic, Groq atd.).
*   **Dva Režimy Zpracování:**
    *   💨 **Dávkový režim:** Zpracuje všechny obrázky v zadané složce automaticky.
    *   👆 **Interaktivní režim:** Umožňuje procházet obrázky jeden po druhém, zobrazit výsledky klasifikace a schválit/přeskočit/upravit je.
*   **Perzistentní Nastavení:** Všechna vaše nakonfigurovaná nastavení (cesty, vybraný provider/model atd.) se ukládají do souboru a načtou při příštím spuštění.
*   **Dynamické Načítání Modelů:** Seznam dostupných modelů se načítá dynamicky pro nakonfigurovaného AI providera (aktuálně plně pro Ollama).
*   **Organizace Souborů:** Automaticky kopíruje zpracované obrázky do složek podle jejich kategorií.
*   **Správa Tagů:** Udržuje a rozšiřuje globální seznam tagů v `tagy.json`.
*   **Cachování Obrázků:** Zmenšené verze obrázků se ukládají do cache pro rychlejší opakované zpracování.

## 📸 Screenshoty (TODO)

*(Zde by bylo ideální místo pro screenshoty hlavního menu, obrazovky nastavení, interaktivního režimu a obrazovky zpracování.)*

## ⚙️ Instalace

1.  **Naklonujte Repozitář:**
    ```bash
    git clone https://github.com/mastnacek/AiZr.git
    cd AiZr
    ```

2.  **(Doporučeno) Vytvořte a Aktivujte Virtuální Prostředí:**
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # Linux / macOS
    source .venv/bin/activate
    ```

3.  **Nainstalujte Závislosti:**
    Vytvořte soubor `requirements.txt` (viz níže) a spusťte:
    ```bash
    pip install -r requirements.txt
    ```
    *(Obsah `requirements.txt` bude doplněn v dalším kroku tohoto subtasku).*

4.  **Nastavte Proměnné Prostředí:**
    Pro správnou funkci AI providerů je potřeba nastavit API klíče jako proměnné prostředí:
    *   `OPENROUTER_API_KEY`: Váš API klíč pro OpenRouter.ai.
    *   `OLLAMA_BASE_URL` (Volitelné): Pokud vaše Ollama běží na jiné adrese než `http://localhost:11434`, nastavte tuto proměnnou.
    *   Další klíče (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_GEMINI_API_KEY`, `GROQ_API_KEY`) budou potřeba, až budou implementováni příslušní provideři.

    *Příklad nastavení proměnné prostředí (Linux/macOS v `.bashrc` nebo `.zshrc`):*
    ```bash
    export OPENROUTER_API_KEY="vas_klic_zde"
    export OLLAMA_BASE_URL="http://vase_ollama_ip:11434"
    ```
    *Nezapomeňte znovu načíst konfiguraci shellu (např. `source ~/.bashrc`) nebo otevřít nový terminál.*

## 🛠️ Konfigurace

*   **Hlavní konfigurace** se provádí přes Textové Uživatelské Rozhraní (TUI) v sekci "Nastavení".
*   **Soubor s nastavením:** Vaše preference (cesty, vybraný AI provider, model atd.) se automaticky ukládají do souboru `image_classifier_settings.json` ve vašem domovském adresáři (specifikovaném proměnnou `HOME_DIR` v `config.py`, standardně `/data/data/com.termux/files/home` pro Termux, což byste si měli upravit pro jiné systémy).
*   **Výchozí cesty:** V `config.py` jsou definovány výchozí cesty pro vstupní složku, výstupní složky kategorií, cache atd. Tyto hodnoty se použijí, pokud nejsou přepsány v TUI nebo v souboru s nastavením. **Pro jiné systémy než Termux si tyto cesty v `config.py` upravte podle potřeby!**

## 🚀 Použití

1.  Ujistěte se, že máte aktivované virtuální prostředí a nastavené proměnné prostředí.
2.  Spusťte aplikaci:
    ```bash
    python main.py
    ```
3.  Otevře se Textové Uživatelské Rozhraní (TUI):
    *   **Hlavní menu:**
        *   `Dávkové zpracování`: Spustí automatickou klasifikaci všech obrázků ve vstupní složce podle aktuálního nastavení. Průběh se loguje na obrazovce "Zpracování obrázků...".
        *   `Interaktivní zpracování`: Spustí režim, kde se obrázky zpracovávají jeden po druhém. U každého uvidíte výsledky klasifikace a můžete je schválit, přeskočit nebo ukončit režim.
        *   `Nastavení`: Otevře obrazovku s konfigurací (viz níže).
        *   `Konec`: Ukončí aplikaci.
    *   **Obrazovka Nastavení:**
        *   `AI Provider`: Vyberte preferovaného AI providera (OpenRouter, Ollama).
        *   `Model`: Dynamicky se načte seznam modelů pro vybraného providera. Vyberte model, který chcete použít.
        *   `Max. velikost (px)`: Maximální rozměr (šířka nebo výška), na který se budou obrázky zmenšovat před odesláním k analýze (zachovává poměr stran).
        *   `Rekurzivní hledání`: Zda se mají prohledávat i podsložky ve zdrojové složce.
        *   `Cesty`: Nastavení cest pro zdrojovou složku obrázků, výstupní složku pro kategorie a složku pro cache.
        *   Uložte nastavení tlačítkem "Uložit nastavení".

## 🤖 Podporovaní AI Provideři

*   ✅ **OpenRouter:**
    *   Konfigurace: Vyžaduje `OPENROUTER_API_KEY`.
    *   Modely: Aktuálně používá model definovaný v `config.py` (výchozí `google/gemini-2.5-flash-preview`), ale měl by být volitelný přes TUI.
*   ✅ **Ollama (Lokální):**
    *   Konfigurace: Vyžaduje běžící instanci Ollama. URL se bere z `OLLAMA_BASE_URL` (výchozí `http://localhost:11434`).
    *   Modely: Dynamicky načítá seznam vašich lokálně stažených modelů (např. `llava:latest`). Ujistěte se, že vybraný model je multimodální a umí zpracovávat obrázky.
*   🔜 OpenAI, Google Gemini (Direct), Anthropic, Groq - budou implementováni.

## 📂 Struktura Projektu (Zjednodušená)

```
.
├── main.py                     # Hlavní spouštěcí skript (spouští TUI)
├── tui_app.py                  # Logika Textual TUI aplikace
├── config.py                   # Konfigurace (cesty, API klíče, konstanty)
├── prompts.py                  # Definice AI promptů
├── image_utils.py              # Utility pro práci s obrázky
├── file_handler.py             # Utility pro práci se soubory (ukládání JSON, správa složek)
├── providers/                  # Moduly pro jednotlivé AI providery
│   ├── base_provider.py        # Abstraktní třída pro providery
│   ├── openrouter_provider.py  # Implementace pro OpenRouter
│   └── ollama_provider.py      # Implementace pro Ollama
│   └── ...                     # Další provideři
├── screens/                    # Obrazovky pro TUI
│   ├── settings_screen.py      # Obrazovka nastavení
│   └── interactive_screen.py   # Obrazovka pro interaktivní režim
├── README.md                   # Tento soubor
└── requirements.txt            # Závislosti projektu
```

---
Vyvinuto s ❤️ a AI.
```
