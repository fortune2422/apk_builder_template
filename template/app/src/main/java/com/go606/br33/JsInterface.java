package com.go606.br33;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.util.Log;
import android.webkit.JavascriptInterface;

import com.adjust.sdk.Adjust;
import com.adjust.sdk.AdjustEvent;

import org.json.JSONObject;

public class JsInterface {
    Activity activity;
    private static final String TAG = "JsBridge";

    // ====== 你的 Adjust 事件 Token ======
    private static final String TOKEN_LOGIN               = "p9dh8r";
    private static final String TOKEN_LOGOUT              = "bp18i2";
    private static final String TOKEN_REGISTER_CLICK      = "wtjysl";
    private static final String TOKEN_REGISTER            = "he7g8i";
    private static final String TOKEN_RECHARGE_CLICK      = "mf0wxn";
    private static final String TOKEN_RECHARGE            = "47qwd6";
    private static final String TOKEN_FIRST_RECHARGE      = "yvgfgt";
    private static final String TOKEN_ENTER_GAME          = "z0p9lo";

    public JsInterface(Activity activity){
        this.activity = activity;
    }


    // =========================================================
    //  WG 平台 API:  postMessage(name, data)
    // =========================================================
    @JavascriptInterface
    public void postMessage(String name, String data){
        Log.d(TAG, "[WG] postMessage -> name=" + name + "  data=" + data);
        handleEvent(name, data);
    }


    // =========================================================
    //  天成平台 API:  eventTracker(event, params)
    // =========================================================
    @JavascriptInterface
    public void eventTracker(String eventType, String eventValues){
        Log.d(TAG, "[TC] eventTracker -> type=" + eventType + "  data=" + eventValues);
        handleEvent(eventType, eventValues);
    }


    // =========================================================
    //  统一事件处理中心（WG + TC 都用它）
    // =========================================================
    private void handleEvent(String name, String data){
        try {
            JSONObject json = (data == null || data.isEmpty())
                    ? new JSONObject()
                    : new JSONObject(data);

            switch (name) {

                case "login":
                    sendEvent(TOKEN_LOGIN, json);
                    break;

                case "logout":
                    sendEvent(TOKEN_LOGOUT, json);
                    break;

                case "registerClick":
                    sendEvent(TOKEN_REGISTER_CLICK, json);
                    break;

                case "register":
                    sendEvent(TOKEN_REGISTER, json);
                    break;

                case "rechargeClick":
                    sendEvent(TOKEN_RECHARGE_CLICK, json);
                    break;

                case "recharge":
                    sendRevenueEvent(TOKEN_RECHARGE, json);
                    break;

                case "firstrecharge":
                case "firstDepositArrival":
                    sendRevenueEvent(TOKEN_FIRST_RECHARGE, json);
                    break;

                case "enterGame":
                    sendEvent(TOKEN_ENTER_GAME, json);
                    break;

                case "openWindow":
                    openExternal(json.optString("url"));
                    break;
            }

        } catch (Exception e){
            e.printStackTrace();
        }
    }


    // =========================================================
    //  普通 Adjust 事件（无金额）
    // =========================================================
    private void sendEvent(String token, JSONObject json) {
        AdjustEvent event = new AdjustEvent(token);

        if (json.has("uid"))
            event.addCallbackParameter("uid", json.optString("uid"));

        if (json.has("cid"))
            event.addCallbackParameter("cid", json.optString("cid"));

        Adjust.trackEvent(event);
    }


    // =========================================================
    //  金额 Adjust 事件（充值）
    // =========================================================
    private void sendRevenueEvent(String token, JSONObject json) {
        double amount = json.optDouble("amount", 0);
        String currency = json.optString("currency", "USD");

        AdjustEvent event = new AdjustEvent(token);

        if (amount > 0)
            event.setRevenue(amount, currency);

        if (json.has("uid"))
            event.addCallbackParameter("uid", json.optString("uid"));

        if (json.has("cid"))
            event.addCallbackParameter("cid", json.optString("cid"));

        Adjust.trackEvent(event);
    }


    // =========================================================
    //  openWindow(): 打开外部浏览器
    // =========================================================
    private void openExternal(String url){
        if (url == null || url.isEmpty()) return;

        try {
            Intent i = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
            i.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            activity.startActivity(i);
        } catch (Exception ignore){}
    }
}
