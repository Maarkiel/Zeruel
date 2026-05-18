# Zeruel — M4RK7 Learning Platform

Bot Discord do szkolenia moderatorów — Opiekun tworzy bazę pytań (ABCDE + opisowe), moderatorzy rozwiązują testy i się douczają, ocenianie jest półautomatyczne.

## Funkcje

- **Baza pytań** — Opiekun tworzy pytania ABCDE (zamknięte) + opisowe, kategorie, import/eksport JSON
- **Testy** — moderatorzy robią testy losowe lub z szablonów, mix ABCDE + opisowe, limit czasu
- **Ocenianie półautomatyczne** — ABCDE sprawdzane automatycznie, opisowe ręcznie przez Opiekuna (tryb szybkiej oceny)
- **Nauka / Douczanie** — sesje nauki z feedbackiem, fiszki, powtórka z błędów
- **Statystyki** — profil moderatora, ranking, analiza jakości pytań

## Wymagania

- Python 3.10+
- discord.py 2.3+
- aiosqlite

## Instalacja

```bash
git clone https://github.com/Maarkiel/Zeruel.git
cd Zeruel
pip install -r requirements.txt
cp .env.example .env
# Edytuj .env — wpisz DISCORD_TOKEN
python bot.py
```

## Konfiguracja (.env)

```env
DISCORD_TOKEN=token_bota
OWNER_ID=184021512813019136
DATABASE_PATH=learning.db
LOG_LEVEL=INFO
```

## Komendy

### Zarządzanie pytaniami (Opiekun)
| Komenda | Opis |
|---------|------|
| `/pytanie dodaj-abcde` | Dodaj pytanie ABCDE |
| `/pytanie dodaj-opisowe` | Dodaj pytanie opisowe |
| `/pytanie lista` | Lista pytań |
| `/pytanie podglad <id>` | Podgląd pytania |
| `/pytanie edytuj <id>` | Edytuj pytanie |
| `/pytanie usun <id>` | Usuń pytanie |
| `/pytanie import <plik>` | Import z JSON |
| `/pytanie eksport` | Eksport do JSON |
| `/kategoria dodaj <nazwa>` | Nowa kategoria |
| `/kategoria lista` | Lista kategorii |
| `/kategoria edytuj <id> <nazwa>` | Edytuj kategorię |
| `/kategoria usun <id>` | Usuń kategorię |

### Testy (Moderatorzy)
| Komenda | Opis |
|---------|------|
| `/test start` | Rozpocznij test |
| `/test moje` | Historia testów |
| `/test wynik <id>` | Wynik testu |
| `/test szablon` | Stwórz szablon (Opiekun) |
| `/test szablony` | Lista szablonów (Opiekun) |
| `/test przypisz <szablon> <user>` | Przypisz test (Opiekun) |
| `/test oczekujace` | Oczekujące na ocenę (Opiekun) |

### Ocenianie (Opiekun)
| Komenda | Opis |
|---------|------|
| `/ocena lista` | Odpowiedzi do oceny |
| `/ocena ocen <id>` | Oceń odpowiedź |
| `/ocena szybka` | Szybkie ocenianie kolejki |

### Nauka (Moderator)
| Komenda | Opis |
|---------|------|
| `/nauka start` | Sesja nauki |
| `/nauka fiszki` | Tryb fiszek |
| `/nauka bledy` | Powtórka z błędów |

### Statystyki
| Komenda | Opis |
|---------|------|
| `/statystyki moje` | Moje statystyki |
| `/statystyki moderator <user>` | Statystyki moderatora (Opiekun) |
| `/statystyki ranking` | Ranking |
| `/statystyki pytania` | Jakość pytań (Opiekun) |
| `/statystyki test <id>` | Szczegóły testu (Opiekun) |

### Konfiguracja (Owner)
| Komenda | Opis |
|---------|------|
| `/config kanal-oceny <#kanał>` | Kanał powiadomień o ocenach |
| `/config kanal-wynikow <#kanał>` | Kanał wyników testów |
| `/config rola-opiekun <@rola>` | Rola Opiekuna |
| `/config rola-moderator <@rola>` | Rola Moderatora |
| `/config pokaz` | Aktualna konfiguracja |

## Hierarchia ról

| Rola | Uprawnienia |
|------|-------------|
| **Owner** | Wszystko (OWNER_ID) |
| **Opiekun** | Zarządzanie pytaniami, szablonami, ocenianie, statystyki |
| **Moderator** | Testy, nauka, własne statystyki |

## Struktura projektu

```
Zeruel/
├── bot.py                    # Główny plik bota
├── config.py                 # Konfiguracja z .env
├── database/
│   ├── connection.py         # Async SQLite (aiosqlite)
│   └── models.py             # Operacje na tabelach
├── cogs/
│   ├── questions.py          # Zarządzanie pytaniami (Opiekun)
│   ├── tests.py              # System testów
│   ├── grading.py            # Ocenianie opisowych (Opiekun)
│   ├── study.py              # Tryb nauki
│   ├── stats.py              # Statystyki
│   └── config.py             # Konfiguracja serwera
├── ui/
│   ├── embeds.py             # Embedy Discord
│   ├── views.py              # Przyciski, interakcje
│   └── modals.py             # Formularze modalne
└── utils/
    └── helpers.py            # Uprawnienia, narzędzia
```

## Licencja

MIT
