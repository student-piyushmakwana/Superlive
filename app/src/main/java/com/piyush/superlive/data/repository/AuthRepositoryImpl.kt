package com.piyush.superlive.data.repository

import com.piyush.superlive.common.Resource
import com.piyush.superlive.data.remote.SuperliveApi
import com.piyush.superlive.domain.model.LoginRequest
import com.piyush.superlive.domain.model.LoginResponse
import com.piyush.superlive.domain.repository.AuthRepository
import javax.inject.Inject

class AuthRepositoryImpl @Inject constructor(private val api: SuperliveApi) : AuthRepository {

    override suspend fun login(email: String, password: String): Resource<LoginResponse> {
        return try {
            val response = api.login(LoginRequest(email, password))
            if (response.isSuccessful && response.body() != null) {
                Resource.Success(response.body()!!)
            } else {
                Resource.Error(response.message() ?: "An unknown error occurred")
            }
        } catch (e: Exception) {
            Resource.Error("Couldn't reach server. Check your internet connection.")
        }
    }
}
