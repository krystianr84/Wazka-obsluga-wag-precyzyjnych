# Ważka - obsługa wag precyzyjnych

**Wersja 0.204.0**

Aplikacja desktopowa do komunikacji z wagami przemysłowymi i laboratoryjnymi przez interfejs RS-232.  
Napisana w Pythonie z wykorzystaniem biblioteki PyQt6.

---

## Funkcje

- Odczyt wartości ważenia w czasie rzeczywistym
- Odczyt ciągły (automatyczne odpytywanie co 1 sekundę)
- Wykonywanie tary i zerowania
- **Statystyki sesji** — wartość minimalna i maksymalna od ostatniej tary/zerowania
- **Profile wag** — zapisywanie ustawień połączenia i szybkie łączenie z wybraną wagą
- Obsługa czterech protokołów komunikacyjnych
- Konfigurowalne parametry portu szeregowego (port, baud rate, parzystość, bity danych, bity stopu)
- Kolorowy log komunikacji z możliwością ukrycia
- Terminal komend RS-232 z legendą komend protokołu
- **Motywy wyglądu** — wybór między motywem ciemnym (domyślnym) a jasnym; ustawienie zapisywane między sesjami

## Obsługiwane protokoły

| Protokół | Producent | Modele |
|---|---|---|
| MT-SICS Level 0/1 | Mettler Toledo | XPE, XSE, ME, AB, PB i inne |
| SBI | Sartorius | Entris, Quintix, Cubis, Practum, Secura i inne |
| R Protocol | Radwag | WLY, WPS, AS, PS i inne |
| CBCP-03 | Radwag | WLY, C315, PUE 7.1 i inne |

## Wymagania

- Python 3.10 lub nowszy
- PyQt6 ≥ 6.6.0
- System operacyjny: Windows 10/11, Linux (Ubuntu 22.04+, Fedora 38+ i inne) lub macOS 10.15+ (Intel i Apple Silicon)

## Instalacja i uruchomienie

### Windows

```bash
pip install -r requirements.txt
python main.py
```

### Linux

```bash
pip install -r requirements.txt
python main.py
```

Na Linuksie dostęp do portów szeregowych wymaga członkostwa w grupie `dialout` (lub `uucp` na niektórych dystrybucjach). Jednorazowo:

```bash
sudo usermod -aG dialout $USER
```

Po wykonaniu tej komendy **wyloguj się i zaloguj ponownie**. Porty pojawią się jako `/dev/ttyUSB0`, `/dev/ttyACM0` itp.

### macOS

```bash
pip install -r requirements.txt
python main.py
```

Na macOS adaptery USB-RS-232 wymagają sterownika odpowiedniego dla układu scalonego:

