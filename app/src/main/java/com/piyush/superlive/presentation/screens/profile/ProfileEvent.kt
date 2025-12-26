package com.piyush.superlive.presentation.screens.profile

sealed class ProfileEvent {
    data class UpdateProfile(val name: String) : ProfileEvent()
    object Refresh : ProfileEvent()
}
