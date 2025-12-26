package com.piyush.superlive.presentation.screens.login

data class LoginState(
        val isLoading: Boolean = false,
        val token: String? = null,
        val error: String = ""
)
