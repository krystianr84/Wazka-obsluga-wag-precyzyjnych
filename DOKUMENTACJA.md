# Dokumentacja techniczna — Ważka

**Wersja: 0.204.0**

## Spis treści

1. [Cel i zakres projektu](#1-cel-i-zakres-projektu)
2. [Architektura aplikacji](#2-architektura-aplikacji)
3. [Warstwa modeli](#3-warstwa-modeli)
4. [Warstwa protokołów](#4-warstwa-protokołów)
5. [Warstwa serwisów](#5-warstwa-serwisów)
6. [Warstwa interfejsu użytkownika](#6-warstwa-interfejsu-użytkownika)
7. [Przepływ danych](#7-przepływ-danych)
8. [Protokoły komunikacyjne](#8-protokoły-komunikacyjne--parametry-rs-232)
9. [Konfiguracja portu szeregowego](#9-konfiguracja-portu-szeregowego)
10. [Budowanie aplikacji](#10-budowanie-aplikacji)
11. [Testy jednostkowe](#11-testy-jednostkowe)
12. [Changelog](#12-changelog)

---

## 1. Cel i zakres projektu

Ważka to wieloplatformowa aplikacja desktopowa napisana w **Python 3 / PyQt6**, służąca do komunikacji z wagami przemysłowymi i laboratoryjnymi przez port szeregowy RS-232. Działa na systemach **Windows 10/11**, **Linux** (Ubuntu 22.04+, Fedora 38+ i inne) oraz **macOS 10.15+** (Intel i Apple Silicon).

Aplikacja:

- wyświetla bieżącą wartość ważenia (wartość, jednostka, status, timestamp),
- wysyła komendy do wagi (odczyt jednorazowy, odczyt natychmiastowy, tara, zerowanie),
- obsługuje tryb odczytu ciągłego (co 1 sekundę),
- umożliwia ręczne wydawanie komend przez wbudowany terminal RS-232,
- obsługuje cztery protokoły komunikacyjne (Mettler Toledo MT-SICS, Sartorius SBI, Radwag R Protocol, Radwag CBCP-03),
- pozwala na pełną konfigurację portu RS-232 (port, baud rate, bity danych, parzystość, bity stopu),
- umożliwia zapisywanie i szybkie wczytywanie profili ustawień wagi,
- śledzi statystyki sesji (min, max, średnia i odchylenie standardowe od ostatniej tary/zerowania),
- umożliwia wybór motywu wyglądu (ciemny lub jasny) zapisywanego między sesjami.

**Projekt jest pracą zaliczeniową** z przedmiotu Programowanie obiektowe I, Semestr IV.  
Autor: **Krystian Rutkowski** · Licencja: MIT.

---

## 2. Architektura aplikacji

Aplikacja zbudowana jest w oparciu o wzorzec warstwowy zbliżony do MVC:

```
┌─────────────────────────────────────────┐
│              UI (PyQt6)                 │
│  MainWindow / WeightDisplay / Dialogi   │
└──────────────────┬──────────────────────┘
                   │ sygnały Qt
┌──────────────────▼──────────────────────┐
│            ScaleService                 │
│   QObject z sygnałami, QSerialPort,     │
│   QTimer, wybór protokołu              │
└──────────────────┬──────────────────────┘
                   │ parse_response()
┌──────────────────▼──────────────────────┐
│           Protokoły (4 szt.)            │
│  ScaleProtocol (ABC) → implementacje    │
└──────────────────┬──────────────────────┘
                   │ WeightReading
┌──────────────────▼──────────────────────┐
│              Modele                     │
│   WeightReading, WeightStatus           │
└─────────────────────────────────────────┘
```

Komunikacja między warstwami odbywa się przez **sygnały i sloty Qt** — warstwy nie wywołują się bezpośrednio, co ułatwia testowanie i rozbudowę.

---

## 3. Warstwa modeli

### `models/weight_reading.py`

#### `WeightStatus` (Enum)

Reprezentuje stan pomiaru zwróconego przez wagę.

| Wartość | Opis |
|---|---|
| `STABLE` | Waga stabilna, wynik pewny |
| `DYNAMIC` | Waga w ruchu, wynik przybliżony |
| `OVER_RANGE` | Przekroczenie górnego zakresu |
| `UNDER_RANGE` | Przekroczenie dolnego zakresu |
| `IN_PROGRESS` | Komenda przyjęta, waga pracuje |
| `ERROR` | Błąd komunikacji lub wykonania |

#### `WeightReading` (dataclass)

Pojedynczy odczyt z wagi.

| Pole | Typ | Opis |
|---|---|---|
| `value` | `float` | Wartość masy |
| `unit` | `str` | Jednostka (np. `g`, `kg`, `N`) |
| `status` | `WeightStatus` | Stan pomiaru |
| `timestamp` | `datetime` | Czas odczytu (wypełniany automatycznie) |

Właściwość `formatted_value` zwraca wartość sformatowaną do 3 miejsc dziesiętnych z jednostką.

---

## 4. Warstwa protokołów

### `protocols/scale_protocol.py` — klasa abstrakcyjna

`ScaleProtocol` definiuje interfejs, który musi zaimplementować każdy protokół.

**Właściwości abstrakcyjne (tylko do odczytu):**

| Właściwość | Typ | Opis |
|---|---|---|
| `name` | `str` | Nazwa protokołu wyświetlana w UI |
| `weight_command` | `bytes` | Komenda żądania odczytu stabilnego |
| `weight_immediate_command` | `bytes` | Komenda odczytu natychmiastowego |
| `tare_command` | `bytes` | Komenda tary |
| `zero_command` | `bytes` | Komenda zerowania |
| `default_baud_rate` | `int` | Domyślna prędkość transmisji |

**Metoda abstrakcyjna:**

```python
def parse_response(self, line: str) -> WeightReading | None
```

Parsuje pojedynczą linię odpowiedzi z wagi. Zwraca `WeightReading` lub `None`, jeśli linia nie jest rozpoznana.

---

### Implementacje protokołów

#### `MettlerSicsProtocol` — Mettler Toledo MT-SICS

- **Baud rate:** 9600
- **Zakończenie komend:** `CR LF`

| Komenda | Bajty | Opis |
|---|---|---|
| Odczyt stabilny | `S\r\n` | Czeka na stabilizację |
| Odczyt natychmiastowy | `SI\r\n` | Zwraca aktualny wynik |
| Tara | `T\r\n` | Zeruje z obciążeniem |
| Zero | `Z\r\n` | Zeruje bez obciążenia |

Format odpowiedzi: `S <STATUS> <WARTOŚĆ> <JEDNOSTKA>`

| Kod statusu | Znaczenie |
|---|---|
| `S` | Stabilna |
| `D` | Dynamiczna |
| `I` | W trakcie |
| `+` | Powyżej zakresu |
| `-` | Poniżej zakresu |

---

#### `SartoriusSbiProtocol` — Sartorius SBI

- **Baud rate:** 1200
- **Zakończenie komend:** `CR LF`

| Komenda | Bajty | Opis |
|---|---|---|
| Odczyt | `P\r\n` | Print — żądanie wyniku |
| Tara | `T\r\n` | Tara |
| Zero | `Z\r\n` | Zero |

Format odpowiedzi: `<ZNAK><WARTOŚĆ> <JEDNOSTKA>`

Pierwszy znak odpowiedzi określa status:

| Znak | Znaczenie |
|---|---|
| `+` | Stabilna, wartość dodatnia |
| `-` | Stabilna, wartość ujemna |
| `S` | Dynamiczna (swinging) |
| `I` | W trakcie |
| `O` | Przekroczenie zakresu |
| `E` | Błąd |

---

#### `RadwagProtocol` — Radwag R Protocol

- **Baud rate:** 9600
- **Zakończenie komend:** `CR LF`

| Komenda | Bajty | Opis |
|---|---|---|
| Odczyt stabilny | `SU\r\n` | W bieżącej jednostce |
| Odczyt natychmiastowy | `SI\r\n` | Natychmiast |
| Tara | `T\r\n` | Tara |
| Zero | `Z\r\n` | Zero |

Format odpowiedzi (dwie obsługiwane odmiany):

```
ST,GS,+   50.000000 g    ← z przecinkami
ST +      50.000000 g    ← ze spacjami
```

| Kod | Znaczenie |
|---|---|
| `ST` | Stabilna |
| `US` | Dynamiczna |
| `OI` | W trakcie |
| `OL` | Przekroczenie zakresu |

---

#### `RadwagCbcp03Protocol` — Radwag CBCP-03

- **Baud rate:** 9600
- **Zakończenie komend:** `CR LF`

| Komenda | Bajty | Opis |
|---|---|---|
| Odczyt stabilny | `S\r\n` | W jednostce podstawowej |
| Odczyt natychmiastowy | `SUI\r\n` | W bieżącej jednostce |
| Tara | `T\r\n` | Tara |
| Zero | `Z\r\n` | Zero |

Format ramki masy (pozycje znaków):

```
Komenda S:    [S][ ][ ][stab][ ][znak][masa 9z][ ][jedn 3z]
Komenda SUI:  [S][U][I][stab][ ][znak][masa 9z][ ][jedn 3z]
Printout:     [stab][ ][znak][masa 9z][ ][jedn 3z]
```

Znak stabilności:

| Znak | Znaczenie |
|---|---|
| ` ` (spacja) | Stabilna |
| `?` | Dynamiczna |
| `^` | Powyżej zakresu |
| `v` | Poniżej zakresu |

Odpowiedzi statusowe:

| Format | Znaczenie |
|---|---|
| `XX A` | Komenda przyjęta, w toku |
| `XX D` | Komenda zakończona |
| `XX I` | Komenda niemożliwa do wykonania |
| `XX OK` | Komenda wykonana (np. `DH OK`) |
| `XX E` | Błąd — timeout oczekiwania na stabilizację |
| `XX ^` | Przepełnienie zakresu (np. `Z ^`) |
| `XX v` | Poniżej zakresu (np. `T v`) |
| `ES` | Komenda niezrozumiana |
| `OL` | Waga powyżej zakresu |
| `LO` | Waga poniżej zakresu |

---

## 5. Warstwa serwisów

### `services/scale_service.py`

Klasa `ScaleService` dziedziczy po `QObject` i stanowi serce aplikacji. Zarządza połączeniem szeregowym, wysyłaniem komend i parsowaniem odpowiedzi.

#### Sygnały

| Sygnał | Typ parametru | Opis |
|---|---|---|
| `reading_updated` | `WeightReading` | Nowy odczyt z wagi |
| `log_added` | `str` | Nowy wpis w logu |
| `connection_changed` | `bool` | Zmiana stanu połączenia |
| `error_occurred` | `str` | Błąd portu lub połączenia |
| `continuous_changed` | `bool` | Zmiana trybu ciągłego odczytu |
| `session_stats_updated` | `float, float, float, float, str` | Zaktualizowane min, max, średnia, odch. std., jednostka |
| `session_stats_reset` | — | Statystyki sesji zresetowane |

#### Stałe

```python
AVAILABLE_PROTOCOLS   # lista wszystkich protokołów
AVAILABLE_BAUD_RATES  # [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200]
PARITY_OPTIONS        # mapowanie nazw parzystości na QSerialPort.Parity
DATA_BITS_OPTIONS     # mapowanie nazw na QSerialPort.DataBits
MAX_LOG_ENTRIES = 200
```

#### Metody publiczne

```python
connect(port_name, baud_rate, parity, data_bits)
    # Otwiera port szeregowy z podanymi parametrami.
    # Emituje connection_changed(True) przy sukcesie.

disconnect()
    # Zamyka port. Zatrzymuje odczyt ciągły.
    # Emituje connection_changed(False).

request_weight()
    # Wysyła komendę odczytu stabilnego.

request_weight_immediate()
    # Wysyła komendę odczytu natychmiastowego.

tare()
    # Wysyła komendę tary.

zero()
    # Wysyła komendę zerowania.

start_continuous()
    # Uruchamia QTimer (konfigurowalny interwał, domyślnie 1000 ms).
    # Podczas odczytu ciągłego log komunikacji jest wyciszony.

stop_continuous()
    # Zatrzymuje timer odczytu ciągłego.

set_continuous_interval(ms: int)
    # Ustawia interwał timera; restartuje timer jeśli był aktywny.
```

#### Logika parsowania

Dla każdej odebranej linii:

1. Wywoływane jest `protocol.parse_response(line)`.
2. Jeśli zwróci `None` — wywoływany jest `_fallback_parse(line)`.
3. Jeśli oba zwrócą `None` — linia jest logowana jako nierozpoznana (`??`).

**Parser awaryjny `_fallback_parse`** obsługuje kompaktowy format bez prefiksu komendy, np. `0,000g` lub `50.000 g`. Używany gdy waga wysyła same cyfry i jednostkę bez dodatkowych pól statusu.

---

## 6. Warstwa interfejsu użytkownika

### `ui/main_window.py` — `MainWindow`

Główne okno aplikacji (`QMainWindow`).

**Elementy UI (od góry):**

1. **Pasek menu** — Waga (Ustawienia `Ctrl+U`, Terminal `Ctrl+T`, Opcje aplikacji `Ctrl+,`, Zakończ `Alt+F4`), Pomoc (O programie `F1`)
2. **Pasek połączenia** — kolorowy wskaźnik ●, informacje o połączeniu, przycisk ustawień
3. **Wyświetlacz wagi** — duża czcionka z wartością, status, timestamp
4. **Przyciski komend** — Odczyt wagi, Odczyt natychmiastowy, Odczyt ciągły, TARA, ZERO
5. **Nagłówek logu** — etykieta + checkbox "Pokaż"
6. **Obszar logu** — domyślnie ukryty, pokazywany po zaznaczeniu checkboxa

**Kolory wskaźnika połączenia** (zależne od motywu):

| Stan | Motyw ciemny | Motyw jasny |
|---|---|---|
| Rozłączono | Szary `#555555` | Szary `#9e9e9e` |
| Połączono | Zielony `#00e676` | Zielony `#2e7d32` |
| Błąd | Czerwony `#ef5350` | Czerwony `#c62828` |

**Kodowanie kolorów logu** (zależne od motywu):

| Prefiks | Motyw ciemny | Motyw jasny | Znaczenie |
|---|---|---|---|
| `>>` | `#64b5f6` (niebieski) | `#1565c0` (granatowy) | Wysłana komenda |
| `<<` | `#81c784` (zielony) | `#2e7d32` (ciemnozielony) | Odebrana odpowiedź |
| `??` | `#ff8a65` (pomarańczowy) | `#bf360c` (brązowy) | Nierozpoznana odpowiedź |
| `BŁĄD` | `#ef5350` (czerwony) | `#c62828` (ciemnoczerwony) | Błąd |
| `Połączono`/`Rozłączono` | `#fff176` (żółty) | `#e65100` (pomarańczowy) | Zmiana stanu |

---

### `ui/weight_display.py` — `WeightDisplay`

Komponent wyświetlający aktualny odczyt wagi.

- Wartość wyświetlana czcionką **Courier New 48pt**
- Kolor wartości zmienia się w zależności od statusu i aktywnego motywu:

| Status | Motyw ciemny | Motyw jasny |
|---|---|---|
| `STABLE` | Zielony `#00e676` | Ciemnozielony `#2e7d32` |
| `DYNAMIC` | Pomarańczowy `#ffa726` | Pomarańczowy `#e65100` |
| `OVER_RANGE` / `UNDER_RANGE` | Czerwony `#ef5350` | Ciemnoczerwony `#c62828` |
| `IN_PROGRESS` | Niebieski `#42a5f5` | Granatowy `#1565c0` |
| `ERROR` | Czerwony `#ef5350` | Ciemnoczerwony `#c62828` |

- **Wiersz statystyk sesji** — pod paskiem statusu wyświetlane są wartości `Min`, `Max`, `Śr` (średnia) i `σ` (odchylenie standardowe) od ostatniego resetu.  
  Metody: `update_stats(min_val, max_val, mean, stddev, unit)` i `reset_stats()`.

---

### `ui/connection_panel.py` — `ConnectionPanel`

Panel konfiguracji połączenia osadzony w oknie ustawień.

**Sygnały:**

```python
connect_requested    = pyqtSignal(str, int, object, object, object)
# (port_name, baud_rate, parity, data_bits, stop_bits)

disconnect_requested = pyqtSignal()
```

**Trzy rzędy kontrolek:**

- **Rząd 0 — Profile:** lista zapisanych profili, przyciski „Wczytaj", „Zapisz profil…", „Usuń"
- **Rząd 1:** Protokół | Port COM | ↻ | Baud rate | [Połącz/Rozłącz]
- **Rząd 2:** Długość słowa | Parzystość | Bity stopu

Podczas aktywnego połączenia dropdowny, przycisk ↻ i przycisk „Wczytaj" są zablokowane. Zapis i usuwanie profili są dostępne zawsze.

---

### `ui/settings_dialog.py` — `SettingsDialog`

Niemodalne okno dialogowe (`setModal(False)`) zawierające `ConnectionPanel`. Może być otwarte równolegle z głównym oknem. Przyjmuje `PresetService` i przekazuje go do panelu.

---

### `ui/about_dialog.py` — `AboutDialog`

Modalne okno "O programie" z informacjami o aplikacji, wersji, autorze i obsługiwanych protokołach. Czyta aktywny motyw przy każdym otwarciu, więc zawsze wyświetla kolory zgodne z bieżącym ustawieniem.

---

### `ui/theme.py` — system motywów

Moduł definiuje:

**`ThemeColors` (frozen dataclass)** — zestaw ~40 pól z wartościami kolorów CSS (hex) dla jednego motywu. Pola pokrywają tła, obramowania, teksty, kolory stanu wagi, kolory przycisków akcji, kolory logu i wskaźnika połączenia.

**`DARK`, `LIGHT`** — dwie gotowe instancje `ThemeColors`:
- `DARK` — motyw ciemny (domyślny): tła `#111111`–`#2a2a2a`, tekst `#cccccc`, neonowe kolory stanu
- `LIGHT` — motyw jasny: tła `#eeeeee`–`#ffffff`, tekst `#212121`, ciemniejsze nasycone kolory stanu

**`ThemeManager(QObject)`** — singleton zarządzający aktywnym motywem:

```python
ThemeManager.instance() -> ThemeManager   # dostęp do singletonu
ThemeManager.initialize(name: str)        # ustawia motyw przed tworzeniem okien (bez sygnału)
ThemeManager.theme -> ThemeColors         # bieżące kolory
ThemeManager.set_theme(name: str)         # zmienia motyw, emituje theme_changed, aktualizuje QPalette
ThemeManager.build_initial_palette() -> QPalette  # paleta Qt dla Fusion (przed pierwszym oknem)

theme_changed = pyqtSignal()              # emitowany po każdej zmianie motywu
```

Przy zmianie motywu (`set_theme`) automatycznie aktualizowana jest `QPalette` aplikacji — dzięki temu widgety bez własnych arkuszy stylu (np. `QComboBox`, `QGroupBox`) też stosują właściwe kolory.

Każdy komponent UI łączy się z sygnałem `theme_changed` i implementuje metodę `_apply_theme()`, która ustawia na nowo swoje `setStyleSheet()` korzystając z `ThemeManager.instance().theme`.

---

### `ui/app_settings_dialog.py` — `AppSettingsDialog`

Modalne okno "Opcje aplikacji" (`Ctrl+,`). Zawiera dwie grupy:

**Motyw** — przyciski radio:
- **Ciemny (domyślny)**
- **Jasny**

**Interwał odczytu ciągłego** — lista rozwijana z wartościami: 250 ms, 500 ms, 1000 ms (domyślny), 2000 ms, 5000 ms, 10 000 ms.

Po kliknięciu OK: zmiany są natychmiastowe (bez restartu aplikacji) i zapisywane do `app_settings.json` przez `AppSettingsService`.

---

### `services/app_settings_service.py` — `AppSettingsService`

Serwis odczytu i zapisu pliku `app_settings.json` w katalogu głównym projektu.

```json
{ "theme": "dark", "interval_ms": 1000 }
```

| Metoda / właściwość | Opis |
|---|---|
| `theme -> str` | Aktywna nazwa motywu (`"dark"` lub `"light"`) |
| `set_theme(name)` | Ustawia motyw i zapisuje plik |
| `interval_ms -> int` | Interwał odczytu ciągłego w milisekundach (domyślnie 1000) |
| `set_interval_ms(ms)` | Ustawia interwał i zapisuje plik |

Dostępne interwały definiuje stała `AVAILABLE_INTERVALS: list[tuple[int, str]]` w module `app_settings_service.py`.

---

## 7. Przepływ danych

### Odczyt wartości z wagi

```
Użytkownik klika "Odczyt wagi"
        │
        ▼
MainWindow._btn_weight.clicked
        │
        ▼
ScaleService.request_weight()
        │  pisze weight_command na port
        ▼
QSerialPort.write(bytes)
        │
        ▼
  [Waga przetwarza komendę]
        │
        ▼
QSerialPort.readyRead (sygnał Qt)
        │
        ▼
ScaleService._on_ready_read()
  ├─ normalizacja zakończeń linii (\r\n → \n)
  ├─ buforowanie i podział na linie
  ├─ protocol.parse_response(line)
  │     └─ [None] → _fallback_parse(line)
  └─ reading_updated.emit(WeightReading)
        │
        ▼
MainWindow._on_reading(reading)
        │
        ▼
WeightDisplay.update_reading(reading)
```

### Odczyt ciągły

```
Użytkownik klika "Odczyt ciągły"
        │
        ▼
ScaleService.start_continuous()
  └─ QTimer.start(interval_ms)
        │
  co 1000 ms:
        ▼
ScaleService._on_timer_tick()
  └─ QSerialPort.write(weight_immediate_command)
        │  [log wyciszony]
        ▼
  [parsowanie jak wyżej]
        │
        ▼
WeightDisplay.update_reading(reading)
```

---

## 8. Protokoły komunikacyjne — parametry RS-232

Domyślne parametry dla poszczególnych protokołów:

| Protokół | Baud rate | Bity danych | Parzystość | Bity stopu |
|---|---|---|---|---|
| MT-SICS | 9600 | 8 | Brak | 1 |
| SBI | 1200 | 8 | Brak | 1 |
| Radwag R | 9600 | 8 | Brak | 1 |
| CBCP-03 | 9600 | 8 | Brak | 1 |

Wszystkie parametry można zmienić ręcznie w oknie ustawień połączenia.

---

## 9. Konfiguracja portu szeregowego

Dostępne opcje parzystości:

| Nazwa | Symbol | `QSerialPort.Parity` |
|---|---|---|
| Brak (N) | N | `NoParity` |
| Parzysta (E) | E | `EvenParity` |
| Nieparzysta (O) | O | `OddParity` |
| Space (S) | S | `SpaceParity` |
| Mark (M) | M | `MarkParity` |

Dostępne długości słowa: **5, 6, 7, 8** bitów.

Dostępne baud rates: **1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200**.

Notacja wyświetlana w pasku połączenia: `COM3  @  9600 baud  |  8N1  [Radwag CBCP-03]`

---

## 10. Budowanie aplikacji

### Uruchomienie ze źródeł

```bash
pip install -r requirements.txt
python main.py
```

Polecenie działa identycznie na Windows, Linuksie i macOS. Poniżej opisane są wymagania specyficzne dla każdego systemu.

---

### Windows

Brak dodatkowych wymagań — dostęp do portów COM jest dostępny bez konfiguracji.

### Linux — dostęp do portów szeregowych

Użytkownik musi należeć do grupy `dialout` (lub `uucp` na niektórych dystrybucjach):

```bash
sudo usermod -aG dialout $USER   # wyloguj się i zaloguj ponownie
```

Porty mają nazwy `/dev/ttyUSB0`, `/dev/ttyACM0`, `/dev/ttyS0` itp.  
`QSerialPortInfo.availablePorts()` i `QSerialPort` obsługują je automatycznie.

### macOS — sterowniki USB-RS-232

macOS nie zawiera sterowników dla popularnych układów USB-RS-232. Należy zainstalować sterownik odpowiedni dla adaptera:

| Układ scalony | Sterownik |
|---|---|
| FTDI FT232 | Oficjalny sterownik FTDI VCP |
| Silicon Labs CP2102 | Oficjalny sterownik Silicon Labs CP210x |
| CH340 / CH341 | Sterownik WCH (github.com/WCHSoftGroup/ch34xser_macos) |

Po instalacji sterownika macOS wyświetli monit o zatwierdzenie rozszerzenia systemowego w **Ustawienia systemowe → Prywatność i bezpieczeństwo**. Może być wymagane ponowne uruchomienie.

Porty pojawiają się jako `/dev/cu.usbserial-*` (zalecane) lub `/dev/tty.usbserial-*`. Różnica: wariant `cu.*` nie czeka na sygnał DCD — jest właściwy do komunikacji z wagami. W aplikacji zawsze wybieraj port `cu.*`.

`QSerialPortInfo.availablePorts()` działa poprawnie na macOS i wykrywa oba warianty nazw.

---

### Budowanie pliku wykonywalnego — Windows

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --hidden-import=PyQt6.QtSerialPort --add-data "img;img" --name Wazka main.py
```

Parametr `--hidden-import=PyQt6.QtSerialPort` jest wymagany — PyInstaller nie wykrywa automatycznie modułu `QSerialPort`, ponieważ jest importowany dynamicznie przez Qt.  
Parametr `--add-data "img;img"` dołącza katalog z logo do pliku wykonywalnego (na Windows separator to `;`).

Wynik: `dist/Wazka.exe` — przenośny, nie wymaga Pythona na docelowym komputerze.

### Budowanie pliku wykonywalnego — Linux

```bash
pip install pyinstaller
pyinstaller --onefile --hidden-import=PyQt6.QtSerialPort --add-data "img:img" --name Wazka main.py
```

Wynik: `dist/Wazka` — samowystarczalny plik binarny.  
Na Linuksie może być wymagane zainstalowanie systemowych bibliotek Qt: `libxcb-*`, `libgl1`.

### Budowanie pliku wykonywalnego — macOS

```bash
pip install pyinstaller
pyinstaller --onedir --windowed --hidden-import=PyQt6.QtSerialPort --add-data "img:img" --name Wazka main.py
```

Wynik: `dist/Wazka.app` — bundle aplikacji macOS.

**Ważne:** budowanie należy wykonać na docelowej architekturze. Plik skompilowany na Macu Intel nie uruchomi się natywnie na Apple Silicon (M1/M2/M3/M4) i odwrotnie. Nie ma możliwości jednoczesnego budowania dla obu architektur z jednego środowiska (cross-compilation).

> Na Linuksie i macOS separatorem w `--add-data` jest `:`. Ścieżka jest w formacie `źródło:cel_w_bundlu`.

---

## Dodanie nowego protokołu

1. Utwórz plik `protocols/nowy_protokol.py`.
2. Zaimplementuj klasę dziedziczącą po `ScaleProtocol`:

```python
from protocols.scale_protocol import ScaleProtocol
from models.weight_reading import WeightReading, WeightStatus

class NowyProtokol(ScaleProtocol):

    @property
    def name(self) -> str:
        return "Nazwa protokołu"

    @property
    def weight_command(self) -> bytes:
        return b"KOMENDA\r\n"

    @property
    def weight_immediate_command(self) -> bytes:
        return b"KOMENDA_NAT\r\n"

    @property
    def tare_command(self) -> bytes:
        return b"T\r\n"

    @property
    def zero_command(self) -> bytes:
        return b"Z\r\n"

    @property
    def default_baud_rate(self) -> int:
        return 9600

    def parse_response(self, line: str) -> WeightReading | None:
        # Implementacja parsowania...
        pass
```

3. Zarejestruj protokół w `services/scale_service.py`:

```python
from protocols.nowy_protokol import NowyProtokol

AVAILABLE_PROTOCOLS: list[ScaleProtocol] = [
    MettlerSicsProtocol(),
    SartoriusSbiProtocol(),
    RadwagProtocol(),
    RadwagCbcp03Protocol(),
    NowyProtokol(),       # ← dodaj tutaj
]
```

Protokół pojawi się automatycznie na liście wyboru w oknie ustawień.

---

## 11. Testy jednostkowe

Testy pokrywają całą logikę biznesową aplikacji — parsery protokołów, modele danych i serwis profili. Komponenty UI (wymagające uruchomionego `QApplication`) nie są testowane jednostkowo.

### Uruchamianie

```bash
# z katalogu głównego projektu
python -m pytest tests/ -v
```

Wymaganie: `pytest` zainstalowany w środowisku wirtualnym (`pip install pytest` lub przez `requirements.txt`).

### Struktura katalogu `tests/`

```
tests/
├── __init__.py
├── test_models.py              # WeightReading, WeightStatus, ScalePreset
├── test_protocol_mettler.py    # MettlerSicsProtocol.parse_response()
├── test_protocol_sartorius.py  # SartoriusSbiProtocol.parse_response()
├── test_protocol_radwag.py     # RadwagProtocol.parse_response()
├── test_protocol_cbcp03.py     # RadwagCbcp03Protocol.parse_response()
├── test_fallback_parse.py      # _fallback_parse() z scale_service
└── test_preset_service.py      # PresetService: zapis, odczyt, usuwanie, persystencja
```

Konfiguracja pytest w `pytest.ini` (katalog główny projektu):

```ini
[pytest]
testpaths = tests
pythonpath = .
```

### Zakres testów

| Plik testów | Liczba testów | Co jest weryfikowane |
|---|---|---|
| `test_models.py` | 10 | `formatted_value`, `status_label`, auto-timestamp, pola `ScalePreset` |
| `test_protocol_mettler.py` | 21 | Stabilna, dynamiczna, tara, zero, zakresy, błędy E\*, separator dziesiętny |
| `test_protocol_sartorius.py` | 17 | Wszystkie znaki statusu (+/−/S/I/O/E), wartości ujemne, brak jednostki |
| `test_protocol_radwag.py` | 19 | Oba formaty (ST,GS vs. ST +), potwierdzenia A, OL, E/ES/ERR |
| `test_protocol_cbcp03.py` | 28 | Prefiksy S/SU/SI/SUI, znaki stabilności ?/^/v, A/D/OK/E/^/v, OL/LO/ES |
| `test_fallback_parse.py` | 12 | Kompaktowe formaty bez prefiksu, separatory , i ., jednostki złożone |
| `test_preset_service.py` | 16 | Zapis nowy, nadpisanie po nazwie, usuwanie, persystencja JSON, uszkodzony plik |
| **Razem** | **123** | |

### Izolacja w testach `PresetService`

`test_preset_service.py` używa fixtury `monkeypatch` z pytest do podmiany ścieżki `_PRESETS_FILE` na katalog tymczasowy (`tmp_path`). Każdy test operuje na osobnym, izolowanym pliku JSON — nie dotyka produkcyjnego `presets.json`.

---

## 12. Changelog

### 0.204.0 — 2026-05-10 *(bieżąca)*

- **Rozszerzone statystyki sesji** — obok min i max wyświetlacz pokazuje teraz średnią (`Śr`) i odchylenie standardowe (`σ`). Algorytm Welford'a — numerycznie stabilny, bez przechowywania całej historii pomiarów.
- Sygnał `session_stats_updated` rozszerzony: `(float, float, str)` → `(float, float, float, float, str)` — min, max, mean, stddev, unit.
- `WeightDisplay` — nowe etykiety `Śr` i `σ` w wierszu statystyk; `update_stats()` przyjmuje 5 argumentów.
- **Konfiguracja interwału odczytu ciągłego** — `AppSettingsDialog` rozszerzony o grupę "Interwał odczytu ciągłego" z listą rozwijaną (250 ms – 10 000 ms). Wybrana wartość jest natychmiast stosowana i zapisywana w `app_settings.json`.
- Nowa metoda `ScaleService.set_continuous_interval(ms: int)` — zmienia interwał QTimer; restartuje timer jeśli aktywny.
- `AppSettingsService` — nowe pole `interval_ms` (domyślnie 1000 ms) i metoda `set_interval_ms(ms)`.
- Stała `AVAILABLE_INTERVALS: list[tuple[int, str]]` w `app_settings_service.py`.

---

### 0.203.0 — 2026-05-10

- **System motywów** — nowy moduł `ui/theme.py` z klasą `ThemeColors` (frozen dataclass), instancjami `DARK` i `LIGHT` oraz singletonem `ThemeManager(QObject)`.
- `ThemeManager` emituje sygnał `theme_changed`; wszystkie komponenty UI (`MainWindow`, `WeightDisplay`, `ConnectionPanel`, `TerminalDialog`, `AboutDialog`) implementują metodę `_apply_theme()` i stosują nowe kolory bez restartu aplikacji.
- Przy zmianie motywu aktualizowana jest `QPalette` aplikacji (Fusion), co zapewnia poprawny wygląd widgetów bez własnych arkuszy stylu (`QComboBox`, `QGroupBox`).
- **Nowe okno** `AppSettingsDialog` (`ui/app_settings_dialog.py`) — przyciski radio "Ciemny (domyślny)" / "Jasny"; dostępne przez `Waga → Opcje aplikacji...` (`Ctrl+,`).
- **Nowy serwis** `AppSettingsService` (`services/app_settings_service.py`) — zapis preferencji motywu w pliku `app_settings.json`; plik tworzony automatycznie przy pierwszej zmianie.
- `main.py` wczytuje ustawienia i inicjuje `ThemeManager` przed tworzeniem okna — aplikacja startuje od razu w wybranym motywie, bez przeflashowania.
- Kolory kolorów stanu wagi, logu i wskaźnika połączenia dostosowane do motywu jasnego (ciemniejsze, nasycone odcienie zapewniające dobry kontrast na jasnym tle).

---

### 0.202.0 — 2026-05-09

- **Statystyki sesji (min/max)** — wyświetlacz wagi pokazuje wartość minimalną i maksymalną od ostatniej tary lub zerowania. Statystyki są resetowane automatycznie przy każdej tarze, zerowaniu i rozłączeniu.
- Dwa nowe sygnały w `ScaleService`: `session_stats_updated(float, float, str)` i `session_stats_reset()`.
- Nowy wiersz statystyk w `WeightDisplay`; metody `update_stats()` i `reset_stats()`.
- **Profile wag** — możliwość zapisywania pełnych ustawień połączenia (protokół, port, baud rate, parzystość, bity danych, bity stopu) pod własną nazwą.
- Nowy model `models/scale_preset.py` (`ScalePreset` dataclass).
- Nowy serwis `services/preset_service.py` (`PresetService`) — zapis i odczyt profili z pliku `presets.json`.
- `ConnectionPanel` rozszerzony o rząd zarządzania profilami: lista profili, „Wczytaj", „Zapisz profil…", „Usuń".
- `SettingsDialog` przyjmuje i przekazuje `PresetService` do panelu.
- Przycisk **⚡ Profile ▾** w pasku połączenia `MainWindow` — kliknięcie otwiera menu z listą profili; wybór profilu natychmiast inicjuje połączenie z wagą.
- Dodano logo aplikacji (`img/festisite_nasa-2.PNG`) do okna „O programie".
- Dodano plik `LICENSE` (MIT, Krystian Rutkowski).
- **Wsparcie macOS** — potwierdzona i udokumentowana kompatybilność z macOS 10.15+ (Intel i Apple Silicon). Aplikacja działa bez zmian w kodzie; wymagana jedynie instalacja sterownika USB-RS-232 (FTDI / CP2102 / CH340) i zatwierdzenie rozszerzenia systemowego w Ustawieniach systemowych. Porty szeregowe dostępne jako `/dev/cu.usbserial-*`.
- **Naprawa: brak logo w pliku wykonywalnym PyInstaller** — `about_dialog.py` używał `__file__` do wyznaczania ścieżki katalogu `img/`, co nie działało w spakowanym exe. Dodano funkcję `_resource_path()` opartą na `sys._MEIPASS`. Komendy budowania rozszerzone o `--add-data "img;img"` (Windows) / `--add-data "img:img"` (Linux, macOS).
- **Dokumentacja** — dodano sekcję `1. Cel i zakres projektu`; pozostałe sekcje przenumerowano (stara 1→2, ..., stara 11→12). Dodano opisy instalacji i budowania dla Linuksa i macOS (sekcja 10).

---

### 0.201.1 — 2026-05-08

- **Terminal: legenda dostępnych komend** — prawa kolumna terminala wyświetla listę komend właściwą dla aktywnego protokołu; dwuklik na pozycji wstawia komendę do pola wejściowego.
- Dodano właściwość `command_list` do klasy bazowej `ScaleProtocol` i do wszystkich czterech implementacji.
- Dodano sygnał `protocol_changed` w `ScaleService`; emitowany przy każdej zmianie protokołu.
- Legenda aktualizuje się automatycznie po wyborze innego protokołu w ustawieniach połączenia.

---

### 0.201.0 — 2026-05-08

- **Terminal komunikacji** (`Waga → Terminal...`, skrót `Ctrl+T`) — niemodalne okno pozwalające na ręczne wysyłanie dowolnych komend do wagi i podgląd odpowiedzi w czasie rzeczywistym.
- Metoda `ScaleService.send_raw(text)` — wysyła surowy tekst na port szeregowy z automatycznym dołączeniem `CR LF`.
- Kolorowy log terminala (ten sam schemat kolorów co główny log).
- Przycisk **Wyczyść** czyści historię w oknie terminala.
- Pole wejściowe i przycisk Wyślij blokują się przy braku połączenia.

---

### 0.200.0 — 2026-05-08

- **Konfiguracja bitów stopu** — dropdown "Bity stopu" (wartości: `1`, `1.5`, `2`) w rzędzie parametrów portu w oknie ustawień.
- Sygnatura `ScaleService.connect()` rozszerzona o parametr `stop_bits`.
- Notacja w pasku połączenia uwzględnia bity stopu (np. `8N2` zamiast `8N1`).
- Dodano stałe `STOP_BITS_OPTIONS` i `_STOP_BITS_LABEL` w `scale_service.py`.

---

### 0.199.0 — 2026-05-08

- **Log komunikacji domyślnie ukryty** — checkbox "Pokaż" przy nagłówku "Log komunikacji:" steruje widocznością obszaru logu.
- Okno automatycznie zmniejsza się po ukryciu logu (`QTimer.singleShot` + `sizeHint()`) i rozszerza po jego pokazaniu.
- Minimalna wysokość okna wynosi 620 px tylko przy widocznym logu.
- Odebrane dane (`<<`) są zawsze widoczne w logu, niezależnie od trybu ciągłego odczytu.

---

### 0.198.0 — 2026-05-08

- **Odczyt ciągły** — przycisk toggle "Odczyt ciągły" (3. pozycja na pasku komend) wysyła `weight_immediate_command` co 1 sekundę przy użyciu `QTimer`.
- `ScaleService.start_continuous()` / `stop_continuous()` — metody zarządzające trybem ciągłym.
- Sygnał `continuous_changed(bool)` informuje UI o zmianie stanu.
- Przy rozłączeniu tryb ciągły jest automatycznie zatrzymywany.
- Podczas odczytu ciągłego log wycisza powtarzające się wpisy `>>` (dane `<<` zawsze widoczne).

---

### 0.197.1 — 2026-05-08

- **Naprawa krytycznego błędu: brak odczytu danych z wagi** — sygnały `QSerialPort.readyRead` i `errorOccurred` były podłączone po instrukcji `return` w propercie `connection_info` (martwy kod). Przeniesiono je do `__init__`. Błąd powodował, że **żadna waga nigdy nie wysyłała danych do parsera**.
- Naprawia: brak odczytu w protokole Sartorius SBI, Radwag i innych.

---

### 0.197.0 — 2026-05-08

- **Protokół Radwag CBCP-03** — czwarty obsługiwany protokół (`protocols/radwag_cbcp03_protocol.py`).
- Implementacja zgodna z dokumentacją CBCP-03 (ITKP-07-01-12-18-EN): obsługa prefiksów ramki masy (`S`, `SI`, `SU`, `SUI`, `DH`), kodów statusu (`XX A/D/I/E/OK/^/v`), stanów `OL`, `LO`, `ES`.
- Dodano import i rejestrację `RadwagCbcp03Protocol` w `AVAILABLE_PROTOCOLS`.
- Nazwa aplikacji zmieniona z "Metler" na **"Ważka"** (okno główne, dialog O programie).
- Dialog "O programie" zaktualizowany: lista protokołów obejmuje wszystkie 4 implementacje.

---

### 0.196.0 — 2026-05-08

- **Menu aplikacji** — pasek menu z pozycjami: `Waga` (Ustawienia `Ctrl+U`, Zakończ `Alt+F4`) i `Pomoc` (O programie `F1`).
- **Okno ustawień połączenia** (`SettingsDialog`) — niemodalne `QDialog` zastępuje panel osadzony w oknie głównym.
- **Okno "O programie"** (`AboutDialog`) — informacje o aplikacji, wersji, autorze i protokołach.
- Kompaktowy **pasek połączenia** z kolorowym wskaźnikiem ●, informacją o aktywnym połączeniu i skrótem do ustawień.

---

### 0.195.0 — 2026-05-07

- **PyInstaller** — konfiguracja budowania przenośnego pliku `.exe` dla Windows 10/11.
- Wymagane flagi: `--onefile --windowed --hidden-import=PyQt6.QtSerialPort`.
- Dodano `sys.path.insert` w `main.py` dla poprawnego działania po spakowaniu.

---

### 0.194.0 — 2026-05-07

- **Protokół Radwag R** (`protocols/radwag_protocol.py`) — obsługa wag serii WLY, WPS, AS, PS.
- Regex obsługuje dwie odmiany formatu: z przecinkami (`ST,GS,+`) i ze spacjami (`ST +`).
- Kody statusu: `ST` (stabilna), `US` (dynamiczna), `OI` (w trakcie), `OL` (poza zakresem).

---

### 0.193.0 — 2026-05-07

- **Naprawa: odczyt wartości 0,000** — wagi wysyłające kompaktowy format bez prefiksu (np. `0,000g`) nie były parsowane przez żaden protokół. Dodano `_fallback_parse()` w `scale_service.py` obsługujący ten format.
- Diagnostyczne logowanie `?? nierozpoznana odpowiedź` ułatwiło identyfikację przyczyny.
- Naprawa normalizacji zakończeń linii RS-232: `\r\n`, `\r`, `\n` → `\n`.
- Naprawa: spacje w logu komunikacji były zwijane przez HTML — zastosowano tagi `<pre>`.

---

### 0.191.0 — 2026-05-07

- **Rozszerzona konfiguracja RS-232** — dodano dropdowny: "Długość słowa" (bity danych: 5–8) i "Parzystość" (Brak, Parzysta, Nieparzysta, Space, Mark).
- Parametry przekazywane do `QSerialPort` przy nawiązaniu połączenia.
- Notacja połączenia w pasku statusu w formacie `XnS` (np. `8N1`).

---

### 0.190.0 — 2026-05-07 *(wersja początkowa)*

- Inicjalny projekt aplikacji w Python 3 / PyQt6.
- **Protokół Mettler Toledo MT-SICS** Level 0/1 (`protocols/mettler_sics_protocol.py`).
- **Protokół Sartorius SBI** (`protocols/sartorius_sbi_protocol.py`).
- Komunikacja przez `QSerialPort` (RS-232): wybór portu COM, baud rate, połącz/rozłącz.
- Wyświetlacz wagi (`WeightDisplay`) z dużą czcionką, kolorem statusu i znacznikiem czasu.
- Log komunikacji z kodowaniem kolorami (`>>` / `<<` / `??` / błędy).
- Architektura warstwowa: modele → protokoły → serwis → UI.
