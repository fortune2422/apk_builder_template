package com.go606.br33;

import android.app.Application;

import com.adjust.sdk.Adjust;
import com.adjust.sdk.AdjustConfig;

public class MyApp extends Application {

    @Override
    public void onCreate() {
        super.onCreate();

        // Adjust 应用识别码（App Token）
        String appToken = "2nw863gtc4xs";

        // 测试环境（正式上线前必须改成 ENVIRONMENT_PRODUCTION）
        String environment = AdjustConfig.ENVIRONMENT_PRODUCTION;

        AdjustConfig config = new AdjustConfig(this, appToken, environment);

        // 启动 Adjust SDK
        Adjust.onCreate(config);
    }
}
