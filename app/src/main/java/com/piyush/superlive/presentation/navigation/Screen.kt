package com.piyush.superlive.presentation.navigation

sealed class Screen(val route: String) {
    object LoginScreen : Screen("login_screen")
    object DashboardScreen : Screen("dashboard_screen/{token}") {
        fun createRoute(token: String) = "dashboard_screen/$token"
    }
    object ProfileScreen : Screen("profile_screen/{token}") {
        fun createRoute(token: String) = "profile_screen/$token"
    }
}