| Układ | Sterownik |
|---|---|
| FTDI FT232 | [ftdichip.com](https://ftdichip.com/drivers/vcp-drivers/) |
| Silicon Labs CP2102 | [silabs.com](https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers) |
| CH340 / CH341 | [github.com/WCHSoftGroup/ch34xser_macos](https://github.com/WCHSoftGroup/ch34xser_macos) |

Po zainstalowaniu sterownika macOS wyświetli prośbę o zatwierdzenie rozszerzenia systemowego w **Ustawienia systemowe → Prywatność i bezpieczeństwo**. Może być wymagane ponowne uruchomienie komputera.

Porty pojawiają się jako `/dev/cu.usbserial-*` (zalecane) lub `/dev/tty.usbserial-*`. W aplikacji wybieraj wariant **`cu.*`**.

## Budowanie pliku wykonywalnego

### Windows (.exe)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --hidden-import=PyQt6.QtSerialPort --add-data "img;img" --name Wazka main.py
```

### Linux (plik binarny)

```bash
pip install pyinstaller
pyinstaller --onefile --hidden-import=PyQt6.QtSerialPort --add-data "img:img" --name Wazka main.py
```

### macOS (.app)

```bash
pip install pyinstaller
pyinstaller --onedir --windowed --hidden-import=PyQt6.QtSerialPort --add-data "img:img" --name Wazka main.py
```

Na macOS PyInstaller tworzy bundle `dist/Wazka.app`. Budowanie należy wykonać **na docelowej architekturze** — plik skompilowany na Macu Intel nie uruchomi się natywnie na Apple Silicon i odwrotnie.

> `--add-data` dołącza katalog `img/` z logo do pliku wykonywalnego. Na Windows separatorem jest `;`, na Linuksie i macOS — `:`.

Plik wykonywalny zostanie wygenerowany w katalogu `dist/`.

## Użytkowanie

1. Uruchom aplikację.
2. Otwórz **Waga → Opcje aplikacji...** (`Ctrl+,`), aby wybrać motyw wyglądu.
3. Otwórz **Waga → Ustawienia połączenia** (lub `Ctrl+U`).
4. Wybierz protokół, port COM, baud rate oraz parametry portu.
5. Kliknij **Połącz** — lub skorzystaj z przycisku **⚡ Profile ▾** w pasku połączenia,  
   jeśli masz już zapisany profil wagi.
6. Użyj przycisków do sterowania wagą:
   - **Odczyt wagi** — żądanie odczytu stabilnego
   - **Odczyt natychmiastowy** — odczyt bez oczekiwania na stabilizację
   - **Odczyt ciągły** — automatyczny odczyt co 1 sekundę (wciśnij ponownie, aby zatrzymać)
   - **TARA** — wyzerowanie z obciążeniem (resetuje statystyki sesji)
   - **ZERO** — zerowanie bez obciążenia (resetuje statystyki sesji)
7. Wartości **Min** i **Max** widoczne pod wyświetlaczem pokazują zakres pomiarów od ostatniej tary lub zerowania.

### Zarządzanie profilami wag

- W oknie ustawień połączenia wybierz parametry, a następnie kliknij **Zapisz profil…**
- Wpisz nazwę profilu (np. „Waga laboratoryjna") i zatwierdź.
- Aby szybko połączyć się z zapisaną wagą: kliknij **⚡ Profile ▾** w pasku połączenia i wybierz profil z listy.

## Testy

Projekt zawiera zestaw testów jednostkowych uruchamianych przez `pytest`.

```bash
python -m pytest tests/ -v
```

Testy nie wymagają podłączonej wagi — sprawdzają parsery protokołów i logikę serwisów na podstawie przykładowych ramek RS-232.

| Plik | Zakres |
|---|---|
| `tests/test_models.py` | `WeightStatus`, `WeightReading`, `ScalePreset` |
| `tests/test_protocol_mettler.py` | Parser Mettler Toledo MT-SICS |
| `tests/test_protocol_sartorius.py` | Parser Sartorius SBI |
| `tests/test_protocol_radwag.py` | Parser Radwag R Protocol |
| `tests/test_protocol_cbcp03.py` | Parser Radwag CBCP-03 |
| `tests/test_fallback_parse.py` | Parser awaryjny (`_fallback_parse`) |
| `tests/test_preset_service.py` | `PresetService` — zapis/odczyt profili |

## Struktura projektu

```
metler/
├── main.py                        # punkt wejścia aplikacji
├── requirements.txt
├── presets.json                   # zapisane profile wag (tworzony automatycznie)
├── app_settings.json              # ustawienia aplikacji: motyw (tworzony automatycznie)
├── models/
│   ├── weight_reading.py          # model danych odczytu
│   └── scale_preset.py            # model profilu wagi
├── protocols/
│   ├── scale_protocol.py          # klasa abstrakcyjna protokołu
│   ├── mettler_sics_protocol.py   # Mettler Toledo MT-SICS
│   ├── sartorius_sbi_protocol.py  # Sartorius SBI
│   ├── radwag_protocol.py         # Radwag R Protocol
│   └── radwag_cbcp03_protocol.py  # Radwag CBCP-03
├── services/
│   ├── scale_service.py           # obsługa RS-232 i logika komunikacji
│   ├── preset_service.py          # zapis i odczyt profili wag (JSON)
│   └── app_settings_service.py    # zapis i odczyt ustawień aplikacji (JSON)
├── ui/
│   ├── theme.py                   # ThemeColors, ThemeManager, motywy DARK i LIGHT
│   ├── main_window.py             # główne okno
│   ├── weight_display.py          # wyświetlacz wartości wagi + statystyki sesji
│   ├── connection_panel.py        # panel konfiguracji połączenia + profile
│   ├── settings_dialog.py         # okno ustawień połączenia
│   ├── app_settings_dialog.py     # okno opcji aplikacji (wybór motywu)
│   ├── terminal_dialog.py         # terminal komend RS-232
│   └── about_dialog.py            # okno "O programie"
├── img/                           # zasoby graficzne (logo aplikacji)
└── docs/                          # materiały pomocnicze (instrukcje, specyfikacje)
```

## Autor

Krystian Rutkowski  
Licencja: MIT
