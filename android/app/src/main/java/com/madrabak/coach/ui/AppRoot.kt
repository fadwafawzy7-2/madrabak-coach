package com.madrabak.coach.ui

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ChatBubble
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Restaurant
import androidx.compose.material.icons.filled.TrendingUp
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.madrabak.coach.R
import com.madrabak.coach.data.repo.ApiProvider
import com.madrabak.coach.ui.screens.AccountScreen
import com.madrabak.coach.ui.screens.AuthScreen
import com.madrabak.coach.ui.screens.CoachScreen
import com.madrabak.coach.ui.screens.FoodScreen
import com.madrabak.coach.ui.screens.HomeScreen
import com.madrabak.coach.ui.screens.OnboardingScreen
import com.madrabak.coach.ui.screens.ProgressScreen
import kotlinx.coroutines.flow.first

private data class Tab(val route: String, val labelRes: Int, val icon: androidx.compose.ui.graphics.vector.ImageVector)

@Composable
fun AppRoot() {
    val context = LocalContext.current
    var startState by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(Unit) {
        val token = ApiProvider.sessionStore(context).token.first()
        startState = if (token == null) "auth" else "main"
    }

    when (startState) {
        null -> {}
        "auth" -> AuthScreen(onAuthenticated = { needsOnboarding ->
            startState = if (needsOnboarding) "onboarding" else "main"
        })
        "onboarding" -> OnboardingScreen(onDone = { startState = "main" })
        "main" -> MainScaffold(onLoggedOut = { startState = "auth" })
    }
}

@Composable
private fun MainScaffold(onLoggedOut: () -> Unit) {
    val navController = rememberNavController()
    val tabs = listOf(
        Tab("home", R.string.nav_home, Icons.Filled.Home),
        Tab("food", R.string.nav_food, Icons.Filled.Restaurant),
        Tab("progress", R.string.nav_progress, Icons.Filled.TrendingUp),
        Tab("coach", R.string.nav_coach, Icons.Filled.ChatBubble),
        Tab("account", R.string.nav_account, Icons.Filled.Person),
    )
    val backStack by navController.currentBackStackEntryAsState()
    val currentRoute = backStack?.destination?.route

    Scaffold(
        bottomBar = {
            NavigationBar {
                tabs.forEach { tab ->
                    NavigationBarItem(
                        selected = currentRoute == tab.route,
                        onClick = {
                            navController.navigate(tab.route) {
                                popUpTo("home") { saveState = true }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                        icon = { Icon(tab.icon, contentDescription = stringResource(tab.labelRes)) },
                        label = { Text(stringResource(tab.labelRes)) },
                    )
                }
            }
        },
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = "home",
            modifier = Modifier.padding(padding),
        ) {
            composable("home") {
                HomeScreen(
                    onNavigateToFood = { navController.navigate("food") },
                    onNavigateToCoach = { navController.navigate("coach") },
                    onNavigateToProgress = { navController.navigate("progress") },
                )
            }
            composable("food") { FoodScreen() }
            composable("progress") { ProgressScreen() }
            composable("coach") { CoachScreen() }
            composable("account") {
                AccountScreen(onLoggedOut = onLoggedOut, onEditProfile = { navController.navigate("edit_profile") })
            }
            composable("edit_profile") {
                OnboardingScreen(
                    isEditing = true,
                    onDone = { navController.popBackStack() },
                    onBack = { navController.popBackStack() },
                )
            }
        }
    }
}
