package com.piyush.superlive.domain.model

import kotlinx.serialization.Serializable

@Serializable data class LoginRequest(val email: String, val password: String)

@Serializable data class LoginResponse(val token: String? = null, val error: String? = null)
