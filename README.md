# My Wardrobe

Локальное приложение для личного каталога одежды. Проект разделяет код и данные: фотографии, таблицы с вещами, manifest и SQLite остаются локальными и не должны попадать в публичный Git-репозиторий.

## Текущее состояние

- Этап 1: загрузчик оригинальных фото, manifest, 139 локальных изображений.
- Этапы 2–4: SQLite, импорт таблиц, REST API, интерфейс каталога, ручной конструктор образов, фото-менеджер, ZIP/CSV/JSON export и ZIP import.
- Публикация frontend/API и перенос фото/БД в облако пока не выполнены.

## Локальный запуск backend

Требуется Python 3.12 или новее, Node.js и pnpm.

Первичная установка:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd frontend
pnpm install
cd ..
```

Запуск и остановка:

```powershell
.\start.ps1
.\stop.ps1
```

Откройте `http://127.0.0.1:8000/docs` для REST/OpenAPI документации. База данных создаётся в `data/wardrobe.db`.

Каталог читается из `data/catalog.csv`, визуальные описания — из `data/visual_descriptions.csv`. При повторном импорте записи обновляются по постоянному ID, а пользовательские заметки приложения сохраняются отдельно. Перед обновлением существующей SQLite базы создаётся резервная копия.

## Данные и приватность

В публичный GitHub-репозиторий входят только код и безопасные примеры конфигурации. Настоящие CSV, HTML-каталог, локальные фотографии, manifest, SQLite и секреты исключены через `.gitignore`. После клонирования приватные таблицы и изображения нужно получить отдельно и поместить в `data/`.

Для локального использования API работает без токена. На хостинге задайте `WARDROBE_REQUIRE_AUTH=true` и сохраните длинный случайный `WARDROBE_API_TOKEN` в настройках секретов провайдера. Не помещайте ключ в frontend, публичный код или GitHub Actions logs.

## Загрузчик фотографий

```powershell
python backend\scripts\download_images.py --limit 5
python backend\scripts\download_images.py
```

Повторный запуск проверяет существующие файлы и пропускает корректные. `--force` принудительно загружает заново; `--limit N` ограничивает тестовую загрузку.

## Тесты

```powershell
$env:PYTHONPATH = "backend"
py -m unittest discover -s backend/tests -v
```
