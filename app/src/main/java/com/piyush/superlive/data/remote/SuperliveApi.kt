package com.piyush.superlive.data.remote

import com.piyush.superlive.domain.model.LoginRequest
import com.piyush.superlive.domain.model.LoginResponse
import com.piyush.superlive.domain.model.ProfileRequest
import com.piyush.superlive.domain.model.ProfileResponse
import com.piyush.superlive.domain.model.UpdateProfileRequest
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.POST

interface SuperliveApi {
    @POST("login") suspend fun login(@Body request: LoginRequest): Response<LoginResponse>

    @POST("profile")
    suspend fun getProfile(@Body request: ProfileRequest): Response<ProfileResponse>

    @POST("update-profile")
    suspend fun updateProfile(@Body request: UpdateProfileRequest): Response<ProfileResponse>
}
