package com.madrabak.coach.ui.screens

import android.content.Context
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.credentials.CredentialManager
import androidx.credentials.GetCredentialRequest
import androidx.credentials.exceptions.GetCredentialException
import com.google.android.libraries.identity.googleid.GetSignInWithGoogleOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.madrabak.coach.R
import com.madrabak.coach.data.api.ApiService
import com.madrabak.coach.data.api.Credentials
import com.madrabak.coach.data.api.GoogleAuthIn
import com.madrabak.coach.data.repo.ApiProvider
import com.madrabak.coach.data.repo.safeCall
import kotlinx.coroutines.launch

@Composable
fun AuthScreen(onAuthenticated: (needsOnboarding: Boolean) -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var isRegister by remember { mutableStateOf(false) }
    var loading by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf(false) }
    var googleLoading by remember { mutableStateOf(false) }
    var googleError by remember { mutableStateOf(false) }

    suspend fun finishSignIn(api: ApiService, token: String) {
        ApiProvider.sessionStore(context).setToken(token)
        val profile = safeCall { api.getProfile() }.getOrNull()
        onAuthenticated(profile?.onboardingCompleted != true)
    }

    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(stringResource(R.string.app_name), style = MaterialTheme.typography.headlineMedium)
        Spacer(Modifier.height(32.dp))
        OutlinedTextField(
            value = email, onValueChange = { email = it },
            label = { Text(stringResource(R.string.email)) },
            modifier = Modifier.fillMaxWidth(), singleLine = true,
        )
        Spacer(Modifier.height(12.dp))
        OutlinedTextField(
            value = password, onValueChange = { password = it },
            label = { Text(stringResource(R.string.password)) },
            visualTransformation = PasswordVisualTransformation(),
            modifier = Modifier.fillMaxWidth(), singleLine = true,
        )
        if (error) {
            Spacer(Modifier.height(8.dp))
            Text(stringResource(R.string.auth_error), color = MaterialTheme.colorScheme.error)
        }
        Spacer(Modifier.height(20.dp))
        Button(
            onClick = {
                loading = true; error = false
                scope.launch {
                    val api = ApiProvider.init(context)
                    val result = safeCall {
                        if (isRegister) api.register(Credentials(email, password))
                        else api.login(Credentials(email, password))
                    }
                    loading = false
                    result.onSuccess { auth -> finishSignIn(api, auth.token) }
                        .onFailure { error = true }
                }
            },
            enabled = !loading && email.isNotBlank() && password.length >= 8,
            modifier = Modifier.fillMaxWidth(),
        ) {
            if (loading) CircularProgressIndicator(modifier = Modifier.height(20.dp))
            else Text(stringResource(if (isRegister) R.string.register else R.string.login))
        }
        TextButton(onClick = { isRegister = !isRegister }) {
            Text(stringResource(if (isRegister) R.string.have_account_login else R.string.no_account_register))
        }

        Spacer(Modifier.height(8.dp))
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
            HorizontalDivider(modifier = Modifier.weight(1f))
            Text(
                stringResource(R.string.or_divider),
                modifier = Modifier.padding(horizontal = 12.dp),
                style = MaterialTheme.typography.bodySmall,
            )
            HorizontalDivider(modifier = Modifier.weight(1f))
        }
        Spacer(Modifier.height(8.dp))

        if (googleError) {
            Text(stringResource(R.string.google_signin_error), color = MaterialTheme.colorScheme.error)
            Spacer(Modifier.height(8.dp))
        }
        OutlinedButton(
            onClick = {
                googleLoading = true; googleError = false
                scope.launch {
                    val outcome = signInWithGoogle(context)
                    outcome.onSuccess { idToken ->
                        val api = ApiProvider.init(context)
                        val result = safeCall { api.googleAuth(GoogleAuthIn(idToken)) }
                        result.onSuccess { auth -> finishSignIn(api, auth.token) }
                            .onFailure { googleError = true }
                    }.onFailure { googleError = true }
                    googleLoading = false
                }
            },
            enabled = !googleLoading,
            modifier = Modifier.fillMaxWidth(),
        ) {
            if (googleLoading) CircularProgressIndicator(modifier = Modifier.height(20.dp))
            else Text(stringResource(R.string.continue_with_google))
        }
    }
}

/** Shows the device's Google account picker via Credential Manager and
 * returns a verified Google ID token on success. */
private suspend fun signInWithGoogle(context: Context): Result<String> {
    return try {
        val option = GetSignInWithGoogleOption
            .Builder(context.getString(R.string.google_web_client_id))
            .build()
        val request = GetCredentialRequest.Builder().addCredentialOption(option).build()
        val response = CredentialManager.create(context).getCredential(context, request)
        val googleCredential = GoogleIdTokenCredential.createFrom(response.credential.data)
        Result.success(googleCredential.idToken)
    } catch (e: GetCredentialException) {
        Result.failure(e)
    } catch (e: Exception) {
        Result.failure(e)
    }
}
