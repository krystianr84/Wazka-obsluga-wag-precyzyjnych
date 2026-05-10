# Ważka — dokument kontynuacji projektu

> Plik opisuje kompletny aktualny stan projektu, podjęte decyzje projektowe oraz wskazówki
> niezbędne do dalszego rozwijania aplikacji. Wersja: **0.204.0** (2026-05-10).

---

## Spis treści

1. [Cel i zakres projektu](#1-cel-i-zakres-projektu)
2. [Środowisko i zależności](#2-środowisko-i-zależności)
3. [Struktura plików](#3-struktura-plików)
4. [Architektura — warstwy i zależności](#4-architektura--warstwy-i-zależności)
5. [Warstwa modeli](#5-warstwa-modeli)
6. [Warstwa protokołów](#6-warstwa-protokołów)
7. [Warstwa serwisów — ScaleService](#7-warstwa-serwisów--scaleservice)
8. [Warstwa UI](#8-warstwa-ui)
9. [Przepływ sygnałów Qt](#9-przepływ-sygnałów-qt)
10. [Ważne decyzje projektowe i naprawione błędy](#10-ważne-decyzje-projektowe-i-naprawione-błędy)
11. [Testy jednostkowe](#11-testy-jednostkowe)
12. [Budowanie pliku wykonywalnego](#12-budowanie-pliku-wykonywalnego)
13. [Możliwe kierunki rozbudowy](#13-możliwe-kierunki-rozbudowy)
14. [Konwencje kodowania](#14-konwencje-kodowania)
15. [Changelog](#15-changelog)

---

## 1. Cel i zakres projektu

Ważka to wieloplatformowa aplikacja desktopowa napisana w **Python 3 / PyQt6**, służąca do komunikacji z wagami przemysłowymi i laboratoryjnymi przez port szeregowy RS-232. Działa na systemach Windows 10/11, Linux oraz macOS 10.15+. Aplikacja:

- wyświetla bieżącą wartość ważenia (wartość, jednostka, status, timestamp),
- wysyła komendy do wagi (odczyt jednorazowy, odczyt natychmiastowy, tara, zerowanie),
- obsługuje tryb odczytu ciągłego (co 1 sekundę),
- umożliwia ręczne wydawanie komend przez wbudowany terminal,
- obsługuje cztery protokoły komunikacyjne czterech różnych producentów,
- pozwala na pełną konfigurację portu RS-232 (port, baud rate, bity danych, parzystość, bity stopu).

**Projekt jest pracą zaliczeniową** z przedmiotu Programowanie obiektowe I, Semestr IV.  
Autor: **Krystian Rutkowski**.

---

## 2. Środowisko i zależności

| Element | Wartość |
|---|---|
| Język | Python 3.10+ (testowane na 3.13, 3.14) |
| Framework GUI | PyQt6 ≥ 6.6.0 |
| Moduł RS-232 | PyQt6.QtSerialPort (część PyQt6) |
| Styl Qt | Fusion |
| System docelowy | Windows 10/11 · Linux (Ubuntu 22.04+, Fedora 38+, inne) · macOS 10.15+ (Intel i Apple Silicon) |
| IDE | PyCharm (konfiguracja w `.idea/`) |
| Środowisko wirtualne | `.venv/` (Python 3.14) |

**`requirements.txt`:**
```
PyQt6>=6.6.0
PyQt6-Qt6>=6.6.0
pytest>=7.0.0
```

**Instalacja:**
```bash
pip install PyQt6
```

**Uruchomienie:**
```bash
python main.py
```

---

## 3. Struktura plików

```
metler/
│
├── main.py                          # punkt wejścia — tworzy QApplication i MainWindow
│
├── models/
│   ├── __init__.py
│   ├── weight_reading.py            # WeightStatus (Enum), WeightReading (dataclass)
│   └── scale_preset.py              # ScalePreset (dataclass) — profil wagi
│
├── protocols/
│   ├── __init__.py
│   ├── scale_protocol.py            # ABC — interfejs dla wszystkich protokołów
│   ├── mettler_sics_protocol.py     # Mettler Toledo MT-SICS Level 0/1
│   ├── sartorius_sbi_protocol.py    # Sartorius SBI
│   ├── radwag_protocol.py           # Radwag R Protocol (WLY, WPS, AS, PS)
│   └── radwag_cbcp03_protocol.py    # Radwag CBCP-03 (WLY, C315, PUE 7.1)
│
├── services/
│   ├── __init__.py
│   ├── scale_service.py             # ScaleService — QSerialPort, sygnały, parsowanie
│   ├── preset_service.py            # PresetService — zapis/odczyt profili (JSON)
│   └── app_settings_service.py      # AppSettingsService — zapis/odczyt ustawień aplikacji (JSON)
│
├── ui/
│   ├── __init__.py
│   ├── theme.py                     # ThemeColors, ThemeManager, motywy DARK i LIGHT
│   ├── main_window.py               # QMainWindow — główne okno aplikacji
│   ├── weight_display.py            # WeightDisplay — wyświetlacz wagi + statystyki sesji
│   ├── connection_panel.py          # ConnectionPanel — konfiguracja połączenia + profile
│   ├── settings_dialog.py           # SettingsDialog — niemodalne okno ustawień
│   ├── app_settings_dialog.py       # AppSettingsDialog — wybór motywu wyglądu
│   ├── terminal_dialog.py           # TerminalDialog — terminal komend RS-232
│   └── about_dialog.py              # AboutDialog — okno "O programie" z logo
│
├── img/
│   └── festisite_nasa-2.PNG         # logo aplikacji (wyświetlane w AboutDialog)
│
├── docs/                            # materiały pomocnicze (instrukcje, specyfikacje PDF)
│
├── tests/
│   ├── test_models.py               # WeightStatus, WeightReading, ScalePreset
│   ├── test_protocol_mettler.py     # parser MT-SICS
│   ├── test_protocol_sartorius.py   # parser SBI
│   ├── test_protocol_radwag.py      # parser R Protocol
│   ├── test_protocol_cbcp03.py      # parser CBCP-03
│   ├── test_fallback_parse.py       # parser awaryjny _fallback_parse
│   └── test_preset_service.py       # PresetService — zapis/odczyt profili
│
├── presets.json                     # zapisane profile wag (tworzony automatycznie)
├── app_settings.json                # ustawienia aplikacji: motyw (tworzony automatycznie)
├── pytest.ini                       # konfiguracja pytest (testpaths, pythonpath)
├── LICENSE                          # licencja MIT
├── requirements.txt
├── requirements.md                  # ← ten plik
├── README.md                        # skrócona instrukcja użytkownika
├── DOKUMENTACJA.md                  # dokumentacja techniczna + changelog
├── CBCP-03-ITKP-07-01-12-18-EN.pdf # dokumentacja protokołu Radwag CBCP-03
└── .gitignore                       # ignoruje: __pycache__, *.pyc, .venv/, *.log, docs/*
```

---

## 4. Architektura — warstwy i zależności

```
main.py
  ├─► AppSettingsService             — wczytuje app_settings.json (motyw)
  ├─► ThemeManager (singleton)       — inicjowany przed otwarciem okna
  └─► MainWindow (QMainWindow)
        ├─► ScaleService (QObject)
        │     ├─► QSerialPort         — fizyczna komunikacja RS-232
        │     ├─► QTimer              — odczyt ciągły (konfigurowalny interwał)
        │     └─► ScaleProtocol (ABC) — aktywny protokół parsowania
        │
        ├─► PresetService             — zapis/odczyt profili wag (presets.json)
        ├─► WeightDisplay             — wyświetlacz odczytu + statystyki sesji
        ├─► SettingsDialog            — niemodalne okno ustawień
        │     └─► ConnectionPanel     — formularz konfiguracji portu + profile
        ├─► TerminalDialog            — niemodalne okno terminala
        ├─► AppSettingsDialog         — modalne okno wyboru motywu
        └─► AboutDialog               — modalne okno "O programie"
```

`ThemeManager` (singleton `QObject`) jest globalnie dostępny przez `ThemeManager.instance()`. Emituje sygnał `theme_changed` po każdej zmianie motywu; wszystkie komponenty UI łączą się z tym sygnałem i wywołują `_apply_theme()`.

**Zasada komunikacji między warstwami:** wyłącznie sygnały i sloty Qt — warstwy nie wywołują się bezpośrednio w górę hierarchii.

**Zależności między modułami (jednokierunkowe):**
```
UI → ScaleService → ScaleProtocol → WeightReading
```

---

## 5. Warstwa modeli

### `models/scale_preset.py`

#### `ScalePreset(dataclass)`
```python
name:          str   # nazwa profilu wyświetlana w UI
protocol_name: str   # wartość ScaleProtocol.name
port:          str   # np. "COM3"
baud_rate:     int
parity:        str   # klucz z PARITY_OPTIONS, np. "Brak (N)"
data_bits:     str   # klucz z DATA_BITS_OPTIONS, np. "8"
stop_bits:     str   # klucz z STOP_BITS_OPTIONS, np. "1"
```

Serializowany do/z JSON przez `dataclasses.asdict()` i `ScalePreset(**dict)`.

---

### `models/weight_reading.py`

#### `WeightStatus(Enum)`
```python
STABLE      # waga stabilna
DYNAMIC     # waga w ruchu
OVER_RANGE  # przekroczono górny zakres
UNDER_RANGE # przekroczono dolny zakres
IN_PROGRESS # komenda w toku
ERROR       # błąd
```

#### `WeightReading(dataclass)`
```python
value:     float         # wartość masy (ze znakiem)
unit:      str           # jednostka, np. "g", "kg", "N"
status:    WeightStatus
timestamp: datetime      # wypełniany automatycznie w __post_init__

# właściwości:
status_label   -> str    # polska etykieta statusu
formatted_value -> str   # f"{value:.3f} {unit}"
```

#### `STATUS_LABELS: dict[WeightStatus, str]`
Polskie etykiety: `"Stabilna"`, `"Dynamiczna"`, `"Przekroczony zakres"`, itd.

---

## 6. Warstwa protokołów

### `protocols/scale_protocol.py` — klasa abstrakcyjna

Każdy protokół musi implementować:

```python
@property name              -> str    # nazwa wyświetlana w UI
@property weight_command    -> bytes  # komenda odczytu stabilnego
@property weight_immediate_command -> bytes
@property tare_command      -> bytes
@property zero_command      -> bytes
@property default_baud_rate -> int
@property command_list      -> list[tuple[str, str]]  # [(komenda, opis), ...]

def parse_response(self, line: str) -> WeightReading | None
```

`command_list` ma domyślną implementację zwracającą `[]` — protokół może ją nadpisać.

---

### Zarejestrowane protokoły (`AVAILABLE_PROTOCOLS` w `scale_service.py`)

| # | Klasa | Nazwa wyświetlana | Baud | Komendy RS-232 |
|---|---|---|---|---|
| 0 | `MettlerSicsProtocol` | Mettler Toledo (MT-SICS) | 9600 | `S\r\n`, `SI\r\n`, `T\r\n`, `Z\r\n` |
| 1 | `SartoriusSbiProtocol` | Sartorius (SBI) | 1200 | `P\r\n`, `P\r\n`, `T\r\n`, `Z\r\n` |
| 2 | `RadwagProtocol` | Radwag (WLY / R protocol) | 9600 | `SU\r\n`, `SI\r\n`, `T\r\n`, `Z\r\n` |
| 3 | `RadwagCbcp03Protocol` | Radwag CBCP-03 | 9600 | `S\r\n`, `SUI\r\n`, `T\r\n`, `Z\r\n` |

Kolejność w liście = kolejność w dropdownie. Domyślnie aktywny: indeks 0 (Mettler).

---

### Szczegóły parsowania

**Wspólny parser awaryjny `_fallback_parse(line)`** w `scale_service.py`:  
Regex: `r"^([+-]?)\s*([\d]+[.,][\d]+)\s*([a-zA-Z/]+)$"`  
Obsługuje kompaktowy format bez prefiksu, np. `0,000g`, `50.000 g`, `-1,234kg`.  
Wywoływany gdy `parse_response` zwróci `None`. Zwraca status `STABLE`.

**Normalizacja zakończeń linii** w `_on_ready_read`:  
`\r\n` → `\n`, `\r` → `\n`. Obsługuje wszystkie warianty RS-232.  
Bajty null (`\x00`) są usuwane przed parsowaniem.

---

## 7. Warstwa serwisów — ScaleService

### Stałe modułu

```python
AVAILABLE_PROTOCOLS: list[ScaleProtocol]   # 4 protokoły

AVAILABLE_BAUD_RATES = [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200]

PARITY_OPTIONS: dict[str, QSerialPort.Parity] = {
    "Brak (N)": NoParity, "Parzysta (E)": EvenParity,
    "Nieparzysta (O)": OddParity, "Space (S)": SpaceParity, "Mark (M)": MarkParity
}

DATA_BITS_OPTIONS: dict[str, QSerialPort.DataBits] = {
    "5": Data5, "6": Data6, "7": Data7, "8": Data8
}

STOP_BITS_OPTIONS: dict[str, QSerialPort.StopBits] = {
    "1": OneStop, "1.5": OneAndHalfStop, "2": TwoStop
}

MAX_LOG_ENTRIES = 200
```

### Sygnały `ScaleService`

```python
reading_updated      = pyqtSignal(object)         # WeightReading — nowy odczyt z wagi
log_added            = pyqtSignal(str)             # nowy wpis w logu "[HH:MM:SS] treść"
connection_changed   = pyqtSignal(bool)            # True = połączono, False = rozłączono
error_occurred       = pyqtSignal(str)             # komunikat błędu portu
continuous_changed   = pyqtSignal(bool)            # True = tryb ciągły włączony
protocol_changed     = pyqtSignal(object)          # ScaleProtocol — przy set_protocol()
session_stats_updated = pyqtSignal(float, float, float, float, str)  # min, max, mean, stddev, jednostka
session_stats_reset  = pyqtSignal()                # statystyki zresetowane
```

Statystyki sesji (min, max, średnia — algorytm Welford'a, odchylenie standardowe populacji) liczone dla statusów `STABLE` i `DYNAMIC`. Resetują się przy tarze, zerowaniu i rozłączeniu.

### Właściwości publiczne

```python
connection_info -> str    # np. "COM3  @  9600 baud  |  8N1  [Radwag CBCP-03]"
protocol        -> ScaleProtocol
is_connected    -> bool
is_continuous   -> bool
```

### Metody publiczne

```python
connect(port_name, baud_rate,
        parity=NoParity, data_bits=Data8, stop_bits=OneStop)
disconnect()
set_protocol(protocol: ScaleProtocol)
request_weight()           # wysyła weight_command
request_weight_immediate() # wysyła weight_immediate_command
tare()
zero()
start_continuous()         # QTimer (interval_ms) → weight_immediate_command
stop_continuous()
set_continuous_interval(ms: int)  # zmienia interwał; restartuje timer jeśli aktywny
send_raw(text: str)        # terminal: wysyła text + "\r\n"

@staticmethod
available_ports() -> list[str]
```

### Zachowanie logu

- Format wpisu: `[HH:MM:SS] treść`
- Prefiksy: `>>` wysłane, `<<` odebrane, `??` nierozpoznane, `BŁĄD` błąd
- Bufor: ostatnie `MAX_LOG_ENTRIES = 200` wpisów (list w pamięci)
- Podczas odczytu ciągłego (`_timer.isActive()`): wpisy `??` są pomijane; `>>` nigdy nie jest logowane przez timer (port.write bezpośrednio); `<<` jest zawsze logowane

---

## 8. Warstwa UI

### `ui/main_window.py` — MainWindow(QMainWindow)

**Rozmiar:** minimalna szerokość 900 px; minimalna wysokość: 620 px gdy log widoczny, 0 gdy ukryty.

**Menu:**
| Pozycja | Skrót | Akcja |
|---|---|---|
| Waga → Ustawienia połączenia... | Ctrl+U | `_open_settings()` |
| Waga → Terminal... | Ctrl+T | `_open_terminal()` |
| Waga → Opcje aplikacji... | Ctrl+, | `_open_app_settings()` |
| Waga → Zakończ | Alt+F4 | `self.close()` |
| Pomoc → O programie... | F1 | `_open_about()` |

**Przyciski komend (w kolejności):**
1. Odczyt wagi (`#1565c0`) → `service.request_weight()`
2. Odczyt natychmiastowy (`#0277bd`) → `service.request_weight_immediate()`
3. Odczyt ciągły (`#1a237e` / `#3949ab` aktywny) — toggle, `pyqtSignal(bool)`
4. TARA (`#e65100`) → `service.tare()`
5. ZERO (`#6a1b9a`) → `service.zero()`

Kolory przycisków akcji są stałe niezależnie od motywu. Stan wyłączony (`disabled`) pobiera kolory z `ThemeColors.btn_disabled_bg` / `btn_disabled_fg`.

**Log komunikacji:**
- Domyślnie ukryty; checkbox "Pokaż" w nagłówku
- Przy ukryciu: `setMinimumHeight(0)` + `QTimer.singleShot(0, resize)`
- Przy pokazaniu: `setMinimumHeight(620)` + `resize(..., max(height, 620))`
- `QPlainTextEdit`, max 200 bloków, czcionka Courier New 9pt
- Kolory wpisów logu pobierane z `ThemeManager.instance().theme` przy każdym wpisie

**Wskaźnik połączenia ●:**
- Kolory z `ThemeColors.dot_idle` / `dot_connected` / `dot_error`
- Stan jest zapamiętywany w `self._is_connected` i re-aplikowany w `_apply_theme()`

---

### `ui/weight_display.py` — WeightDisplay(QFrame)

Tło: `ThemeColors.bg_display` (ciemny: `#111111`, jasny: `#eeeeee`), border-radius 8px, minimalna wysokość 150px.

**Metody:**
- `update_reading(reading: WeightReading)` — aktualizuje wartość, kolor, status, timestamp; zapisuje `_last_reading`
- `update_stats(min_val, max_val, mean, stddev, unit)` — aktualizuje wiersz Min/Max/Śr/σ; ustawia `_stats_active = True`
- `reset_stats()` — przywraca „Min: ---  Max: ---  Śr: ---  σ: ---"; ustawia `_stats_active = False`
- `_apply_theme()` — ponownie stosuje kolory tła i tekstu; jeśli `_last_reading is not None`, wywołuje `update_reading` dla przywrócenia koloru wartości

Kolory wartości wg statusu i motywu — patrz `_status_color()` w `weight_display.py`:

| Status | Motyw ciemny | Motyw jasny |
|---|---|---|
| `STABLE` | `#00e676` | `#2e7d32` |
| `DYNAMIC` | `#ffa726` | `#e65100` |
| `OVER_RANGE` / `UNDER_RANGE` / `ERROR` | `#ef5350` | `#c62828` |
| `IN_PROGRESS` | `#42a5f5` | `#1565c0` |

Specjalne teksty zamiast wartości liczbowej: `> MAX`, `< MIN`, `ERR`, `...`

Czcionka wartości: Courier New 48pt Bold. Wiersz statystyk: 11pt, wyśrodkowany.

---

### `ui/connection_panel.py` — ConnectionPanel(QGroupBox)

Przyjmuje `ScaleService` i `PresetService`.

**Sygnały:**
```
connect_requested    (port_name, baud_rate, parity, data_bits, stop_bits)
disconnect_requested ()
```

**Trzy rzędy kontrolek:**

- **Rząd 0 — Profile:** `[Profil:] [combo] [Wczytaj] [Zapisz profil…] [Usuń]`
- **Rząd 1:** Protokół | Port COM | ↻ | Baud rate | [Połącz/Rozłącz]
- **Rząd 2:** Długość słowa | Parzystość | Bity stopu

Podczas aktywnego połączenia: dropdowny, ↻ i „Wczytaj" zablokowane. „Zapisz profil…" i „Usuń" zawsze aktywne.

Przy zmianie protokołu: baud rate aktualizuje się na `protocol.default_baud_rate`.  
„Wczytaj" wypełnia wszystkie pola formularza wartościami z wybranego profilu.  
„Zapisz profil…" otwiera `QInputDialog` z polem nazwy; jeśli nazwa istnieje — nadpisuje.  
„Usuń" pyta o potwierdzenie przez `QMessageBox`.

---

### `ui/settings_dialog.py` — SettingsDialog(QDialog)

Niemodalne (`setModal(False)`), minimalna szerokość 740 px.  
Zawiera `ConnectionPanel(service, preset_service)` + przycisk Zamknij.  
Połączenia sygnałów: `connect_requested → service.connect`, `disconnect_requested → service.disconnect`, `service.connection_changed → panel.set_connected`.

---

### `ui/terminal_dialog.py` — TerminalDialog(QDialog)

Niemodalne, rozmiar początkowy 880×500 px.  
Podzielone `QSplitter` (poziomy, proporcja 3:1):

**Lewa strona:** log terminala (QPlainTextEdit, max 500 bloków, Courier New 9pt)  
**Prawa strona:** legenda komend
- `QListWidget` z komendami aktywnego protokołu (Courier New 9pt)
- Dwuklik → wstawia komendę do pola wejściowego (`UserRole` przechowuje czysty tekst komendy)
- Aktualizuje się przy `service.protocol_changed`

**Wiersz wejściowy:** etykieta + `QLineEdit` (Courier New 10pt) + Wyślij + Wyczyść  
Enter lub Wyślij → `service.send_raw(text)` → automatycznie dołącza `\r\n`  
Pole i przycisk blokują się przy braku połączenia.

---

### `ui/about_dialog.py` — AboutDialog(QDialog)

Modalne, rozmiar stały 450×450 px.  
Zawiera: logo z `img/festisite_nasa-2.PNG` (120×120 px), nazwa "Ważka", wersja "0.204.0",  
autor "Krystian Rutkowski", opis, lista protokołów, informacja o licencji MIT.  
Kolory tekstu pobierane z `ThemeManager.instance().theme` przy tworzeniu — reaguje na motyw bez podłączania się do `theme_changed` (dialog jest zawsze tworzony od nowa).

---

### `ui/app_settings_dialog.py` — AppSettingsDialog(QDialog)

Modalne okno "Opcje aplikacji". Otwierane przez `Waga → Opcje aplikacji...` (`Ctrl+,`).

Zawiera dwie sekcje `QGroupBox`:

**"Motyw"** — dwa `QRadioButton`: Ciemny (domyślny) / Jasny. Radio button odpowiadający aktualnemu motywowi jest zaznaczony przy otwarciu.

**"Interwał odczytu ciągłego"** — `QComboBox` wypełniany z `AVAILABLE_INTERVALS` (250 ms, 500 ms, 1000 ms, 2000 ms, 5000 ms, 10 000 ms). Aktualny interwał z `AppSettingsService.interval_ms` jest wstępnie zaznaczony.

Po kliknięciu OK: `ThemeManager.instance().set_theme(name)` + `AppSettingsService.set_theme(name)` + `AppSettingsService.set_interval_ms(ms)` + `ScaleService.set_continuous_interval(ms)`.  
Po kliknięciu Anuluj: bez zmian.

---

## 9. Przepływ sygnałów Qt

```
ConnectionPanel.connect_requested(port, baud, parity, data_bits, stop_bits)
    → ScaleService.connect(...)
        → ScaleService.connection_changed(True)
            → MainWindow._on_connection_changed(True)   [aktualizuje ●, pasek]
            → ConnectionPanel.set_connected(True)       [blokuje kontrolki]
            → TerminalDialog._on_connection_changed(True)

ScaleService.reading_updated(WeightReading)
    → MainWindow._on_reading(reading)
        → WeightDisplay.update_reading(reading)

ScaleService.log_added(str)
    → MainWindow._on_log(entry)          [główny log]
    → TerminalDialog._on_log(entry)      [log terminala, jeśli okno zostało otwarte]

ConnectionPanel._on_protocol_changed(index)
    → ScaleService.set_protocol(protocol)
        → ScaleService.protocol_changed(protocol)
            → TerminalDialog._rebuild_commands(protocol)
```

---

## 10. Ważne decyzje projektowe i naprawione błędy

### Krytyczny błąd — sygnały RS-232 (naprawiono w 0.197.1)

Sygnały `QSerialPort.readyRead` i `errorOccurred` znalazły się **po `return`** w propercie `connection_info` — były martwym kodem. Żadna waga nigdy nie wysyłała danych do parsera. Przeniesiono je do `__init__`. **Należy pilnować, żeby nie trafić tam ponownie przy refaktoringu.**

### Format 0,000g — parser awaryjny

Wagi Mettler Toledo (i inne) wysyłają wartość zero w kompaktowym formacie `0,000g` (przecinek dziesiętny, brak spacji przed jednostką) — żaden protokół tego nie obsługuje. Rozwiązanie: `_fallback_parse()` w `scale_service.py` jako ostatnia linia obrony.

### Tłumienie logu podczas odczytu ciągłego

Timer pisze na port bezpośrednio (`self._port.write(...)`) zamiast przez `_send()` — dzięki temu wpisy `>>` nie zaśmiecają logu. Wpisy `<<` są zawsze logowane. Wpisy `??` są tłumione podczas trybu ciągłego.

### Zmiana rozmiaru okna przy ukrytym logu

`setVisible(False)` samo w sobie nie zmniejsza okna. Wymagane: `setMinimumHeight(0)` + `QTimer.singleShot(0, lambda: self.resize(..., self.sizeHint().height()))`. Opóźnienie jest konieczne — Qt musi najpierw przeliczać layout.

### PyInstaller — brakujący moduł

`PyQt6.QtSerialPort` nie jest wykrywany automatycznie przez PyInstaller. Wymagana flaga: `--hidden-import=PyQt6.QtSerialPort`.

### Separator dziesiętny

Polskie locale używa przecinka. Parser konwertuje `,` → `.` przed `float()` we wszystkich protokołach.

---

## 11. Testy jednostkowe

Projekt zawiera 7 plików testowych uruchamianych przez `pytest`. Testy nie wymagają podłączonej wagi fizycznej.

**Uruchomienie:**
```bash
python -m pytest tests/ -v
```

**Konfiguracja (`pytest.ini`):**
```ini
[pytest]
testpaths = tests
pythonpath = .
```

| Plik testu | Testowany moduł | Liczba testów |
|---|---|---|
| `test_models.py` | `WeightStatus`, `WeightReading`, `ScalePreset` | 10 |
| `test_protocol_mettler.py` | `MettlerSicsProtocol.parse_response` | 21 |
| `test_protocol_sartorius.py` | `SartoriusSbiProtocol.parse_response` | 17 |
| `test_protocol_radwag.py` | `RadwagProtocol.parse_response` | 19 |
| `test_protocol_cbcp03.py` | `RadwagCbcp03Protocol.parse_response` | 28 |
| `test_fallback_parse.py` | `_fallback_parse` (parser awaryjny) | 12 |
| `test_preset_service.py` | `PresetService` (zapis/odczyt JSON) | 16 |

Testy `PresetService` używają `monkeypatch.setattr` do przekierowania `_PRESETS_FILE` na katalog tymczasowy `tmp_path`, dzięki czemu nie modyfikują pliku `presets.json` użytkownika.

---

## 12. Budowanie pliku wykonywalnego

### Windows (.exe)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --hidden-import=PyQt6.QtSerialPort --add-data "img;img" --name Wazka main.py
```

Wynik: `dist/Wazka.exe` — przenośny, nie wymaga Pythona na docelowym komputerze. Rozmiar: ~35 MB.

### Linux (plik binarny)

```bash
pip install pyinstaller
pyinstaller --onefile --hidden-import=PyQt6.QtSerialPort --add-data "img:img" --name Wazka main.py
```

Wynik: `dist/Wazka`. Na Linuksie może być wymagane zainstalowanie bibliotek Qt: `libxcb-*`, `libgl1`.

### macOS (.app)

```bash
pip install pyinstaller
pyinstaller --onedir --windowed --hidden-import=PyQt6.QtSerialPort --add-data "img:img" --name Wazka main.py
```

Wynik: `dist/Wazka.app` — bundle aplikacji macOS. Budowanie musi być wykonane na docelowej architekturze (Intel lub Apple Silicon — pliki binarne nie są wzajemnie kompatybilne).

---

`--hidden-import=PyQt6.QtSerialPort` jest wymagany we wszystkich systemach — PyInstaller nie wykrywa automatycznie `QSerialPort`, ponieważ jest ładowany dynamicznie przez Qt.

`--add-data` dołącza katalog `img/` z logo aplikacji. Separator: `;` na Windows, `:` na Linuksie i macOS.

`main.py` zawiera `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))` — wymagane dla poprawnych importów w spakowanym pliku wykonywalnym.

---

## 13. Możliwe kierunki rozbudowy

### Funkcjonalne
- **Eksport danych** — zapis odczytów do pliku CSV/Excel z timestampem (przydatne przy odczycie ciągłym)
- **Wykres** — wizualizacja wartości w czasie (np. `pyqtgraph` lub `matplotlib` embedded)
- ~~**Rozszerzone statystyki**~~ — zaimplementowano w wersji 0.204.0
- ~~**Konfiguracja interwału**~~ — zaimplementowano w wersji 0.204.0
- **Dźwięk** / powiadomienie przy przekroczeniu zakresu
- **Historia sesji** — zapis i odczyt logów z poprzednich sesji

### Techniczne
- **Obsługa Ethernet** — protokoły Radwag i Mettler obsługują też TCP/IP; dodanie `QTcpSocket` obok `QSerialPort`
- **macOS** — potwierdzono kompatybilność (PyQt6 + QSerialPort działają natywnie na Intel i Apple Silicon); udokumentowane w sekcji 12
- **Nowe protokoły** — Kern (SFB), A&D (AD-8920), Ohaus (Scout Pro) — patrz sekcja 9 DOKUMENTACJA.md
- **Konfiguracja printoutu** — tryb automatycznych wydruków (C1/CU1 w CBCP-03)

### UI
- ~~**Tryb ciemny / jasny**~~ — zaimplementowano w wersji 0.203.0
- **Powiększenie wyświetlacza** — skala czcionki ustawiana przez użytkownika
- **Zakładki protokołów** — jednoczesne połączenie z wieloma wagami na różnych portach

---

## 14. Konwencje kodowania

- **Python 3.10+** — używać union-type `X | Y` zamiast `Optional[X]`, match/case gdzie sensowne
- **Sygnały Qt** — `pyqtSignal(object)` dla obiektów (WeightReading, ScaleProtocol)
- **Nowy protokół** — dziedziczyć po `ScaleProtocol`, nadpisać wszystkie `@abstractmethod`, dodać do `AVAILABLE_PROTOCOLS` w `scale_service.py`; lista pojawi się automatycznie w UI
- **Bez komentarzy do oczywistego kodu** — komentarze tylko gdy motywacja jest nieoczywista
- **Brak obsługi błędów dla niemożliwych przypadków** — `ValueError` przy `float()` jest obsługiwany, bo dane RS-232 mogą być zepsute; reszta nie
- **Kolory** — definiowane w `ui/theme.py` jako pola `ThemeColors`; nigdy nie używać hardkodowanych wartości hex poza `DARK` i `LIGHT` w `theme.py`. W komponentach UI zawsze sięgać po `ThemeManager.instance().theme.<pole>`
- **Wcięcia** — 4 spacje; bez tabulacji
- **Zakończenia linii wysyłanych komend** — zawsze `\r\n` (bytes), niezależnie od platformy

---

## 15. Changelog

### 0.204.0 — 2026-05-10 *(bieżąca)*

- **Rozszerzone statystyki sesji** — dodano średnią (`Śr`) i odchylenie standardowe (`σ`) obok istniejących min/max. Algorytm Welford'a zapewnia stabilność numeryczną.
- Sygnał `session_stats_updated`: `(float, float, str)` → `(float, float, float, float, str)` — min, max, mean, stddev, unit.
- `WeightDisplay` — nowe etykiety Śr i σ w wierszu statystyk.
- **Konfiguracja interwału odczytu ciągłego** — `AppSettingsDialog` rozszerzony o grupę "Interwał odczytu ciągłego" (`QComboBox`, wartości 250–10 000 ms). Ustawienie zapisywane w `app_settings.json`.
- Nowa metoda `ScaleService.set_continuous_interval(ms: int)`.
- `AppSettingsService` — nowe pole `interval_ms` (domyślnie 1000) i metoda `set_interval_ms(ms)`.
- Stała `AVAILABLE_INTERVALS` w `app_settings_service.py`.

---

### 0.203.0 — 2026-05-10

- **System motywów** (`ui/theme.py`): `ThemeColors` (frozen dataclass ~40 pól), `DARK`, `LIGHT`, `ThemeManager` (singleton `QObject`, sygnał `theme_changed`).
- Zmiana motywu działa na żywo — `theme_changed` powiadamia wszystkie komponenty UI przez `_apply_theme()`; aktualizowana jest też `QPalette` aplikacji.
- Nowy serwis `AppSettingsService` (`services/app_settings_service.py`) — persystencja motywu w `app_settings.json`.
- Nowe okno `AppSettingsDialog` (`ui/app_settings_dialog.py`) — wybór motywu, dostępne przez `Waga → Opcje aplikacji...` (`Ctrl+,`).
- `main.py` inicjuje `ThemeManager` przed tworzeniem okna — brak przeflashowania przy starcie.
- Kolory stanu wagi, logu i wskaźnika połączenia dostosowane do obu motywów.

---

### 0.202.0 — 2026-05-09

- Dodano `ScalePreset` (dataclass) i `PresetService` — zapis i odczyt profili wag w `presets.json`.
- `ConnectionPanel` rozszerzony o rząd zarządzania profilami; `SettingsDialog` i `MainWindow` zaktualizowane.
- Statystyki sesji (min/max) w `ScaleService` i `WeightDisplay`; sygnały `session_stats_updated` i `session_stats_reset`.
- Testy jednostkowe (pytest): 7 plików, ~123 testy pokrywające parsery, modele i `PresetService`.
- **Wsparcie macOS** — potwierdzona kompatybilność z macOS 10.15+ (Intel i Apple Silicon). Brak zmian w kodzie; wymagany sterownik USB-RS-232 (FTDI / CP2102 / CH340) i zatwierdzenie rozszerzenia systemowego. Porty dostępne jako `/dev/cu.usbserial-*`.
- Dokumentacja rozszerzona o instalację i budowanie dla Linuksa i macOS.
