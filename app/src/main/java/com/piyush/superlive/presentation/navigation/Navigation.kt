package com.piyush.superlive.presentation.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.piyush.superlive.presentation.screens.dashboard.DashboardScreen
import com.piyush.superlive.presentation.screens.login.LoginScreen
import com.piyush.superlive.presentation.screens.profile.ProfileScreen

@Composable
fun Navigation() {
    val navController = rememberNavController()

    NavHost(navController = navController, startDestination = Screen.LoginScreen.route) {
        composable(route = Screen.LoginScreen.route) {
            LoginScreen(
                    onNavigateToDashboard = {
                        navController.navigate(Screen.DashboardScreen.createRoute(it)) {
                            popUpTo(Screen.LoginScreen.route) { inclusive = true }
                        }
                    }
            )
        }
        composable(
                route = Screen.DashboardScreen.route,
                arguments = listOf(navArgument("token") { type = NavType.StringType })
        ) { backStackEntry ->
            val token = backStackEntry.arguments?.getString("token") ?: ""
            DashboardScreen(
                    token = token,
                    onNavigateToProfile = {
                        navController.navigate(Screen.ProfileScreen.createRoute(it))
                    }
            )
        }
        composable(
                route = Screen.ProfileScreen.route,
                arguments = listOf(navArgument("token") { type = NavType.StringType })
        ) { ProfileScreen() }
    }
}
