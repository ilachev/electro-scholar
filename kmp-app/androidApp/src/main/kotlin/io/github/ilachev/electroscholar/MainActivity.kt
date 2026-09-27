package io.github.ilachev.electroscholar

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import io.github.ilachev.electroscholar.app.App
import io.github.ilachev.electroscholar.app.initializeAndroidApp

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        initializeAndroidApp(applicationContext)
        enableEdgeToEdge()
        setContent { App() }
    }
}
