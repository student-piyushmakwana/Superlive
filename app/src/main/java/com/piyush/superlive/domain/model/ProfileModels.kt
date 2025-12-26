package com.piyush.superlive.domain.model

import kotlinx.serialization.Serializable

@Serializable data class ProfileRequest(val token: String)

@Serializable data class UpdateProfileRequest(val token: String, val name: String? = null)

@Serializable data class ProfileResponse(val data: ProfileData? = null, val error: String? = null)

@Serializable
data class ProfileData(val name: String, val email: String, val coins: Int = 0
// Add other fields as needed based on API response
)
