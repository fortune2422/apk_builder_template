package com.go606.br33;

import android.content.Context;
import android.content.Intent;
import android.content.res.Configuration;
import android.net.Uri;
import android.os.Bundle;
import android.os.Message;
import android.util.DisplayMetrics;
import android.webkit.*;
import androidx.appcompat.app.AppCompatActivity;
import com.adjust.sdk.Adjust;

public class MainActivity extends AppCompatActivity {

    @Override
    protected void onResume() {
        super.onResume();
        Adjust.onResume();
    }

    @Override
    protected void onPause() {
        super.onPause();
        Adjust.onPause();
    }

    // 固定字体
    @Override
    public void applyOverrideConfiguration(Configuration overrideConfiguration) {
        if (overrideConfiguration != null) {
            overrideConfiguration.fontScale = 1.0f;
        }
        super.applyOverrideConfiguration(overrideConfiguration);
    }

    // 固定显示密度
    @Override
    protected void attachBaseContext(Context newBase) {
        Configuration config = newBase.getResources().getConfiguration();
        config.fontScale = 1.0f;
        config.densityDpi = DisplayMetrics.DENSITY_DEVICE_STABLE;
        Context context = newBase.createConfigurationContext(config);
        super.attachBaseContext(context);
    }

    @Override
    protected void onCreate(Bundle b){
        super.onCreate(b);
        setContentView(R.layout.activity_main);

        final WebView w = findViewById(R.id.webview);

        WebSettings s = w.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setJavaScriptCanOpenWindowsAutomatically(true);
        s.setSupportMultipleWindows(true);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        s.setTextZoom(100);

        JsInterface jsInterface = new JsInterface(this);
        w.addJavascriptInterface(jsInterface, "jsBridge");


        // WebViewClient：内部链接在 WebView 打开，外链使用外部 Intent
        w.setWebViewClient(new WebViewClient() {
            // API 21+
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                String url = request.getUrl().toString();
                return handleUrl(view, url);
            }

            // 兼容旧版
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String urlRaw) {
                if (urlRaw == null) return false;
                return handleUrl(view, urlRaw);
            }

            private boolean handleUrl(WebView view, String urlRaw) {
                if (urlRaw == null) return false;
                String url = urlRaw.trim();

                // 如果是你的 H5 域名 -> 在 WebView 内打开
                if (url.contains("3go606.com") || url.contains("go606.com") || url.contains("1go606.com")) {
                    // 允许 WebView 继续加载（内链）
                    return false;
                }

                // 非内链：交给外部处理（APP scheme 优先，浏览器降级）
                openExternal(url);
                return true;
            }
        });

        // WebChromeClient：处理 target="_blank" / window.open()
        w.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onCreateWindow(WebView view, boolean isDialog,
                                          boolean isUserGesture, Message resultMsg) {

                // HitTestResult 有时返回图片（img src），但真实打开的 URL 往往会由新 WebView 的请求流经 shouldOverrideUrlLoading。
                // 因此要给 newWebView 完整的 settings + client，确保能捕获目标 URL。
                WebView newWebView = new WebView(MainActivity.this);

                // 必要的设置（与主 WebView 一致）
                WebSettings ns = newWebView.getSettings();
                ns.setJavaScriptEnabled(true);
                ns.setDomStorageEnabled(true);
                ns.setJavaScriptCanOpenWindowsAutomatically(true);
                ns.setSupportMultipleWindows(true);
                ns.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);

                // 拦截 newWebView 的导航：如果是内链，载回主 WebView；否则走外部打开
                newWebView.setWebViewClient(new WebViewClient() {
                    @Override
                    public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                        String url = request.getUrl().toString();
                        return handleNewWebViewUrl(url);
                    }

                    @Override
                    public boolean shouldOverrideUrlLoading(WebView view, String url) {
                        return handleNewWebViewUrl(url);
                    }

                    private boolean handleNewWebViewUrl(String url) {
                        if (url == null) return false;
                        // 如果是图片资源（png/jpg），不要直接在浏览器打开图片（这就是你之前看到 png 的原因）
                        // 优先尝试寻找是否为外链社媒链接 —— newWebView 通常会接到真实外链；若是图片，尝试从 parent 打开外部（避免打开图片本身）
                        if (url.matches(".*\\.(png|jpg|jpeg)(\\?.*)?$")) {
                            // 如果是图片资源，直接尝试打开外部（因为通常它不是最终目标）
                            // 也可以选择在主 WebView 内显示，但更常见的是把外链交浏览器或 APP 处理
                            openExternal(url);
                            return true;
                        }

                        // 如果是你的域名：在主 WebView 内打开
                        if (url.contains("3go606.com") || url.contains("go606.com") || url.contains("1go606.com")) {
                            // 把主 WebView 导向该 URL（在主 WebView 内打开）
                            runOnUiThread(() -> w.loadUrl(url));
                            return true;
                        }

                        // 其他域名：外部打开
                        openExternal(url);
                        return true;
                    }
                });

                // 重要：为 newWebView 设置 WebChromeClient，支持再次创建 window.open 链
                newWebView.setWebChromeClient(new WebChromeClient());

                // 将 newWebView 交给 transport（这是 window.open 的标准流程）
                WebView.WebViewTransport transport = (WebView.WebViewTransport) resultMsg.obj;
                transport.setWebView(newWebView);
                resultMsg.sendToTarget();
                return true;
            }
        });

        // 最后加载 H5
        w.loadUrl("https://4go606.com?ch=zdcal&sdmode=3");
    }


    // 外部跳转（APP 优先）
    private void openExternal(String url) {

        if (url == null || url.isEmpty()) return;

        // APP 优先：将网页链接转成对应 APP Scheme
        String appUrl = buildAppLink(url);

        // try app scheme first
        try {
            Intent appIntent = new Intent(Intent.ACTION_VIEW, Uri.parse(appUrl));
            appIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(appIntent);
            return;
        } catch (Exception ignored) {}

        // fallback to browser
        try {
            Intent webIntent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
            webIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(webIntent);
        } catch (Exception ignored) {}
    }

    // 转换 APP Scheme（尽量打开原生 App）
    private String buildAppLink(String url) {

        if (url == null) return url;

        // Telegram
        if (url.contains("t.me/")) {
            String user = url.substring(url.lastIndexOf("/") + 1);
            return "tg://resolve?domain=" + user;
        }

        // Facebook
        if (url.contains("facebook.com/")) {
            // fb scheme 会打开 facebook app 页面（如果安装）
            return "fb://facewebmodal/f?href=" + url;
        }

        // Instagram
        if (url.contains("instagram.com/")) {
            String user = url.substring(url.indexOf(".com/") + 5).split("[/?]")[0];
            return "instagram://user?username=" + user;
        }

        // WhatsApp Channel（无稳定 scheme 可用）
        if (url.contains("whatsapp.com/channel/")) {
            return url;
        }

        // X / Twitter
        if (url.contains("x.com/") || url.contains("twitter.com/")) {
            String user = url.substring(url.lastIndexOf("/") + 1).split("\\?")[0];
            return "twitter://user?screen_name=" + user;
        }

        return url;
    }
}
