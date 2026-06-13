// アプリ内で技術書(techbook.html)を読むビュー。完全オフライン(WebView でバンドル HTML を表示)。
// HTML は dev/build_techbook.py が生成し ios/Resources/techbook.html に同梱(Mermaid 図も内蔵)。
import SwiftUI
import WebKit

struct TechBookView: View {
    var body: some View {
        TechBookWeb()
            .ignoresSafeArea(edges: .bottom)
            .navigationTitle("技術書")
            .navigationBarTitleDisplayMode(.inline)
    }
}

private struct TechBookWeb: UIViewRepresentable {
    func makeUIView(context: Context) -> WKWebView {
        let web = WKWebView()
        web.isOpaque = false
        if let url = Bundle.main.url(forResource: "techbook", withExtension: "html") {
            web.loadFileURL(url, allowingReadAccessTo: url.deletingLastPathComponent())
        } else {
            web.loadHTMLString("<h2>技術書が見つかりません</h2>", baseURL: nil)
        }
        return web
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {}
}
