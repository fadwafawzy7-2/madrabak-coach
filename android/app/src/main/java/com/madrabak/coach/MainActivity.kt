package com.madrabak.coach

import android.app.Application
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
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

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            CoachTheme {
                AppRoot()
            }
        }
    }
}
