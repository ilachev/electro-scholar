# Архитектура и долговечность

## Цель

Новый продуктовый сценарий должен разрабатываться один раз и работать на
Android, iOS, macOS, Linux и Windows. При этом общий код не ограничивает доступ
к нативным API: зависимость от ОС находится за узким контрактом и реализуется в
соответствующем source set или host-модуле.

## Граф модулей

```text
androidApp ─┐
desktopApp ─┼──> shared (composition root) ──> features:question-bank
iosApp ─────┘                                      ├── commonMain
                                                   ├── androidMain
                                                   ├── iosMain
                                                   └── jvmMain
```

- `androidApp` содержит Android lifecycle, manifest и системную интеграцию.
- `desktopApp` содержит JVM entry point, управление окном и native packaging.
- `iosApp` является обычным SwiftUI/Xcode host и встраивает Compose controller.
- `shared` только собирает приложение из feature-модулей и не владеет данными.
- `features/question-bank` является полным vertical slice: UI, сценарии,
  модели, SQLDelight, ресурсы, платформенные адаптеры и тесты находятся рядом.

Новые области добавляются соседними slices, например `features/formula-review`
и `features/circuit-review`. Slice не импортирует host-модули и не обращается к
другому slice напрямую. Общий стабильный контракт выносится в маленький
`core/*` модуль только после появления реальной потребности.

## Правило vertical slice

Изменение должно проходить вертикально от пользовательского действия до данных
и теста внутри одного feature-модуля. Не создаются глобальные слои `ui`, `data`
или `domain`, в которые постепенно попадает весь проект. Внутренние подпакеты
slice допустимы, но не становятся межмодульным API автоматически.

Публичная поверхность slice минимальна: сейчас это `QuestionBankFeature()` и
Android initializer. Остальные классы должны становиться `internal`, когда это
не мешает генерации SQLDelight и тестам.

## Нативные возможности

Общий сценарий объявляет узкий port только тогда, когда он действительно нужен:
например `ImageSource`, `DocumentExporter` или `ShareService`. Реализации живут
в `androidMain`, `iosMain` и `jvmMain` либо передаются из host-модуля.

Текущий slice уже использует этот подход:

- Android хранит SQLite через `AndroidSqliteDriver` и обрабатывает системный
  Back через Android adapter.
- iOS хранит SQLite в Application Support через native SQLDelight driver и
  запускается из SwiftUI.
- desktop хранит SQLite в пользовательском каталоге через JDBC и получает
  нативные DMG, DEB и MSI пакеты.

Допустимы нативные экраны и views внутри общего приложения. UIKit/SwiftUI,
Android Views/Compose и desktop APIs не переносятся в `commonMain`; общий код
видит только контракт и данные результата.

## Unix philosophy для инструментов

Каждая программа в `tools/` решает одну задачу, запускается без GUI и имеет
явные входы, выходы и коды завершения. Инструменты связываются через
долговечные форматы SQLite, JSON, JSON Schema, TSV и файлы изображений.

```text
legacy files -> inspect_legacy_db.py -> SQLite/JPEG
JPEG -> media/ML worker -> Observation IR
Observation IR -> validator/reviewer -> Circuit IR
Circuit IR -> independent exporters -> SPICE/KiCad/CircuitikZ
```

ML и Python остаются offline workers. End-user приложения не требуют Python и
не знают, каким инструментом был создан валидный IR.

## Данные и версии

Банк вопросов read-only и поставляется как Compose resource. Пользовательские
ответы, настройки и результаты будут храниться отдельно и мигрироваться без
перезаписи исходного корпуса. Экспорт SQLite устанавливает
`PRAGMA user_version = 1`, совпадающий с SQLDelight schema.

Версии Kotlin, Compose, SQLDelight, AGP и Gradle фиксируются. CI отдельно
проверяет чистый common/JVM цикл, Android APK, iOS simulator build и desktop
packages. Ни один platform target не считается поддержанным только потому, что
его имя присутствует в Gradle.

Задача `./gradlew checkArchitecture` делает границы исполняемыми: запрещает
platform imports в `commonMain` и зависимости feature-модулей от host,
`shared` или соседнего slice.

Задача `./gradlew checkVersionConsistency` проверяет SemVer и совпадение версии
Gradle-приложений с iOS host. Release Please обновляет оба файла в одном PR.
