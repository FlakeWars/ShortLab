# Plan przygotowania środowiska (macOS M2 Pro)

Dokument opisuje plan przygotowania lokalnego środowiska uruchomieniowego zgodnego z PRD i proponowanym stosem technologicznym. Priorytetem jest deterministyczność renderu, stabilność zależności na macOS ARM64 oraz prosty, powtarzalny setup.

## 1. Założenia i cele
- **Lokalny pipeline MVP**: generacja -> render -> review -> publikacja -> metryki (PRD).
- **Deterministyczność**: stabilne wersje narzędzi i bibliotek dla renderu 2D i FFmpeg.
- **macOS ARM64 (M2 Pro)**: render i FFmpeg uruchamiane natywnie, infrastruktura pomocnicza w Docker Compose.
- **Powtarzalność**: pinowanie zależności + bootstrap skrypt.

## 2. Zakres konteneryzacji
- **Docker Compose**: Postgres, Redis, MinIO (zgodnie z tech-stack).
- **Natywnie na macOS**: renderer (Skia-Python/Cairo), FFmpeg, Python, Node.js.

## 3. Wymagane narzędzia systemowe
1. **Xcode Command Line Tools**
   - Niezbędne do kompilacji natywnych zależności.
2. **Homebrew**
   - Standardowe źródło zależności systemowych na macOS.

## 4. Pinowanie wersji (stabilność i deterministyczność)
- **Python**: wersja 3.12.
- **Node.js**: wersja LTS.
- **FFmpeg**: jawnie przypięta wersja z Homebrew.
- **Skia/Cairo**: jawnie przypięte wersje (brew lub wheel w zależności od kompatybilności).
- **Python deps**: `pyproject.toml` + lock (uv/poetry), opcjonalnie `constraints.txt`.

## 5. Plan instalacji (kroki)

### 5.1. System i narzędzia bazowe
1. Zainstaluj Xcode Command Line Tools.
2. Zainstaluj Homebrew.
3. Zainstaluj narzędzia bazowe przez `Brewfile` (patrz sekcja 6).

### 5.2. Python i środowisko backendu
1. Zainstaluj Python 3.12 przez Homebrew.
2. Zainstaluj `uv` lub `poetry`.
3. Utwórz i aktywuj wirtualne środowisko.
4. Zainstaluj zależności backendu z lockfile.

### 5.3. Node.js i panel review
1. Zainstaluj Node.js LTS.
2. Zainstaluj zależności frontendu (React + Vite).

### 5.4. Renderer 2D i FFmpeg
1. Zainstaluj FFmpeg z Homebrew (przypięta wersja).
2. Zainstaluj Skia-Python lub Cairo (zależnie od decyzji MVP).
3. Zweryfikuj render testowy (deterministyczny output).

### 5.5. Infrastruktura lokalna (Docker Compose)
1. Zainstaluj Docker Desktop (ARM64).
2. Uruchom `docker compose up` dla Postgresa/Redisa/MinIO.
3. Zweryfikuj połączenia z backendu.

## 6. Brewfile (propozycja)
W repozytorium warto utrzymywać `Brewfile` z przypiętymi wersjami i podstawowymi narzędziami:
- python@3.12
- node
- ffmpeg
- cairo (jeśli używany)
- pkg-config
- git

## 7. Skrypt bootstrapowy
Zalecany plik `scripts/setup-macos.sh`, który:
- instaluje Homebrew (jeśli brak),
- uruchamia `brew bundle`,
- weryfikuje wersje kluczowych binarek,
- tworzy lokalne `.env` i wskazuje brakujące sekrety.

## 8. Weryfikacja po instalacji (checklista)
- `python --version` zwraca 3.12.x.
- `ffmpeg -version` zwraca przypiętą wersję.
- Backend uruchamia się lokalnie.
- Panel review odpala się przez Vite.
- Compose uruchamia Postgresa/Redisa/MinIO.
- Render testowy generuje identyczny wynik dla tego samego seeda.

## 9. Utrzymanie stabilności
- Zmiany wersji tylko przez aktualizację `Brewfile` i lockfile.
- Wszelkie zmiany renderera i FFmpeg muszą skutkować aktualizacją golden tests.
- Wersje DS/DSL zapisujemy w metadanych renderu (wymóg PRD).

## 10. Uwagi końcowe
To podejście minimalizuje ryzyko różnic między macOS i Linuksem, zapewnia stabilność na M2 Pro i jest spójne z MVP: lokalny pipeline, deterministyczny render, panel review i półautomatyczna publikacja.
