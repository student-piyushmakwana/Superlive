package com.piyush.superlive.presentation.screens.profile

import com.piyush.superlive.domain.model.ProfileData

data class ProfileState(
        val isLoading: Boolean = false,
        val profile: ProfileData? = null,
        val error: String = ""
)
