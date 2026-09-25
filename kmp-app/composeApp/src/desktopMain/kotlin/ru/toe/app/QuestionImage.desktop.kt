package ru.toe.app

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Box
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.toComposeImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.style.TextAlign
import org.jetbrains.skia.Image as SkiaImage

@Composable
actual fun QuestionImage(resourcePath: String, modifier: Modifier) {
    val bitmap = remember(resourcePath) {
        Thread.currentThread().contextClassLoader.getResourceAsStream(resourcePath)?.use { stream ->
            SkiaImage.makeFromEncoded(stream.readBytes()).toComposeImageBitmap()
        }
    }

    if (bitmap == null) {
        Box(modifier = modifier, contentAlignment = Alignment.Center) {
            Text("Изображение не найдено", textAlign = TextAlign.Center)
        }
    } else {
        Image(
            bitmap = bitmap,
            contentDescription = null,
            modifier = modifier,
            contentScale = ContentScale.Fit,
        )
    }
}
