# Enveloppe Android

Cible : Android 9 (API 28) et superieur, Kotlin.

```kotlin
class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val webView = WebView(this)
        webView.settings.javaScriptEnabled = true
        webView.loadUrl("https://api.mercury.local/app")
        setContentView(webView)
    }
}
```

Fonctions natives a brancher : CameraX, ARCore (livrable #48), WorkManager
pour la file hors ligne, chiffrement EncryptedSharedPreferences.
