# Enveloppe iOS

Cible : iOS 15 et superieur, SwiftUI.

```swift
import SwiftUI
import WebKit

struct MercuryApp: View {
    let apiURL = URL(string: "https://api.mercury.local")!
    var body: some View {
        WebView(url: apiURL.appendingPathComponent("app"))
            .edgesIgnoringSafeArea(.all)
    }
}
```

Fonctions natives a brancher : appareil photo (releves chantier), ARKit
(livrable #48), notifications d'alerte du jumeau numerique, stockage
chiffre du cache hors ligne.
