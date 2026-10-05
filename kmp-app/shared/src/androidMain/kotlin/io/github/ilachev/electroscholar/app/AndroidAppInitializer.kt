package io.github.ilachev.electroscholar.app

import android.content.Context
import io.github.ilachev.electroscholar.feature.questionbank.data.initializeQuestionBankAndroid
import io.github.ilachev.electroscholar.feature.questionreview.data.initializeQuestionReviewAndroid

fun initializeAndroidApp(context: Context) {
    initializeQuestionBankAndroid(context)
    initializeQuestionReviewAndroid(context)
}
