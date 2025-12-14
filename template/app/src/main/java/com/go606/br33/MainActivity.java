package com.pt717.apk13;

import android.content.Context;
import android.content.Intent;
import android.content.res.Configuration;
import android.net.Uri;
import android.os.Bundle;
import android.os.Message;
import android.webkit.*;

import androidx.appcompat.app.AppCompatActivity;

import com.adjust.sdk.Adjust;

public class MainActivity extends AppCompatActivity {

    private WebView webView;

    private static final String HOME_URL =
            "https://2jjbet.com/?ch=38064&sd=6";

    // ================= 生命周期 =================

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // 系统回收兜底（防 WebView 白屏）
        if (savedInstanceState != null) {
            recreate();
            return;
        }

        setContentView(R.layout.activity_main);
        webView = findViewById(R.id.webview);

        initWebView();
        webView.loadUrl(HOME_URL);
    }

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

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.destroy();
            webView = null;
        }
        super.onDestroy();
    }

    // ================= 返回键 =================

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            moveTaskToBack(true);
        }
    }

    // ================= 字体配置 =================

    @Override
    public void applyOverrideConfiguration(Configuration overrideConfiguration) {
        if (overrideConfiguration != null) {
            overrideConfiguration.fontScale = 1.0f;
        }
        super.applyOverrideConfiguration(overrideConfiguration);
    }

    @Override
    protected void attachBaseContext(Context newBase) {
        Configuration config = newBase.getResources().getConfiguration();
        config.fontScale = 1.0f;
        super.attachBaseContext(
                newBase.createConfigurationContext(config)
        );
    }

    // ================= WebView 初始化 =================

    private void initWebView() {

        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setJavaScriptCanOpenWindowsAutomatically(true);
        s.setSupportMultipleWindows(true);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        s.setTextZoom(100);

        // 永远加载最新 H5
        s.setCacheMode(WebSettings.LOAD_NO_CACHE);

        webView.addJavascriptInterface(
                new JsInterface(this), "jsBridge"
        );

        // ===== 下载监听（关键）=====
        webView.setDownloadListener(
                (url, userAgent, contentDisposition, mimeType, contentLength) -> {
                    try {
                        Intent i = new Intent(Intent.ACTION_VIEW);
                        i.setData(Uri.parse(url));
                        startActivity(i);
                    } catch (Exception ignored) {}
                }
        );

        // ===== WebViewClient =====
        webView.setWebViewClient(new WebViewClient() {

            @Override
            public boolean shouldOverrideUrlLoading(
                    WebView view, WebResourceRequest request) {
                return handleUrl(request.getUrl().toString());
            }

            @Override
            public boolean shouldOverrideUrlLoading(
                    WebView view, String url) {
                return handleUrl(url);
            }

            private boolean handleUrl(String url) {
                if (url == null) return false;

                // ★ 下载文件（APK 等）强制外部
                if (isDownloadFile(url)) {
                    openExternal(url);
                    return true;
                }

                // 内链网页
                if (isInnerDomain(url)) {
                    return false;
                }

                // 其他外链
                openExternal(url);
                return true;
            }
        });

        // ===== WebChromeClient =====
        webView.setWebChromeClient(new WebChromeClient() {

            @Override
            public boolean onCreateWindow(WebView view,
                                          boolean isDialog,
                                          boolean isUserGesture,
                                          Message resultMsg) {

                WebView newWebView = new WebView(MainActivity.this);
                WebSettings ns = newWebView.getSettings();

                ns.setJavaScriptEnabled(true);
                ns.setDomStorageEnabled(true);
                ns.setSupportMultipleWindows(true);
                ns.setJavaScriptCanOpenWindowsAutomatically(true);
                ns.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);

                newWebView.setWebViewClient(new WebViewClient() {

                    @Override
                    public boolean shouldOverrideUrlLoading(
                            WebView v, WebResourceRequest r) {
                        return handleNewUrl(r.getUrl().toString());
                    }

                    @Override
                    public boolean shouldOverrideUrlLoading(
                            WebView v, String url) {
                        return handleNewUrl(url);
                    }

                    private boolean handleNewUrl(String url) {
                        if (url == null) return false;

                        if (isDownloadFile(url)) {
                            openExternal(url);
                            return true;
                        }

                        if (isInnerDomain(url)) {
                            runOnUiThread(() -> webView.loadUrl(url));
                            return true;
                        }

                        openExternal(url);
                        return true;
                    }
                });

                newWebView.setWebChromeClient(new WebChromeClient());

                WebView.WebViewTransport transport =
                        (WebView.WebViewTransport) resultMsg.obj;
                transport.setWebView(newWebView);
                resultMsg.sendToTarget();
                return true;
            }
        });
    }

    // ================= 外链跳转（不回弹） =================

    private void openExternal(String url) {
        if (url == null || url.isEmpty()) return;

        String appUrl = buildAppLink(url);

        try {
            Intent appIntent =
                    new Intent(Intent.ACTION_VIEW, Uri.parse(appUrl));
            appIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);

            if (appIntent.resolveActivity(getPackageManager()) != null) {
                startActivity(appIntent);
                moveTaskToBack(true);
                return;
            }
        } catch (Exception ignored) {}

        try {
            Intent webIntent =
                    new Intent(Intent.ACTION_VIEW, Uri.parse(url));
            webIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(webIntent);
        } catch (Exception ignored) {}
    }

    // ================= 判断方法 =================

    private boolean isInnerDomain(String url) {
        return url.contains("10jjbet.com")
                || url.contains("go606.com")
                || url.contains("1go606.com")
                || url.contains("3go606.com")
                || url.contains("4go606.com");
    }

    private boolean isDownloadFile(String url) {
        String u = url.toLowerCase();
        return u.endsWith(".apk")
                || u.endsWith(".zip")
                || u.endsWith(".rar")
                || u.endsWith(".pdf");
    }

    private String buildAppLink(String url) {

        if (url.contains("t.me/")) {
            String u = url.substring(url.lastIndexOf("/") + 1);
            return "tg://resolve?domain=" + u;
        }

        if (url.contains("facebook.com/")) {
            return "fb://facewebmodal/f?href=" + url;
        }

        if (url.contains("instagram.com/")) {
            String u = url.substring(url.indexOf(".com/") + 5)
                    .split("[/?]")[0];
            return "instagram://user?username=" + u;
        }

        if (url.contains("twitter.com/")
                || url.contains("x.com/")) {
            String u = url.substring(url.lastIndexOf("/") + 1)
                    .split("\\?")[0];
            return "twitter://user?screen_name=" + u;
        }

        return url;
    }
}
