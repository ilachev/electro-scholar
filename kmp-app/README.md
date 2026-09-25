# ТОЭ KMP

Первый рабочий инкремент новой версии программы «ТЕСТ» на Kotlin Multiplatform
и Compose Multiplatform. Общая логика и SQL-запросы находятся в `commonMain`,
desktop-реализация для macOS — в `desktopMain`.

## Требования

- JDK 21 LTS.
- Остальные инструменты скачивает зафиксированный Gradle Wrapper.

## Запуск

```bash
./gradlew :composeApp:run
```

## Проверка

```bash
./gradlew :composeApp:desktopTest
```

Приложение использует встроенный снимок восстановленной SQLite-базы. При запуске
read-only банк вопросов обновляется в `~/.toe-reborn/toe.sqlite`; пользовательские
данные в дальнейшем будут храниться отдельно.

## Обновление банка вопросов

```bash
cd ..
python3 tools/inspect_legacy_db.py test --export-database analysis/database
cd kmp-app
./gradlew :composeApp:syncQuestionBank
```

Готовый macOS `.app` создаётся командой:

```bash
./gradlew :composeApp:createDistributable
```

Результат: `composeApp/build/compose/binaries/main/app/TOE.app`.
