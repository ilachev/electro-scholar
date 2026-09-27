package io.github.ilachev.electroscholar.feature.questionbank.data

import app.cash.sqldelight.driver.native.NativeSqliteDriver
import co.touchlab.sqliter.DatabaseFileContext
import kotlinx.cinterop.ExperimentalForeignApi
import kotlinx.cinterop.addressOf
import kotlinx.cinterop.convert
import kotlinx.cinterop.usePinned
import platform.posix.fclose
import platform.posix.fopen
import platform.posix.fwrite

@OptIn(ExperimentalForeignApi::class)
private fun writeDatabaseFile(path: String, bytes: ByteArray) {
    val file = checkNotNull(fopen(path, "wb")) {
        "Unable to open the packaged question database destination"
    }
    try {
        val written = bytes.usePinned {
            fwrite(it.addressOf(0), 1.convert(), bytes.size.convert(), file)
        }
        check(written == bytes.size.toULong()) {
            "Unable to install the complete packaged question database"
        }
    } finally {
        fclose(file)
    }
}

@OptIn(ExperimentalForeignApi::class)
internal actual suspend fun createDatabase(): QuestionBankDatabase {
    val databasePath = DatabaseFileContext.databasePath(DATABASE_NAME, null)
    val bytes = packagedDatabaseBytes()
    writeDatabaseFile(databasePath, bytes)

    val driver = NativeSqliteDriver(QuestionBankDatabase.Schema, DATABASE_NAME)
    return QuestionBankDatabase(driver)
}
