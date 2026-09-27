package io.github.ilachev.electroscholar.app

import android.content.Context
import io.github.ilachev.electroscholar.feature.questionbank.data.initializeQuestionBankAndroid

fun initializeAndroidApp(context: Context) {
    initializeQuestionBankAndroid(context)
}
