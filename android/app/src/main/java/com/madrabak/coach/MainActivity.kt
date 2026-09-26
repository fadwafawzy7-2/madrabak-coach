package com.madrabak.coach

import android.app.Application
import android.os.Build
import android.os.Bundle
import android.Manifest
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import com.madrabak.coach.data.repo.ApiProvider
import com.madrabak.coach.ui.AppRoot
import com.madrabak.coach.ui.theme.CoachTheme
import com.madrabak.coach.util.Notifications

class CoachApp : Application() {
    override fun onCreate() {
        super.onCreate()
        ApiProvider.init(this)
        Notifications.createChannels(this)
    }
}

class MainActivity : AppCompatActivity() {
    private val requestNotificationPermission =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { /* no-op either way */ }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Required on Android 13+ (targetSdk 34) — without this the morning-weight
        // and weekly-review reminders are silently never shown.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            requestNotificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
        setContent {
            CoachTheme {
                AppRoot()
            }
        }
    }
}
