# ElectroScholar KMP application

The first runnable ElectroScholar client is built with Kotlin Multiplatform and
Compose Multiplatform. Shared models, SQL queries, and UI live in `commonMain`;
the current desktop implementation lives in `desktopMain`.

## Requirements

- JDK 21 LTS.
- All other build dependencies are resolved by the pinned Gradle Wrapper.

## Run

```bash
./gradlew :composeApp:run
```

## Test

```bash
./gradlew :composeApp:desktopTest
```

The application ships with a read-only snapshot of the recovered question
bank. It is copied to `~/.electroscholar/question-bank.sqlite` on startup.
Future user progress and preferences must use a separate migrated database.

## Refresh the question bank

```bash
cd ..
python3 tools/inspect_legacy_db.py test --export-database analysis/database
cd kmp-app
./gradlew :composeApp:syncQuestionBank
```

## Package for macOS

```bash
./gradlew :composeApp:createDistributable
./gradlew :composeApp:packageDmg
```

The application bundle is created at
`composeApp/build/compose/binaries/main/app/ElectroScholar.app`.
