# Кай (Kai)

Компаньон для продуктивности и выработки привычек: задачи с шагами, репетиции
(мысленная прогонка задачи перед работой), геймификация (XP, уровни, бои с
«врагами прокрастинации»), мониторинг активных окон с реакциями на отвлечения,
пуш-уведомления и голосовой движок с цепочкой фолбэков **Gemini → edge-tts →
системный голос (pyttsx3)**.

## Установка

```bash
pip install -r requirements.txt
```

или как пакет (даёт команду `kai`):

```bash
pip install -e .
```

## Запуск

```bash
python run.py        # без установки
python -m kai        # после pip install -e .
kai                  # после pip install -e .
```

## Данные и ключи

Все пользовательские данные лежат в `%APPDATA%\pixel\` (Roaming):

| Файл/папка      | Что хранит                                        |
|-----------------|---------------------------------------------------|
| `data.json`     | проекты и задачи                                  |
| `progress.json` | XP, уровень, достижения, бои, ивенты              |
| `phrases.json`  | пользовательские фразы Кая                        |
| `voice.json`    | настройки голоса: движок, ключ Gemini, тембр и пр. |
| `monitor.json`  | настройки мониторинга                             |
| `sprites\`      | спрайты аватара по эмоциям (neutral.png и т.д.)   |
| `crash.log`     | лог сбоев                                         |

API-ключ Gemini вводится во вкладке «⚙ Настройки → Голос и движок озвучки»
(хранится в `voice.json`). Без ключа работает edge-tts (нужен интернет) или
системный голос офлайн.

## Структура

```
src/kai/
├── constants.py, text_utils.py, sys_utils.py   # константы и утилиты
├── core/    # storage, gamification, phrases, monitor, avatar, companion
├── voice/   # styles, engine (очередь/кэш/фолбэки), провайдеры gemini/edge/system
└── ui/      # theme, widgets, dialogs, nav, status_bar, main_window, pages/
```

Направление зависимостей: `ui → core/voice → constants/utils`.
Общие сервисы создаются один раз в `MainWindow` (composition root).

## Тесты

```bash
python -m pytest tests/
```
