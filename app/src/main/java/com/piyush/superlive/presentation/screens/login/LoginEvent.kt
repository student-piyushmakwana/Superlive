package com.piyush.superlive.presentation.screens.login

sealed class LoginEvent {
    data class Login(val email: String, val password: String) : LoginEvent()
    object Result : LoginEvent()
}
