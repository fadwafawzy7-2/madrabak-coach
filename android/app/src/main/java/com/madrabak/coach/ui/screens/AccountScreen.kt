package com.madrabak.coach.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.core.os.LocaleListCompat
import androidx.appcompat.app.AppCompatDelegate
import com.madrabak.coach.R
import com.madrabak.coach.data.api.Profile
import com.madrabak.coach.data.api.ProfileUpdate
import com.madrabak.coach.data.api.SubscriptionStatus
import com.madrabak.coach.data.repo.ApiProvider
import com.madrabak.coach.data.repo.safeCall
import kotlinx.coroutines.launch

@Composable
fun AccountScreen(onLoggedOut: () -> Unit, onEditProfile: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var profile by remember { mutableStateOf<Profile?>(null) }
    var subscription by remember { mutableStateOf<SubscriptionStatus?>(null) }
    var confirmDialog by remember { mutableStateOf<String?>(null) } // "account" | "data"

    LaunchedEffect(Unit) {
        val api = ApiProvider.init(context)
        safeCall { api.getProfile() }.onSuccess { profile = it }
        safeCall { api.subscription() }.onSuccess { subscription = it }
    }

    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Text(stringResource(R.string.account_title), style = MaterialTheme.typography.headlineMedium)

        // subscription card
        subscription?.let { sub ->
            Card {
                Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(stringResource(R.string.subscription), style = MaterialTheme.typography.titleLarge)
                    Text(
                        when (sub.status) {
                            "trial" -> stringResource(R.string.subscription_trial, sub.trialEndsAt.take(10))
                            "active" -> stringResource(R.string.subscription_active)
                            else -> stringResource(R.string.subscription_expired)
                        },
                        color = if (sub.hasAccess) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,
                    )
                    Text(stringResource(R.string.subscription_price), style = MaterialTheme.typography.bodyMedium)
                }
            }
        }

        OutlinedButton(onClick = onEditProfile, modifier = Modifier.fillMaxWidth()) {
            Text(stringResource(R.string.edit_profile))
        }

        // language selector — updates app locale AND backend profile (AI replies follow it)
        Card {
            Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(stringResource(R.string.language), style = MaterialTheme.typography.titleLarge)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf("ar" to "العربية", "en" to "English", "he" to "עברית").forEach { (code, label) ->
                        FilterChip(
                            selected = profile?.language == code,
                            onClick = {
                                scope.launch {
                                    safeCall { ApiProvider.init(context).updateProfile(ProfileUpdate(language = code)) }
                                        .onSuccess { profile = it }
                                    ApiProvider.sessionStore(context).setLanguage(code)
                                    AppCompatDelegate.setApplicationLocales(
                                        LocaleListCompat.forLanguageTags(if (code == "he") "iw" else code)
                                    )
                                }
                            },
                            label = { Text(label) },
                        )
                    }
                }
            }
        }

        // notifications toggle
        Card {
            Row(Modifier.fillMaxWidth().padding(16.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(stringResource(R.string.notifications), style = MaterialTheme.typography.bodyLarge)
                Switch(
                    checked = profile?.notificationsEnabled ?: true,
                    onCheckedChange = { enabled ->
                        scope.launch {
                            safeCall {
                                ApiProvider.init(context).updateProfile(ProfileUpdate(notificationsEnabled = enabled))
                            }.onSuccess { profile = it }
                        }
                    },
                )
            }
        }

        Spacer(Modifier.height(12.dp))

        OutlinedButton(onClick = {
            scope.launch {
                ApiProvider.sessionStore(context).setToken(null)
                onLoggedOut()
            }
        }, modifier = Modifier.fillMaxWidth()) { Text(stringResource(R.string.logout)) }

        TextButton(onClick = { confirmDialog = "data" }, modifier = Modifier.fillMaxWidth()) {
            Text(stringResource(R.string.delete_data), color = MaterialTheme.colorScheme.error)
        }
        TextButton(onClick = { confirmDialog = "account" }, modifier = Modifier.fillMaxWidth()) {
            Text(stringResource(R.string.delete_account), color = MaterialTheme.colorScheme.error)
        }
    }

    confirmDialog?.let { which ->
        AlertDialog(
            onDismissRequest = { confirmDialog = null },
            title = { Text(stringResource(if (which == "account") R.string.delete_account else R.string.delete_data)) },
            text = { Text(stringResource(R.string.delete_confirm)) },
            confirmButton = {
                TextButton(onClick = {
                    scope.launch {
                        val api = ApiProvider.init(context)
                        if (which == "account") {
                            safeCall { api.deleteAccount() }
                            ApiProvider.sessionStore(context).setToken(null)
                            confirmDialog = null
                            onLoggedOut()
                        } else {
                            safeCall { api.deleteData() }
                            confirmDialog = null
                        }
                    }
                }) { Text(stringResource(R.string.confirm)) }
            },
            dismissButton = {
                TextButton(onClick = { confirmDialog = null }) { Text(stringResource(R.string.cancel)) }
            },
        )
    }
}
